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
    contract = benchmark._resume_contract(
        scenario_ids=["scenario-a", "scenario-b", "scenario-c"],
        repetitions=10,
        turns=8,
        candidate_policy="paskian",
        apparatus_model="fixture/apparatus",
        simulator_model="fixture/participant",
        api_base="https://fixture.test/v1",
        three_arm=True,
    )
    assert contract["participant_format_version"] == 3
    assert contract["participant_length_policy"] == "long_form_allowed"
    assert contract["apparatus_max_output_tokens"] == 2048


def test_three_arm_participant_request_preserves_natural_length() -> None:
    body = benchmark.participant_request_body(
        [{"role": "assistant", "content": "State the cache decision and a validation criterion."}],
        "fixture/participant",
        api_base="https://integrate.api.nvidia.com/v1",
        participant_system="Act as the engineering lead. Reply to the system's latest argument in 1-3 sentences.",
    )

    assert body["messages"][0]["content"].endswith("Reply to the system's latest argument in 1-3 sentences.")
    assert "max_tokens" not in body


def test_t38_accepts_long_complete_participant_replies_and_reports_length_descriptively() -> None:
    content = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
    parsed = benchmark.parse_participant_completion(
        {
            "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
            "model": "fixture/participant",
            "provider": "nvidia",
            "usage": {"completion_tokens": 20},
        },
        allow_long_replies=True,
    )
    short_form = benchmark.parse_participant_completion(
        {
            "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
            "model": "fixture/participant",
            "provider": "nvidia",
            "usage": {"completion_tokens": 20},
        }
    )
    turns = [{"next_participant_completion": parsed.to_dict()}]

    assert parsed.valid is True
    assert short_form.valid is False
    assert benchmark._participant_validity(turns, 1, allow_long_replies=True) == {
        "expected_completions": 1,
        "completion_count": 1,
        "valid_count": 1,
        "stop_rate": 1.0,
        "format_rate": 0.0,
        "format_gate_applied": False,
        "valid_rate": 1.0,
        "empty_count": 0,
        "passed": True,
    }
    assert benchmark._participant_validity(turns, 1)["passed"] is False


def test_t38_resume_migration_requires_matching_model_budget_and_complete_receipt() -> None:
    expected = benchmark._resume_contract(
        scenario_ids=["scenario"],
        repetitions=10,
        turns=8,
        candidate_policy="paskian",
        apparatus_model="nvidia_router/nvidia/nemotron-test",
        simulator_model="nvidia/nemotron-test",
        api_base="https://integrate.api.nvidia.com/v1",
        three_arm=True,
    )
    legacy = {
        key: value
        for key, value in expected.items()
        if key not in {"participant_format_version", "participant_length_policy", "apparatus_max_output_tokens"}
    }
    legacy["schema_version"] = 1
    completion = {
        "content": "One. Two. Three. Four.",
        "finish_reason": "stop",
        "native_finish_reason": "stop",
        "usage": {"completion_tokens": 8},
        "model": "nvidia/nemotron-test",
        "provider": "nvidia",
        "valid": False,
        "exclusion_reasons": ["sentence_count_out_of_range"],
    }
    turn = {
        "model": "nvidia/nemotron-test",
        "provider": "model_pool_nvidia",
        "applied_controls": {"forwarded": {"max_tokens": 2048}},
        "next_participant_completion": completion,
    }
    run_turns = [dict(turn) for _ in range(7)]
    run_turns.append({key: value for key, value in turn.items() if key != "next_participant_completion"})
    run = {"policy": "active", "turns": run_turns}

    assert benchmark._can_migrate_t38_length_policy(legacy, expected, [run]) is True
    run["turns"][0]["provider"] = "model_pool_openrouter"
    assert benchmark._can_migrate_t38_length_policy(legacy, expected, [run]) is False
    run["turns"][0]["provider"] = "model_pool_nvidia"
    run["turns"][0].pop("next_participant_completion")
    assert benchmark._can_migrate_t38_length_policy(legacy, expected, [run]) is False


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


def test_apparatus_budget_validation_accepts_only_recorded_bounded_retry_sequence() -> None:
    assert benchmark._valid_apparatus_budget_controls({"forwarded": {"max_tokens": 2048}}, 2048)
    assert benchmark._valid_apparatus_budget_controls(
        {
            "requested": {"max_tokens": 2048},
            "forwarded": {"max_tokens": 4096},
            "truncation_retries": [{"from": 2048, "to": 4096}],
        },
        2048,
    )
    assert benchmark._valid_apparatus_budget_controls(
        {
            "requested": {"max_tokens": 2048},
            "forwarded": {"max_tokens": 8192},
            "truncation_retries": [{"from": 2048, "to": 4096}, {"from": 4096, "to": 8192}],
        },
        2048,
    )
    assert not benchmark._valid_apparatus_budget_controls(
        {
            "requested": {"max_tokens": 2048},
            "forwarded": {"max_tokens": 8192},
            "truncation_retries": [{"from": 2048, "to": 8192}],
        },
        2048,
    )
    assert not benchmark._valid_apparatus_budget_controls({"forwarded": {"max_tokens": 16384}}, 2048)


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


def test_worker_environment_locks_apparatus_fallback_to_benchmark_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AAA_BENCHMARK_MODEL", "nvidia_router/nvidia/nemotron-test")

    environment = benchmark._worker_environment(tmp_path / "benchmark.db")

    assert environment["AAA_LLM_MODELS"] == "nvidia_router/nvidia/nemotron-test"
    assert environment["AAA_LLM_FALLBACK_MODEL"] == "nvidia_router/nvidia/nemotron-test"


def test_interrupted_worker_directory_is_cleaned_and_completed_receipt_reused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    isolation_root = tmp_path / "isolated"
    arm_root = isolation_root / "r1_scenario_current"
    arm_root.mkdir(parents=True)
    (arm_root / "partial.db").write_text("incomplete", encoding="utf-8")
    calls = 0

    def complete_worker(command: list[str], **_kwargs: Any) -> None:
        nonlocal calls
        calls += 1
        assert not (arm_root / "partial.db").exists()
        output_path = Path(command[command.index("--worker-output") + 1])
        output_path.write_text(
            json.dumps({"policy": "current", "repetition": 1, "scenario_id": "scenario"}),
            encoding="utf-8",
        )

    monkeypatch.setattr(benchmark.subprocess, "run", complete_worker)
    kwargs = {
        "policy": "current",
        "repetition": 1,
        "turn_count": 3,
        "simulator_model": "fixture/participant",
        "api_base": "https://fixture.test/v1",
        "isolation_root": isolation_root,
        "scenario_id": "scenario",
        "causal_arm": "current",
    }

    first = benchmark._run_isolated_arm(**kwargs)
    second = benchmark._run_isolated_arm(**kwargs)

    assert first == second
    assert calls == 1


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
        turns = []
        for turn_index in range(3):
            turn: dict[str, Any] = {
                "scenario_id": scenario_id,
                "turn": turn_index + 1,
                "latency_ms": 1.0,
                "metrics": {
                    "paskian_health": 0.5,
                    "divergence_resolution_ratio": 0.5,
                    "collapse_pressure": 0.2,
                    "conceptual_velocity": 0.3,
                },
                "homeostatic": {},
            }
            if turn_index < 2:
                turn["next_participant_completion"] = {
                    "content": "A complete fixture response.",
                    "sentence_count": 1,
                    "finish_reason": "stop",
                    "model": "fixture/participant",
                    "provider": "fixture",
                    "usage": {"completion_tokens": 4},
                    "valid": True,
                    "exclusion_reasons": [],
                }
            turns.append(turn)
        return benchmark._summarize_run(
            policy,
            repetition,
            turns,
            scenario_id=scenario_id,
            expected_completions=2,
            allow_long_participant_replies=True,
        )

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
