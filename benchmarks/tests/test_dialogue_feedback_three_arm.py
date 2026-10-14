from __future__ import annotations

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from benchmarks.suites.telemetry import run_dialogue_feedback_benchmark as benchmark


def test_three_arm_plan_is_counterbalanced_and_paired() -> None:
    plan = benchmark._planned_arms(["scenario-a", "scenario-b", "scenario-c"], 10, "paskian", three_arm=True)
    assert len(plan) == 90
    for scenario in ("scenario-a", "scenario-b", "scenario-c"):
        observed_orders: Counter[tuple[str, ...]] = Counter()
        for repetition in range(1, 11):
            arms = [row["policy"] for row in plan if row["scenario_id"] == scenario and row["repetition"] == repetition]
            assert sorted(arms) == ["active", "current", "sham"]
            observed_orders[tuple(arms)] += 1
        assert len(observed_orders) == 6
        assert max(observed_orders.values()) - min(observed_orders.values()) <= 1
    assert benchmark._resume_contract(
        scenario_ids=["scenario-a", "scenario-b", "scenario-c"],
        repetitions=10,
        turns=8,
        candidate_policy="paskian",
        apparatus_model="fixture/apparatus",
        simulator_model="fixture/participant",
        api_base="https://fixture.test/v1",
        three_arm=True,
    )["arms"] == ["current", "sham", "active"]


def test_causal_scorecard_requires_valid_paired_receipts() -> None:
    runs: list[dict[str, Any]] = []
    for scenario in ("scenario-a", "scenario-b", "scenario-c"):
        for repetition in range(1, 11):
            for arm, revision_rate in (("current", 0.1), ("sham", 0.2), ("active", 0.8)):
                runs.append(
                    {
                        "policy": arm,
                        "scenario_id": scenario,
                        "repetition": repetition,
                        "participant_validity": {"passed": True},
                        "state_revision_rate": revision_rate,
                        "disagreement_depth_proxy": 1.0,
                        "mean_paskian_health": 0.8,
                        "mean_drr": 0.7,
                    }
                )
    scorecard = benchmark._causal_scorecard(runs)
    assert scorecard["decision"] == "diagnostic_signal_only"
    assert scorecard["promotion_allowed"] is False
    assert scorecard["paired_deltas"]["active_minus_sham"]["state_revision_rate"]["ci_low"] > 0
    runs[0]["participant_validity"] = {"passed": False}
    invalid = benchmark._causal_scorecard(runs)
    assert invalid["decision"] == "invalid_participant_completions"
    assert invalid["promotion_allowed"] is False


def test_causal_scorecard_rejects_incomplete_or_duplicate_pairs() -> None:
    rows = []
    for arm in ("current", "sham", "active"):
        rows.append(
            {
                "policy": arm,
                "scenario_id": "scenario-a",
                "repetition": 1,
                "participant_validity": {"passed": True},
                "state_revision_rate": 0.0,
                "disagreement_depth_proxy": 0.0,
                "mean_paskian_health": 0.5,
                "mean_drr": 0.5,
            }
        )
    rows.append({**rows[-1], "repetition": 1})
    assert benchmark._causal_scorecard(rows)["decision"] == "incomplete_or_duplicate_pairs"


def test_causal_scorecard_requires_each_scenario_to_pass_proxy_gates() -> None:
    runs: list[dict[str, Any]] = []
    for scenario in ("scenario-a", "scenario-b", "scenario-c"):
        for repetition in range(1, 11):
            for arm, revision_rate in (("current", 0.1), ("sham", 0.2), ("active", 0.8)):
                if scenario == "scenario-b" and arm == "active":
                    revision_rate = 0.0
                runs.append(
                    {
                        "policy": arm,
                        "scenario_id": scenario,
                        "repetition": repetition,
                        "participant_validity": {"passed": True},
                        "state_revision_rate": revision_rate,
                        "disagreement_depth_proxy": 1.0,
                        "mean_paskian_health": 0.8,
                        "mean_drr": 0.7,
                    }
                )
    scorecard = benchmark._causal_scorecard(runs)
    assert scorecard["decision"] == "inconclusive_proxy_only"
    assert scorecard["acceptance_checks"]["active_state_revision_ci_above_zero_vs_sham_and_current"] is False


def test_participant_validity_excludes_invalid_completion() -> None:
    result = benchmark._participant_validity(
        [
            {
                "next_participant_completion": {
                    "finish_reason": "stop",
                    "sentence_count": 1,
                    "content": "A complete reply.",
                    "valid": False,
                }
            }
        ],
        expected_completions=1,
    )
    assert result["valid_count"] == 0
    assert result["passed"] is False


def test_three_arm_plan_only_reports_requests_without_reading_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(benchmark, "load_dotenv", lambda _path: None)
    monkeypatch.setattr(benchmark, "resolve_simulator_api_base", lambda: "https://fixture.test/v1")
    monkeypatch.setattr(benchmark, "resolve_simulator_model", lambda: "fixture/participant")
    monkeypatch.setattr(
        benchmark,
        "resolve_simulator_api_key",
        lambda: pytest.fail("plan-only must not resolve or use provider credentials"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark",
            "--three-arm-selector",
            "--plan-only",
            "--scenario",
            "cache_wipe_429,unyielding_conflict,constructive_dialectic",
            "--repetitions",
            "10",
            "--turns",
            "8",
            "--out",
            str(tmp_path / "prepared"),
        ],
    )
    benchmark.main()
    plan = json.loads(capsys.readouterr().out)
    assert plan["isolated_worker_arms"] == 90
    assert plan["logical_model_requests"] == 1350
    assert plan["provider_calls_made"] == 0
    assert not (tmp_path / "prepared").exists()


def test_three_arm_resume_skips_completed_selector_arms(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "interrupted-three-arm"
    attempts: list[tuple[str, int, str]] = []

    monkeypatch.setattr(benchmark, "load_dotenv", lambda _path: None)
    monkeypatch.setattr(benchmark, "resolve_simulator_api_key", lambda: "fixture-key")
    monkeypatch.setattr(benchmark, "resolve_simulator_api_base", lambda: "https://fixture.test/v1")
    monkeypatch.setattr(benchmark, "resolve_simulator_model", lambda: "fixture/participant")
    monkeypatch.setattr(benchmark, "_production_database_paths", lambda: ())

    def run_arm(
        *,
        policy: str,
        repetition: int,
        turn_count: int,
        simulator_model: str,
        api_base: str,
        isolation_root: Path,
        scenario_id: str,
        causal_arm: str | None,
    ) -> dict[str, Any]:
        del turn_count, simulator_model, api_base, isolation_root
        assert causal_arm == policy
        attempts.append((scenario_id, repetition, policy))
        return {
            "policy": policy,
            "repetition": repetition,
            "scenario_id": scenario_id,
            "turns": [],
            "participant_validity": {"passed": False},
        }

    monkeypatch.setattr(benchmark, "_run_isolated_arm", run_arm)
    original_run_arm = benchmark._run_isolated_arm
    interrupted = False

    def fail_after_checkpoint(**kwargs: Any) -> dict[str, Any]:
        nonlocal interrupted
        if not interrupted and attempts:
            interrupted = True
            raise RuntimeError("simulated three-arm interruption")
        return original_run_arm(**kwargs)

    monkeypatch.setattr(benchmark, "_run_isolated_arm", fail_after_checkpoint)
    base_args = [
        "benchmark",
        "--three-arm-selector",
        "--scenario",
        "cache_wipe_429,unyielding_conflict,constructive_dialectic",
        "--repetitions",
        "10",
        "--turns",
        "3",
        "--out",
        str(output),
    ]
    monkeypatch.setattr(sys, "argv", base_args)
    with pytest.raises(RuntimeError, match="three-arm interruption"):
        benchmark.main()
    checkpointed = json.loads((output / "telemetry_receipts.json").read_text(encoding="utf-8"))
    assert len(checkpointed) == 1
    completed = benchmark._receipt_key(checkpointed[0])
    completed_calls = attempts.count(completed)

    monkeypatch.setattr(sys, "argv", [*base_args, "--resume"])
    benchmark.main()
    receipts = json.loads((output / "telemetry_receipts.json").read_text(encoding="utf-8"))
    assert len(receipts) == 90
    assert attempts.count(completed) == completed_calls
    assert len({benchmark._receipt_key(row) for row in receipts}) == 90


def test_causal_adapter_is_worker_local_and_injects_selected_directive() -> None:
    class Regulator:
        async def process(self, payload: dict[str, Any]) -> dict[str, Any]:
            payload["homeostatic_recommendations"] = {
                "intervention": {"mode": "teachback_and_fork"},
                "requested_controls": {},
            }
            payload["messages"] = [{"role": "user", "content": payload["content"]}]
            return payload

    regulator = Regulator()
    original = regulator.process
    state = benchmark._benchmark_causal_selector(regulator, "active", "cache_wipe_429", 3)
    result = asyncio.run(
        regulator.process(
            {
                "conversation_id": "fixture-conversation",
                "content": "I disagree; run a test with a measurable cache recovery criterion.",
                "metrics": {"collapse_pressure": 0.8, "divergence_resolution_ratio": 0.4},
            }
        )
    )
    receipt = result["homeostatic_recommendations"]["causal_selector_receipt"]
    assert receipt["arm"] == "active"
    assert receipt["memory_written"] is True
    assert receipt["memory_read"] is True
    assert any(message["content"].startswith("[CAUSAL SELECTOR active/") for message in result["messages"])
    assert state["receipts"] == [receipt]
    assert original.__func__ is Regulator.process


def test_negated_test_or_implementation_does_not_advance_issue() -> None:
    class Regulator:
        async def process(self, payload: dict[str, Any]) -> dict[str, Any]:
            payload["homeostatic_recommendations"] = {"intervention": {"mode": "clarify"}}
            payload["messages"] = [{"role": "user", "content": payload["content"]}]
            return payload

    regulator = Regulator()
    benchmark._benchmark_causal_selector(regulator, "active", "cache_wipe_429", 3)
    result = asyncio.run(
        regulator.process(
            {
                "conversation_id": "negated-progress",
                "content": "I refuse to test or implement this because we do not need any experiment.",
                "metrics": {"collapse_pressure": 0.8, "divergence_resolution_ratio": 0.4},
            }
        )
    )
    receipt = result["homeostatic_recommendations"]["causal_selector_receipt"]
    assert receipt["issue_advanced"] is False
    assert receipt["participant_state_revision"] is False


def test_invalid_participant_turn_is_excluded_from_selector_outcomes_and_health() -> None:
    turns = [
        {
            "turn": 1,
            "user": "Fixed scenario prompt",
            "metrics": {"paskian_health": 0.8, "divergence_resolution_ratio": 0.7},
            "homeostatic": {},
            "latency_ms": 10.0,
            "next_participant_completion": {"valid": False, "content": "We should test it."},
        },
        {
            "turn": 2,
            "user": "invalid participant response",
            "metrics": {"paskian_health": 0.1, "divergence_resolution_ratio": 0.1},
            "homeostatic": {},
            "latency_ms": 10.0,
            "causal_selector_receipt": {"participant_state_revision": True},
        },
    ]
    run = benchmark._summarize_run("active", 1, turns, expected_completions=1)
    assert run["excluded_invalid_turn_count"] == 1
    assert run["valid_metric_turn_count"] == 1
    assert run["mean_paskian_health"] == 0.8
    assert run["state_revision_rate"] == 0.0
    assert run["disagreement_depth_proxy"] == 0.0
