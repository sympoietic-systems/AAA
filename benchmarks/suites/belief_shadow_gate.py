"""Offline dimension-by-dimension shadow projection of sealed belief assessments."""

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

from benchmarks.suites.calibration_contract import digest

FLOOR = 0.85
RELATION_PREFIX = "relation_"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assess_case(case: dict[str, Any]) -> dict[str, Any]:
    """Project legacy aggregate gate beside independently retained dimensions.

    All observations are benchmark-only. Candidate context/quote failures block
    every dimension; relation observations also require a bound, matching peer.
    """
    candidate = case["candidate"]
    candidate_valid = bool(
        candidate.get("scope", "").strip()
        and candidate.get("temporal_scope", "").strip()
        and candidate.get("evidence_quote", "")
        and candidate["evidence_quote"] in candidate.get("source_text", "")
        and not case.get("context_issues")
    )
    diagnostics = case["diagnostics"]
    complete = case.get("legacy_assessment") == "evaluated"
    retained = []
    unresolved = []
    for diagnostic in diagnostics:
        question = diagnostic.get("question_id", "")
        confidence = diagnostic.get("confidence")
        choice = diagnostic.get("choice")
        status = "unresolved"
        reason = "below_threshold_or_missing"
        if not candidate_valid:
            reason = "candidate_context_or_quote_unbound"
        elif (
            isinstance(confidence, (int, float))
            and math.isfinite(confidence)
            and confidence >= FLOOR
            and diagnostic.get("status") == "within_threshold"
        ):
            resolved_choices = {
                "consequence": {"durable", "local", "none"},
                "factual_grounding": {"supported", "unsupported"},
                "artistic_grounding": {"supported", "unsupported"},
                "tension": {"present", "absent"},
            }
            if question.startswith(RELATION_PREFIX) and choice not in {
                "equivalent",
                "extension",
                "contradiction",
                "independent",
            }:
                reason = "noncommittal_relation_choice"
            elif question in resolved_choices and choice not in resolved_choices[question]:
                reason = "noncommittal_dimension_choice"
            elif question.startswith(RELATION_PREFIX):
                peer = case.get("comparisons", {}).get(question)
                peer_valid = bool(
                    peer
                    and peer.get("scope", "").strip()
                    and peer.get("temporal_scope", "").strip()
                    and peer.get("scope", "").strip().casefold() == candidate["scope"].strip().casefold()
                    and peer.get("temporal_scope", "").strip().casefold()
                    == candidate["temporal_scope"].strip().casefold()
                    and peer.get("evidence_quote") in peer.get("source_text", "")
                    and not case.get("relation_context_issues", {}).get(question)
                )
                if peer_valid:
                    status, reason = "retained_for_shadow", "dimension_threshold_and_source_context_pass"
                else:
                    reason = "comparison_context_or_quote_unbound"
            else:
                status, reason = "retained_for_shadow", "dimension_threshold_and_source_context_pass"
        entry = {
            "dimension": question,
            "choice": choice,
            "confidence": confidence,
            "floor": FLOOR,
            "status": status,
            "reason": reason,
        }
        (retained if status == "retained_for_shadow" else unresolved).append(entry)
    return {
        "case_id": case["case_id"],
        "source_kind": case["source_kind"],
        "legacy_assessment": case.get("legacy_assessment", "unknown"),
        "legacy_aggregate_gate_passed": complete and candidate_valid,
        "candidate_context_valid": candidate_valid,
        "dimension_count": len(diagnostics),
        "provider_calls": case.get("provider_calls", 0),
        "shadow_retained": retained,
        "unresolved": unresolved,
        "adoption_authority": "none",
    }


def _challenge_cases(root: Path) -> list[dict[str, Any]]:
    contract = json.loads((root / "contract.json").read_text(encoding="utf-8"))
    intake = json.loads((root / "combined-intake.json").read_text(encoding="utf-8"))
    result = []
    for row in intake:
        data = next(c for c in contract["cases"] if c["id"] == row["case_id"])
        call_path = root / f"jev-{row['case_id']}.json"
        call = json.loads(call_path.read_text(encoding="utf-8")) if call_path.exists() else {}
        if call:
            checksum = call.pop("receipt_sha256", None)
            if checksum != digest(call):
                raise ValueError("Frozen challenge call receipt hash mismatch")
            if call.get("case_id") != row["case_id"]:
                raise ValueError("Frozen challenge call does not match intake case")
            if call.get("input_sha256") != digest([call.get("state"), call.get("questions")]):
                raise ValueError("Frozen challenge call input hash mismatch")
            call["receipt_sha256"] = checksum
            if call.get("state", {}).get("candidate", {}).get("statement") != data["candidate"]["statement"]:
                raise ValueError("Frozen challenge call candidate differs from frozen corpus")
        candidate = data["candidate"]
        comparison = data["comparison"]
        diagnostics = row["receipt"]["evaluation"].get("diagnostics", [])
        result.append(
            {
                "case_id": row["case_id"],
                "source_kind": "authored_hypothetical_challenge",
                "candidate": candidate,
                "comparisons": {
                    d["question_id"]: comparison for d in diagnostics if d["question_id"].startswith(RELATION_PREFIX)
                },
                "diagnostics": diagnostics,
                "context_issues": row["receipt"].get("context_issues", []),
                "legacy_assessment": row["receipt"]["evaluation"]["status"],
                "provider_calls": row["provider_calls"],
            }
        )
    return result


def _conversation_cases(root: Path) -> list[dict[str, Any]]:
    results = json.loads((root / "results.json").read_text(encoding="utf-8"))
    cases = json.loads((root / "contract.json").read_text(encoding="utf-8"))["cases"]
    case_by_id = {str(c["id"]): c for c in cases}
    result = []
    attempted_rows = [row for row in results if row.get("provider_calls")]
    provider_inputs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(root.glob("provider-*.json"))]
    if len(attempted_rows) != len(provider_inputs):
        raise ValueError("Frozen provider input count does not match attempted result rows")
    for row, provider_input in zip(attempted_rows, provider_inputs, strict=True):
        source_case = case_by_id[row["case_id"]]
        source = source_case["data"]
        receipt = row["receipt"]
        eval_receipt = receipt["evaluation"]
        if provider_input.get("state", {}).get("candidate", {}).get("statement") != source.get("statement"):
            raise ValueError("Frozen conversation provider input differs from source candidate")
        peer_by_id = {p.get("id"): p for p in provider_input.get("state", {}).get("comparisons", [])}
        comparisons = {}
        for diagnostic in eval_receipt.get("diagnostics", []):
            question = diagnostic.get("question_id", "")
            if not question.startswith(RELATION_PREFIX):
                continue
            peer = peer_by_id.get(diagnostic.get("comparison_id"))
            if peer is None:
                raise ValueError("Frozen relation diagnostic has no matching comparison snapshot")
            comparisons[question] = {
                "scope": peer.get("context", {}).get("scope", ""),
                "temporal_scope": peer.get("context", {}).get("temporal_scope", ""),
            }
        result.append(
            {
                "case_id": row["case_id"],
                "source_kind": source_case["origin"],
                "candidate": {
                    "scope": source.get("scope", ""),
                    "temporal_scope": source.get("temporal_scope", ""),
                    "evidence_quote": source.get("evidence_quote", ""),
                    "source_text": source_case.get("parent", ""),
                },
                "comparisons": comparisons,
                "diagnostics": eval_receipt.get("diagnostics", []),
                "context_issues": receipt.get("context_issues", []),
                "legacy_assessment": eval_receipt.get("status", "unknown"),
                "provider_calls": row["provider_calls"],
            }
        )
    return result


def _conversation_guard_cases(root: Path) -> list[dict[str, Any]]:
    results = json.loads((root / "results.json").read_text(encoding="utf-8"))
    cases = json.loads((root / "contract.json").read_text(encoding="utf-8"))["cases"]
    by_id = {str(c["id"]): c for c in cases}
    result = []
    for row in results:
        if row.get("provider_calls"):
            continue
        source_case = by_id[row["case_id"]]
        source = source_case["data"]
        receipt = row["receipt"]
        result.append(
            {
                "case_id": row["case_id"],
                "source_kind": "recorded_conversation_nomination_context_guard",
                "candidate": {
                    "scope": source.get("scope", ""),
                    "temporal_scope": source.get("temporal_scope", ""),
                    "evidence_quote": source.get("evidence_quote", ""),
                    "source_text": source_case.get("parent", ""),
                },
                "comparisons": {},
                "diagnostics": [],
                "context_issues": receipt.get("context_issues", []),
                "legacy_assessment": "not_called_context_guard",
                "provider_calls": 0,
            }
        )
    return result


def build(challenge_root: Path, conversation_root: Path, guarded_root: Path) -> dict[str, Any]:
    inputs = (
        _challenge_cases(challenge_root)
        + _conversation_cases(conversation_root)
        + _conversation_guard_cases(guarded_root)
    )
    if not inputs:
        raise ValueError("No sealed successful provider assessments found")
    output = [assess_case(case) for case in inputs]
    counter = Counter()
    for row in output:
        counter["cases"] += 1
        counter["legacy_aggregate_passes"] += int(row["legacy_aggregate_gate_passed"])
        counter["shadow_cases_with_retained_dimensions"] += int(bool(row["shadow_retained"]))
        counter["shadow_retained_dimensions"] += len(row["shadow_retained"])
        counter["unresolved_dimensions"] += len(row["unresolved"])
        counter["context_blocked_cases"] += int(not row["candidate_context_valid"])
        counter[f"source:{row['source_kind']}:cases"] += 1
        counter[f"source:{row['source_kind']}:provider_calls"] += int(row.get("provider_calls", 0))
        counter[f"source:{row['source_kind']}:retained_dimensions"] += len(row["shadow_retained"])
        counter[f"source:{row['source_kind']}:retained_cases"] += int(bool(row["shadow_retained"]))
    by_dimension: dict[str, dict[str, int]] = {}
    for row in output:
        for dimension in row["shadow_retained"] + row["unresolved"]:
            summary = by_dimension.setdefault(dimension["dimension"], {"retained_for_shadow": 0, "unresolved": 0})
            summary[dimension["status"]] += 1
    return {
        "schema_version": 1,
        "independent_gold": False,
        "floor": FLOOR,
        "policy_change": False,
        "adoption_decisions": 0,
        "new_provider_calls": 0,
        "summary": dict(counter),
        "by_dimension": by_dimension,
        "cases": output,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--challenge", type=Path, required=True)
    parser.add_argument("--conversation", type=Path, required=True)
    parser.add_argument("--conversation-guards", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    roots = [args.challenge.resolve(), args.conversation.resolve(), args.conversation_guards.resolve()]
    body = {
        "source_roots": [str(p) for p in roots],
        "source_sha256": {
            str(p): {relative: _sha(p / relative) for relative in files}
            for p, files in (
                (
                    roots[0],
                    ["contract.json", "combined-intake.json"]
                    + [x.relative_to(roots[0]).as_posix() for x in sorted(roots[0].glob("jev-*.json"))],
                ),
                (
                    roots[1],
                    ["contract.json", "results.json"]
                    + [x.relative_to(roots[1]).as_posix() for x in sorted(roots[1].glob("provider-*.json"))],
                ),
                (roots[2], ["contract.json", "results.json"]),
            )
        },
        "result": build(*roots),
    }
    body["run_sha256"] = digest(body)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(body, indent=2), encoding="utf-8")
    print(json.dumps(body["result"]["summary"], indent=2))


if __name__ == "__main__":
    main()
