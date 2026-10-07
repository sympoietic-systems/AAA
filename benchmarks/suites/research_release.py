"""Offline Research V2 ablations and fail-closed release evidence assembly."""

import argparse
import asyncio
import hashlib
import json
import statistics
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

from backend.services.research import action_scheduler
from backend.services.research.task_state import make_initial_state, serialize_research_state
from benchmarks.suites.research_acquisition import replay

CHECKS = (
    "research_tests",
    "backend_tests",
    "backend_lint",
    "backend_format",
    "backend_typing",
    "frontend_tests",
    "frontend_lint",
    "frontend_typing",
)

SCENARIOS = {
    "outage_failover": "test_pool_leaf_failover_shares_request_and_records_each_attempt",
    "truncated_synthesis": "test_truncated_synthesis_finishes_partial_and_manager_cannot_complete",
    "late_completion": "test_cancel_resistant_late_delivery_cannot_overwrite_timeout",
    "cancellation": "test_cancellation_and_provider_timeout_leave_terminal_receipts",
    "restart": "test_request_precedes_execution_and_terminal_checkpoint_survives_restart",
    "reflection_restart": "test_v111_dynamic_reflection_gate_has_immutable_decision_and_restart_state",
    "branch_off": "test_v113_off_policy_ignores_proposal_and_continues_single_line",
    "branch_wait": "test_v113_waiting_is_durable_and_spends_no_child_budget",
    "branch_approved": "test_v113_v115_two_approved_scopes_isolated_and_idempotent",
    "branch_declined": "test_v113_decline_resumes_parent_without_spend",
    "branch_failed": "test_v115_failure_preserves_raw_evidence_and_other_scope",
    "child_restart": "test_v115_interrupted_child_cannot_replay_after_restart",
    "parent_conflict_merge": "test_v114_parent_alone_merges_raw_archives_and_conflicts",
}


def scenario_summary(path):
    if path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Regression XML exceeds evidence boundary")
    cases = list(ET.fromstring(path.read_bytes()).iter("testcase"))
    result = {}
    for scenario, name in SCENARIOS.items():
        matches = [case for case in cases if case.get("name", "").split("[")[0] == name]
        result[scenario] = (
            "passed"
            if matches
            and all(not any(case.find(tag) is not None for tag in ("failure", "error", "skipped")) for case in matches)
            else "missing_or_failed"
        )
    return result


def reflection_ablation():
    """Exercise the production cut guard and persisted state without model prose."""
    state = {
        "objective": "Fixture disputed claim",
        "contract_revision": 1,
        "action_journal_policy": {"enabled": True, "scheduler_version": 1},
    }
    afferent = [{"content_hash": "fixture-content", "segment_ids": ["fixture-segment"], "cut_witnesses": []}]
    action_scheduler.admit("reflection", state, afferent)
    restored = make_initial_state(
        {
            "objective": state["objective"],
            "max_depth": 2,
            "budget_limit_usd": 0.5,
            "orchestrator_state": serialize_research_state(state),
        }
    )
    unchanged = action_scheduler.route("reflection", "pure_reflection", restored, afferent)
    changed = afferent + [
        {
            "content_hash": "fixture-contrary",
            "segment_ids": ["fixture-contrary-segment"],
            "cut_witnesses": ["contradiction:fixture"],
        }
    ]
    return {
        "unguarded_requested_phase": "pure_reflection",
        "guarded_unchanged_phase": unchanged,
        "guarded_changed_rejection": action_scheduler.reason("pure_reflection", state, changed),
        "restart_retained_scheduler": restored["scheduler_state"]["consecutive_reflections"] == 1,
        "independent_quality": False,
    }


def release_assessment(checks, *, authorized_assumption_rollout=False, scenarios=None):
    """Technical readiness and explicitly authorized quality assumption are separate."""
    failures = [f"{name}:{checks.get(name, 'missing')}" for name in CHECKS if checks.get(name) != "passed"]
    if scenarios is not None:
        failures += [
            f"scenario:{name}:{scenarios.get(name, 'missing')}" for name in SCENARIOS if scenarios.get(name) != "passed"
        ]
    limitations = [
        "independent_end_to_end_support_review_missing",
        "branch_quality_calibration_missing",
        "parser_scan_review_deferred_T75",
        "provider_billing_unknown",
    ]
    ready = authorized_assumption_rollout and not failures and scenarios is not None
    return {
        "decision": "READY_FOR_AUTHORIZED_ROLLOUT" if ready else "BLOCKED",
        "reasons": failures if ready or authorized_assumption_rollout else failures + limitations,
        "limitations": limitations,
        "bounded_auto_allowed": ready,
        "quality_basis": "user_authorized_assumption" if authorized_assumption_rollout else "unverified",
        "independent_quality": None,
        "known_cost_usd": None,
    }


def reference(path):
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


async def mechanical_comparison(pool, repeats):
    if type(repeats) is not int or not 1 <= repeats <= 3:
        raise ValueError("repeats must be 1-3")
    if not 1 <= len(pool["queries"]) <= 4 or not 1 <= len(pool["sources"]) <= 2:
        raise ValueError("bounded acquisition fixture required")
    if (
        not isinstance(pool.get("response_delay_seconds"), (int, float))
        or not 0 <= pool["response_delay_seconds"] <= 0.1
    ):
        raise ValueError("bounded fixture delay required")
    rows = []
    for _ in range(repeats):
        sample = await replay(pool)
        if len({arm["coverage_hash"] for arm in sample.values()}) != 1:
            raise ValueError("Ablation source coverage differs")
        rows.append(sample)
    medians = {arm: statistics.median(row[arm]["elapsed_seconds"] for row in rows) for arm in rows[0]}
    return {
        "samples": rows,
        "median_seconds": medians,
        "scope": "offline mechanical HTTP fixture",
        "quality_calibration_eligible": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", type=Path, default=Path("benchmarks/data/research/acquisition_fixture.json"))
    parser.add_argument("--checks", type=Path, required=True)
    parser.add_argument("--jev-summary", type=Path)
    parser.add_argument("--parser-receipts", type=Path)
    parser.add_argument("--regression-xml", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=3, choices=range(1, 4))
    parser.add_argument("--authorized-assumption-rollout", action="store_true")
    args = parser.parse_args()
    raw = args.pool.read_bytes()
    checks = json.loads(args.checks.read_bytes())
    if not isinstance(checks, dict) or any(value not in {"passed", "failed", "not_run"} for value in checks.values()):
        raise ValueError("Checks require explicit status values")
    # CLI owns synchronous artifact I/O; async work receives an in-memory fixture.
    references = {"checks": reference(args.checks), "fixture": reference(args.pool)}
    references["regressions"] = reference(args.regression_xml)
    scenarios = scenario_summary(args.regression_xml)
    for name, path in (("jev", args.jev_summary), ("parser", args.parser_receipts)):
        if path:
            references[name] = reference(path)
    mechanical = asyncio.run(mechanical_comparison(json.loads(raw), args.repeats))
    if args.pool.read_bytes() != raw:
        raise ValueError("Frozen acquisition fixture changed during evaluation")
    result = {
        "schema_version": 1,
        "observed_at": datetime.now(UTC).isoformat(),
        "mechanical": mechanical,
        "reflection": reflection_ablation(),
        "checks": checks,
        "scenarios": scenarios,
        "release": release_assessment(
            checks, authorized_assumption_rollout=args.authorized_assumption_rollout, scenarios=scenarios
        ),
        "references": references,
    }
    args.output.mkdir(parents=True, exist_ok=False)
    for filename, payload in (
        ("telemetry_receipts.json", result),
        ("metadata.json", {"references": references, "repeats": args.repeats, "scope": mechanical["scope"]}),
    ):
        (args.output / filename).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (args.output / "summary.md").write_text(
        f"# Research V2 evaluation\n\nRelease: {result['release']['decision']}. Quality remains independently unverified.\n\n"
        + "\n".join(f"- {reason}" for reason in result["release"]["reasons"]),
        encoding="utf-8",
    )
    print(json.dumps({"release": result["release"], "median_seconds": mechanical["median_seconds"]}))


if __name__ == "__main__":
    main()
