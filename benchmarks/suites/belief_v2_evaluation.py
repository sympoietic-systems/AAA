"""Offline T15 audit and matched structural replay; no semantic or adoption authority."""

import argparse
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from backend.modules.belief_selection import ParticipationPolicy, exploratory, frame_selection
from backend.storage.activation import BeliefSelectionReceipt
from backend.storage.repositories.cognitive.belief_selection import SelectionRecord, SelectionSnapshot
from benchmarks.suites.belief_auto_review import validate_provisional
from benchmarks.suites.belief_review_corpus import validate
from benchmarks.suites.calibration_contract import digest, validate_splits

POLICY = "belief-v2-evaluation-v1"
TIMESTAMP = "2026-10-11T00:00:00+00:00"


def freeze_contract(packet: dict[str, Any], *, replay_source: str) -> dict[str, Any]:
    """Freeze engineering bounds before held-out execution, never guess semantic thresholds."""
    validate(packet)
    if replay_source not in {"synthetic_regression", "recorded_snapshot"}:
        raise ValueError("Explicit replay provenance required")
    contract = {
        "policy": POLICY,
        "packet_sha256": digest(packet),
        "replay_source": replay_source,
        "arms": [0, 1, 2],
        "recommended_production_slots": 0,
        "targets": {
            "authority_changes": 0,
            "warrant_changes": 0,
            "record_mutations": 0,
            "duplicate_selections": 0,
            "invalid_receipts": 0,
        },
        "semantic_targets": None,
        "semantic_target_reason": "independent baseline required before justified thresholds can be frozen",
        "downstream_usefulness": "unmeasured",
        "promotion": "BLOCKED",
    }
    return {**contract, "contract_sha256": digest(contract)}


def audit(packet: dict[str, Any], frozen: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    bound = dict(contract)
    checksum = bound.pop("contract_sha256")
    if checksum != digest(bound) or contract["packet_sha256"] != digest(packet):
        raise ValueError("Evaluation contract or source binding changed")
    if contract != freeze_contract(packet, replay_source=contract["replay_source"]):
        raise ValueError("Evaluation budgets or acceptance boundary changed")
    validate_provisional(packet, frozen)
    validate_splits(packet["cases"])
    summaries = {}
    for split in ("tune", "validation", "heldout"):
        cases = [c for c in frozen["cases"] if c["split"] == split]
        source = [c for c in packet["cases"] if c["split"] == split]
        reviews = [r for c in cases for r in c["reviewers"] if r["status"] == "reviewed"]
        summaries[split] = {
            "cases": len(cases),
            "families": len({c["family_id"] for c in cases}),
            "review_outcomes": dict(Counter(c["review_outcome"] for c in cases)),
            "valid_review_outputs": len(reviews),
            "effective_relations": dict(Counter(r["annotation"]["relation"] for r in reviews)),
            "recommendations": dict(Counter(r["annotation"]["recommendation"] for r in reviews)),
            "warrant_nominations": dict(Counter(r["annotation"]["warrant"] for r in reviews)),
            "failure_statuses": dict(
                Counter(r["status"] for c in cases for r in c["reviewers"] if r["status"] != "reviewed")
            ),
            "unknown_lineage_cases": sum(c["lineage_baseline"].get("independence_status") == "unknown" for c in source),
            "incomplete_pair_context_cases": sum(c["context_incomplete"] for c in cases),
            # Counts are attributed opinions, never errors or correct predictions.
            "equivalence_nominations": sum(r["annotation"]["relation"] == "equivalent" for r in reviews),
            "distinction_nominations": sum(r["annotation"]["relation"] in {"distinct", "extension"} for r in reviews),
            "conflict_nominations": sum(r["annotation"]["relation"] == "contradiction" for r in reviews),
            "abstaining_reviews": sum(r["annotation"]["relation"] == "insufficient_context" for r in reviews),
            "retained_cases": len(cases),
            "reviewer_slots": 2 * len(cases),
            "reviewer_disagreement_case_ids": [c["case_id"] for c in cases if c["review_outcome"] == "disagreement"],
        }
    return {
        "policy": POLICY,
        "contract_sha256": contract["contract_sha256"],
        "frozen_review_sha256": frozen["frozen_sha256"],
        "partitions": summaries,
        "independent_gold": False,
        "accuracy": None,
        "false_equivalence": None,
        "missed_conflicts": None,
        "useful_distinction_retention": None,
        "redundant_review_burden": None,
        "downstream_usefulness": None,
        "semantic_acceptance": "UNRESOLVED",
        "reason": "Provisional reviewer opinions cannot supply independent truth or usefulness judgments",
        "adoption_authority": "none",
        "promotion": "BLOCKED",
    }


def replay(snapshot: SelectionSnapshot, signatures: list[list[float]], *, source_kind: str) -> dict[str, Any]:
    """Same immutable records and signatures for all arms; measures exploratory slots only."""
    if source_kind not in {"synthetic_regression", "recorded_snapshot"}:
        raise ValueError("Explicit replay provenance required")
    if not 1 <= len(signatures) <= 100 or len(snapshot.records) > 200:
        raise ValueError("Replay requires 1..100 signatures and at most 200 records")
    if len({r.id for r in snapshot.records}) != len(snapshot.records):
        raise ValueError("Duplicate replay record identity")
    vectors = [np.asarray(s, dtype=float) for s in signatures]
    if any(v.shape != (16,) or not np.isfinite(v).all() for v in vectors):
        raise ValueError("Replay signatures must be finite 16-dimensional vectors")
    before = digest(asdict(snapshot))
    arms = []
    for slots in (0, 1, 2):
        rows = []
        for signature in vectors:
            items = exploratory(
                snapshot, signature, ParticipationPolicy(enabled=bool(slots), slots=slots), timestamp=TIMESTAMP
            )
            receipts = []
            for item in items:
                receipt = BeliefSelectionReceipt.model_validate_json(json.dumps(item["selection_receipt"]))
                framed = json.loads(frame_selection(item))
                if receipt.tool_authority != "none" or receipt.independent_warrant_delta != 0:
                    raise ValueError("Replay acquired authority or warrant")
                if framed["standing"] != receipt.standing or framed["scope"] != receipt.scope:
                    raise ValueError("Replay lost scoped standing")
                receipts.append(receipt.model_dump(mode="json"))
            if len({i["id"] for i in items}) != len(items) or len(items) > slots:
                raise ValueError("Replay violated finite unique selection budget")
            rows.append({"signature_sha256": digest(signature.tolist()), "receipts": receipts})
        selected = {r["record_id"] for row in rows for r in row["receipts"]}
        eligible = [r for r in snapshot.records if r.stratum != "active" and not r.label.startswith("skill:")]
        arms.append(
            {
                "slots": slots,
                "rows": rows,
                "insertion_count": sum(len(row["receipts"]) for row in rows),
                "unique_selected": len(selected),
                "eligible_records": len(eligible),
                "unselected_record_ids": [r.id for r in eligible if r.id not in selected],
                "dissent_selected": sum(r.id in selected and bool(r.dissent) for r in eligible),
                "dormant_selected": sum(r.id in selected and r.stratum == "history" for r in eligible),
                "candidate_selected": sum(r.id in selected and r.stratum == "pending" for r in eligible),
                "authority_changes": 0,
                "warrant_changes": 0,
                "record_mutations": int(digest(asdict(snapshot)) != before),
                "duplicate_selections": 0,
                "invalid_receipts": 0,
            }
        )
    if digest(asdict(snapshot)) != before:
        raise ValueError("Replay changed input records")
    return {
        "source_kind": source_kind,
        "snapshot_sha256": before,
        "signatures_sha256": digest(signatures),
        "scan_truncated": snapshot.truncated,
        "selector": "belief-participation-v1 exploratory only; legacy/spectral held constant outside this replay",
        "arms": arms,
        "downstream_usefulness": "unmeasured; insertion is not response influence",
        "promotion": "BLOCKED",
    }


def structural_acceptance(contract: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Passing engineering bounds cannot close unresolved semantic acceptance."""
    replay_result = result["participation_replay"]
    arms = replay_result["arms"]
    failures = []
    if [a["slots"] for a in arms] != contract["arms"]:
        failures.append("matched_arm_budget_changed")
    if replay_result["source_kind"] != contract["replay_source"]:
        failures.append("replay_provenance_changed")
    for arm in arms:
        for target, maximum in contract["targets"].items():
            if arm.get(target) != maximum:
                failures.append(f"slots_{arm['slots']}:{target}")
    return {
        "engineering": "FAIL" if failures else "PASS",
        "failures": failures,
        "semantic": "UNRESOLVED",
        "recorded_downstream_replay": "NOT_RUN"
        if replay_result["source_kind"] == "synthetic_regression"
        else "UNVERIFIED",
        "overall": "INCOMPLETE",
        "promotion": "BLOCKED",
    }


def stress_fixture() -> tuple[SelectionSnapshot, list[list[float]]]:
    """Deliberate coverage sentinel, not recovered production geometry or semantic gold."""
    records = []
    for index in range(12):
        records.append(
            SelectionRecord(
                id=f"fixture-{index:02d}",
                label=f"question-{index}",
                statement=f"Scoped question {index}",
                confidence=0.5,
                ontological_mass=0.1,
                vector_16d=json.dumps([1.0] + [0.0] * 15),
                lifecycle_stage="nucleating",
                stratum="history" if index == 0 else "pending",
                review_state="declined" if index == 0 else "candidate",
                standing="provisional_candidate",
                scope="synthetic replay",
                temporal_scope="fixture only",
                challenges=("unresolved",),
                dissent=("retained disagreement",) if index == 0 else (),
                decision_id=None,
                history_truncated=False,
                counter_trace=None,
                kind="proposal",
            )
        )
    return SelectionSnapshot(tuple(records), False), [[1.0] + [0.0] * 15, [0.0, 1.0] + [0.0] * 14]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--frozen", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Use a fresh output directory; historical receipts cannot be overwritten")
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    frozen = json.loads(args.frozen.read_text(encoding="utf-8"))
    contract = freeze_contract(packet, replay_source="synthetic_regression")
    args.output.mkdir(parents=True)
    # Durable contract precedes any held-out audit/replay execution.
    (args.output / "contract.json").write_text(json.dumps(contract, indent=2), encoding="utf-8")
    result = audit(packet, frozen, contract)
    snapshot, signatures = stress_fixture()
    result["participation_replay"] = replay(snapshot, signatures, source_kind="synthetic_regression")
    result["acceptance"] = structural_acceptance(contract, result)
    result["result_sha256"] = digest(result)
    (args.output / "evaluation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
