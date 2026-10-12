"""Isolated real v2 intake/assessment replay; authored contrasts are nongold."""

import argparse
import asyncio
import json
import os
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

from dotenv import dotenv_values

from backend.modules.providers.typesafe_provider import TypeSafeDecisionClient
from backend.modules.sensory.evidence_triage import EvidenceTriage
from backend.services.belief_admission import admit_candidate
from backend.storage.database import init_db
from backend.storage.migrations import run_all_migrations
from backend.storage.repositories import ConversationRepository, MessageRepository, NotificationRepository
from backend.utils.belief_candidate import inert_belief_history
from backend.utils.parsers.belief import parse_belief_nucleate_tags
from benchmarks.suites.calibration_contract import digest

CONFIG = {"belief_review": {"origin_intake": {"explicit_chat": True}, "assessment": {"enabled": True}}}


def validate_seal(value, field):
    body = dict(value)
    checksum = body.pop(field)
    if digest(body) != checksum:
        raise ValueError("Source artifact hash mismatch")


def contrasts():
    baseline = "Repeated identical input must produce a changed decision when memory is consequential."
    source = "During repeated-input memory trials, decision changes were absent; a later trial changed the decision after an external counterexample."
    statements = [
        ("baseline", baseline),
        ("exact_repeat", baseline),
        ("paraphrase", "Consequential memory requires different decisions across identical repeated inputs."),
        ("extension", "Consequential memory requires changed decisions only after an external counterexample."),
        ("conflict", "Consequential memory must preserve identical decisions across identical repeated inputs."),
        (
            "artistic_question",
            "An unchanged decision can expose a worthwhile artistic question about habitual refusal.",
        ),
        ("missing_quote", "Consequential memory requires changed decisions after new evidence."),
    ]
    return [
        {
            "id": name,
            "origin": "authored_contrast_nongold",
            "parent": source,
            "data": {
                "statement": statement,
                "label": name,
                "confidence": 0.8,
                "scope": "Repeated-input memory trials",
                "temporal_scope": "During the described trials",
                "trigger": "conflict" if name == "conflict" else "insight",
                "consequence": "Reconsider whether unchanged decisions indicate habitual refusal.",
                "rationale": "Authored contrast for routing inspection; not measured truth.",
                "evidence_quote": "Absent invented quotation" if name == "missing_quote" else source,
            },
        }
        for name, statement in statements
    ]


def recorded(packet, reviews):
    validate_seal(packet, "packet_sha256")
    case = next(c for c in packet["cases"] if str(c["id"]) == "3974")
    parent = next(m["content"] for m in reversed(case["prompts"]["archived"]) if m["role"] == "user")
    rows = []
    for condition, report in reviews:
        validate_seal(report, "report_sha256")
        for arm, receipt in report["cases"][0]["outputs"].items():
            if receipt["status"] != "complete":
                continue
            validate_seal(receipt, "receipt_sha256")
            raw = receipt["raw_output"]
            _, candidates = parse_belief_nucleate_tags(raw)
            for index, data in enumerate(candidates):
                rows.append(
                    {
                        "id": f"{condition}-{arm}-{index}",
                        "origin": "recorded_generated_nomination",
                        "parent": parent,
                        "data": data,
                        "raw": raw,
                        "source_receipt_sha256": receipt["receipt_sha256"],
                    }
                )
    if rows:
        rows.append(rows[0] | {"id": "recorded_exact_recurrence", "recurrence_of": rows[0]["id"]})
    return rows


def source_ancestry(capture):
    validate_seal(capture, "capture_sha256")
    case = next(c for c in capture["cases"] if str(c["id"]) == "3974")
    messages = {str(m["id"]): m for m in case["path"]}
    rows = []
    for source_id in ("3784", "3818", "3897", "3974"):
        message = messages[source_id]
        parent = messages.get(str(message.get("parent_message_id")))
        if parent is None:
            raise ValueError("Source parent unavailable")
        _, candidates = parse_belief_nucleate_tags(message["content"])
        for index, data in enumerate(candidates):
            rows.append(
                {
                    "id": f"source-{source_id}-{index}",
                    "origin": "recorded_generated_nomination",
                    "parent": parent["content"],
                    "data": data,
                    "raw": message["content"],
                    "source_capture_sha256": capture["capture_sha256"],
                    "source_message_id": source_id,
                }
            )
    return rows


def setup(path):
    # Migration 051 otherwise resolves the ambient live structural provider.
    # Its existing unavailable-scorer fallback seeds zeros; geometry is not measured here.
    with patch(
        "backend.modules.structural_engine.CompositeStructuralScorer",
        side_effect=RuntimeError("Benchmark migration has no structural network port"),
    ):
        connection = init_db(str(path))
        run_all_migrations(connection)
        connection.commit()
        connection.close()
    ConversationRepository(str(path)).create("isolated-replay", agent_id="symbia")


def insert(path, parent, raw):
    repo = MessageRepository(str(path))
    common = {
        "embedding": b"",
        "embedding_model": "replay-none",
        "embedding_dim": 0,
        "conversation_id": "isolated-replay",
    }
    source = repo.insert(speaker="human", content=parent, **common)
    return repo.insert(speaker="apparatus", content=raw, parent_message_id=source.id, **common)


def counts(path):
    with sqlite3.connect(path) as conn:
        return {
            table: conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("belief_proposals", "belief_encounters", "belief_review_decisions")
        }


class ObservedClient:
    def __init__(self, client, root):
        self.client, self.root = client, root
        self.model, self.is_configured = client.model, client.is_configured
        self.calls = 0
        self.failures = 0

    async def evaluate(self, state, questions):
        if self.failures >= 3 or self.calls >= 7:
            return {"success": False, "answers": {}, "error": "benchmark_call_budget_exhausted"}
        self.calls += 1
        target = self.root / f"provider-{self.calls}.json"
        receipt = {
            "status": "outcome_unknown",
            "input_sha256": digest([state, questions]),
            "requested_model": self.model,
            "state": state,
            "questions": questions,
        }
        await asyncio.to_thread(target.write_text, json.dumps(receipt, indent=2), encoding="utf-8")
        result = await self.client.evaluate(state, questions)
        receipt.update(
            status="complete" if result.get("success") else "failed",
            answers=result.get("answers", {}),
            returned_model=result.get("model"),
            usage=result.get("usage", {}),
        )
        self.failures += not bool(result.get("success"))
        await asyncio.to_thread(target.write_text, json.dumps(receipt, indent=2), encoding="utf-8")
        return result


async def run(root, cases, client):
    root = root.resolve()
    allowed = (Path(__file__).resolve().parents[1] / "runs").resolve()
    if not root.is_relative_to(allowed) and "pytest" not in sys.modules:
        raise ValueError("Replay databases must remain in benchmarks/runs")
    if not 1 <= len(cases) <= 24 or len({c["id"] for c in cases}) != len(cases):
        raise ValueError("Replay cases must be bounded and uniquely identified")
    await asyncio.to_thread(root.mkdir, parents=True, exist_ok=False)
    contract = {
        "cases": cases,
        "cases_sha256": digest(cases),
        "config": CONFIG,
        "independent_gold": False,
        "production_slots": 0,
        "database_kind": "fresh migrated source reconstruction; not production snapshot",
        "max_provider_calls": 7,
        "max_failures": 3,
        "workers": 1,
        "provider_timeout": 8,
    }
    await asyncio.to_thread((root / "contract.json").write_text, json.dumps(contract, indent=2), encoding="utf-8")
    observed = ObservedClient(client, root)
    results = []
    for group in ("recorded_generated_nomination", "authored_contrast_nongold"):
        path = root / (group + ".sqlite")
        await asyncio.to_thread(setup, path)
        for case in [c for c in cases if c["origin"] == group]:
            raw = case.get("raw") or case["data"]["statement"]
            message = await asyncio.to_thread(insert, path, case["parent"], raw)
            before = observed.calls
            receipt = await admit_candidate(
                str(path),
                "isolated-replay",
                message.id,
                case["data"],
                config=CONFIG,
                evaluator=EvidenceTriage(observed),
            )
            retry = await admit_candidate(
                str(path),
                "isolated-replay",
                message.id,
                case["data"],
                config=CONFIG,
                evaluator=EvidenceTriage(observed),
            )
            if retry != receipt:
                raise AssertionError("Same source replay changed receipt")
            row = {
                "case_id": case["id"],
                "receipt": receipt,
                "provider_calls": observed.calls - before,
                "counts": await asyncio.to_thread(counts, path),
                "history_inert": "<belief_nucleate" not in inert_belief_history(raw),
            }
            results.append(row)
            await asyncio.to_thread((root / "results.json").write_text, json.dumps(results, indent=2), encoding="utf-8")
        traces = await asyncio.to_thread(NotificationRepository(str(path)).list_all)
        await asyncio.to_thread(
            (root / (group + "-traces.json")).write_text, json.dumps(traces, indent=2), encoding="utf-8"
        )
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--recorded-only", action="store_true")
    args = parser.parse_args()
    values = {**dotenv_values(".env"), **os.environ}
    client = TypeSafeDecisionClient(
        api_key=(values.get("AAA_TYPESAFE_API_KEY") or values.get("AAA_LLM_API_KEY") or "").split(",")[0],
        api_base=values.get("AAA_TYPESAFE_API_BASE") or "https://openrouter.ai/api/alpha",
        model=values.get("AAA_TYPESAFE_MODEL") or "typesafe/jev-1.13",
        timeout=8,
    )
    packet = json.loads((args.source / "packet.json").read_text(encoding="utf-8"))
    reviews = [
        (name, json.loads((args.source / folder / "review.json").read_text(encoding="utf-8")))
        for name, folder in (("historical", "nvidia-review"), ("current", "current-protocol-review"))
    ]
    capture = json.loads((args.source / "capture.json").read_text(encoding="utf-8"))
    cases = source_ancestry(capture) + recorded(packet, reviews)
    if not args.recorded_only:
        cases += contrasts()
    print("Completed cases:", len(asyncio.run(run(args.output, cases, client))))


if __name__ == "__main__":
    main()
