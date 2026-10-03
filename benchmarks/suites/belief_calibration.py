"""Export annotation packets and compare frozen, independently labeled belief pairs."""

import argparse
import asyncio
import json
from dataclasses import asdict
from itertools import combinations
from pathlib import Path

from backend.config import load_config
from backend.core.logging_config import mask_secrets
from backend.modules.providers.typesafe_provider import TypeSafeDecisionClient
from backend.modules.sensory.belief_context import ClaimContext, context_error
from backend.modules.sensory.evidence_triage import EvidenceTriage, probability
from backend.services.belief_triage import BeliefEvidence, BeliefTriage, relation_questions
from benchmarks.suites.belief_triage import CORPUS, VECTOR, read_snapshot
from benchmarks.suites.calibration_contract import belief_score, digest, reviewed_label, validate_splits


def prepare(database: Path, agent_id: str, count: int = 240) -> dict:
    if not 1 <= count <= 300:
        raise ValueError("packet size must be 1..300")
    beliefs, _, skipped, _ = read_snapshot(database, agent_id)
    ordered = sorted(beliefs, key=lambda b: digest(b.id))
    n = len(ordered)
    partitions = [
        ("tune", ordered[: int(n * 0.2)], 0.2),
        ("validation", ordered[int(n * 0.2) : int(n * 0.4)], 0.2),
        ("heldout", ordered[int(n * 0.4) :], 0.6),
    ]
    cases = []
    for split, nodes, fraction in partitions:
        pairs = sorted(combinations(nodes, 2), key=lambda pair: digest([pair[0].id, pair[1].id]))
        for a, b in pairs[: int(count * fraction)]:
            values = [{**asdict(x), "statement": mask_secrets(x.statement)} for x in (a, b)]
            cases.append(
                {
                    "id": digest([a.id, b.id])[:20],
                    "split": split,
                    "split_entities": [a.id, b.id],
                    "a": values[0],
                    "b": values[1],
                    "annotations": [],
                    "source_kind": "real_snapshot",
                }
            )
    validate_splits(cases)
    return {
        "schema_version": 1,
        "source": str(database),
        "agent_id": agent_id,
        "cases": cases,
        "skipped": skipped,
        "requested_count": count,
        "manifest_sha256": digest(cases),
        "annotation_status": "UNLABELED",
        "promotion": "BLOCKED",
    }


def evidence(value: dict) -> BeliefEvidence:
    context = ClaimContext.model_validate_json(json.dumps(value["context"])) if value.get("context") else None
    return BeliefEvidence(value["id"], value["statement"], value["mass"], tuple(value["vector"]), context)


async def baseline_pair(service: BeliefTriage, a: BeliefEvidence, b: BeliefEvidence) -> dict:
    """Isolated unguarded baseline. Its receipts cannot be replayed into matrix edges."""
    questions = relation_questions()
    receipt = await service.evaluator.evaluate({"a": a.statement, "b": b.statement}, questions)
    receipt.update(mode="calibration_baseline_only", context_validated=False, route="abstain", tension_magnitude=None)
    try:
        answer = receipt["answers"]["relation"]
        relation = answer.get("choice", answer.get("decision"))
        confidence = min(
            probability(answer["confidence"]), probability(receipt["answers"]["contradicts"]["confidence"])
        )
        strength = probability(
            receipt["answers"]["contradicts"].get("score", receipt["answers"]["contradicts"].get("value"))
        )
        receipt["relation"] = relation
        if (
            relation == "contradiction"
            and strength >= 0.7
            and confidence >= (0.85 if max(a.mass, b.mass) >= 0.8 else 0.7)
        ):
            receipt["route"] = "review_contradiction"
    except (KeyError, TypeError, ValueError):
        receipt["reason"] = "invalid_baseline_answers"
    return receipt


async def sentinels(service: BeliefTriage, repeats: int = 2) -> dict:
    rows = []
    for case in CORPUS:
        claims = []
        for side in ("a", "b"):
            statement = case[side]
            context = ClaimContext(
                statement_sha256=digest_text(statement),
                scope="explicit synthetic case",
                temporal_scope="times stated in the synthetic claim",
                provenance="synthetic fixture",
                resolution="ambiguous" if case["expected"] == "abstain" else "resolved",
            )
            claims.append(BeliefEvidence(case["id"] + ":" + side, statement, 0.9, VECTOR, context))
        for repeat in range(repeats):
            for arm in ("baseline", "context", "staged"):
                receipt = (
                    await baseline_pair(service, *claims)
                    if arm == "baseline"
                    else await service.evaluate_pair(*claims, staged=arm == "staged")
                )
                rows.append(
                    {"id": case["id"], "repeat": repeat, "arm": arm, "gold": case["expected"], "receipt": receipt}
                )
    return {
        "purpose": "synthetic regression only; no independent gold",
        "rows": rows,
        "scores": {
            arm: belief_score([r for r in rows if r["arm"] == arm]) for arm in ("baseline", "context", "staged")
        },
        "promotion": "BLOCKED",
    }


def digest_text(statement: str) -> str:
    import hashlib

    return hashlib.sha256(statement.encode()).hexdigest()


async def evaluate(packet: dict, service: BeliefTriage, repeats: int = 1) -> dict:
    if not 1 <= repeats <= 3:
        raise ValueError("repeats must be 1..3")
    cases = packet["cases"]
    if not 1 <= len(cases) <= 300:
        raise ValueError("dataset must contain 1..300 cases")
    validate_splits(cases)
    if packet.get("frozen") and packet.get("frozen_sha256") != digest(cases):
        raise ValueError("frozen dataset changed")
    rows, pending = [], []
    for case in cases:
        if case["split"] != "heldout":
            continue
        gold, reason = reviewed_label(case)
        if not packet.get("frozen"):
            pending.append({"id": case["id"], "reason": reason or "freeze_required"})
            continue
        if gold is None:
            pending.append({"id": case["id"], "reason": reason})
            continue
        if not isinstance(gold, str) or gold not in {"contradiction", "endorsement", "orthogonal", "abstain"}:
            raise ValueError("unknown gold relation")
        for repeat in range(repeats):
            for arm in ("baseline", "context", "staged"):
                a, b = evidence(case["a"]), evidence(case["b"])
                receipt = (
                    await baseline_pair(service, a, b)
                    if arm == "baseline"
                    else await service.evaluate_pair(a, b, staged=arm == "staged")
                )
                rows.append(
                    {
                        "id": case["id"],
                        "repeat": repeat,
                        "arm": arm,
                        "gold": gold,
                        "annotation_note": reason,
                        "receipt": receipt,
                    }
                )
    return {
        "dataset_sha256": digest(packet),
        "rows": rows,
        "pending": pending,
        "scores": {
            arm: belief_score([r for r in rows if r["arm"] == arm]) for arm in ("baseline", "context", "staged")
        },
        "promotion": "BLOCKED",
        "reason": "independent corpus completion and reviewed opt-in required",
    }


def freeze(packet: dict) -> dict:
    validate_splits(packet["cases"])
    for case in packet["cases"]:
        gold, _ = reviewed_label(case)
        if not isinstance(gold, str) or gold not in {"contradiction", "endorsement", "orthogonal", "abstain"}:
            raise ValueError("independent labels required before freeze")
        for side in ("a", "b"):
            claim = evidence(case[side])
            if claim.context is None or (context_error(claim.statement, claim.context) and gold != "abstain"):
                raise ValueError("reviewed statement context required before freeze")
    return {**packet, "frozen": True, "frozen_sha256": digest(packet["cases"])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", type=Path)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--sentinels", action="store_true")
    parser.add_argument("--freeze", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--agent-id", default="symbia")
    parser.add_argument("--count", type=int, default=240)
    parser.add_argument("--repeats", type=int, default=1)
    args = parser.parse_args()
    if sum([bool(args.prepare), bool(args.dataset), args.sentinels, bool(args.freeze)]) != 1:
        parser.error("choose prepare, dataset or sentinels")
    if args.output.exists():
        parser.error("output must be fresh")
    if args.freeze:
        result = freeze(json.loads(args.freeze.read_text(encoding="utf-8")))
    elif args.prepare:
        result = prepare(args.prepare, args.agent_id, args.count)
    else:
        config = load_config(args.config) if args.config else {}
        service = BeliefTriage(EvidenceTriage(TypeSafeDecisionClient.from_config(config.get("typesafe", {}))))
        result = (
            asyncio.run(sentinels(service, args.repeats))
            if args.sentinels
            else asyncio.run(evaluate(json.loads(args.dataset.read_text(encoding="utf-8")), service, args.repeats))
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
