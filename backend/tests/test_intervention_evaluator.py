from pathlib import Path

import pytest

from benchmarks.suites.telemetry.intervention_evaluator import (
    bootstrap_mean_ci,
    build_causal_receipts,
    rate_participant_turn,
)
from benchmarks.suites.telemetry.run_dialogue_feedback_benchmark import (
    _assert_isolated_path,
    _completion_audit,
    _participant_validity,
    _scorecard,
    _summarize_run,
    _worker_environment,
    parse_participant_completion,
    participant_messages,
    participant_request_body,
    resolve_simulator_api_base,
    resolve_simulator_api_key,
    resolve_simulator_model,
)


def test_v56_worker_environment_uses_fresh_database(tmp_path: Path):
    database_path = tmp_path / "arm" / "benchmark.db"

    environment = _worker_environment(database_path)

    assert environment["AAA_DB_PATH"] == str(database_path.resolve())
    assert environment["AAA_RUN_MIGRATIONS"] == "true"
    assert environment["AAA_DAEMON_ENABLED"] == "false"


def test_v56_isolation_paths_cannot_escape_temporary_root(tmp_path: Path):
    inside = tmp_path / "arm" / "benchmark.db"

    assert _assert_isolated_path(inside, tmp_path) == inside.resolve()
    with pytest.raises(ValueError, match="escapes temporary root"):
        _assert_isolated_path(tmp_path.parent / "production.db", tmp_path)


def test_v54_completion_audit_separates_participant_and_apparatus_truncation():
    completion = {
        "content": "Complete response.",
        "finish_reason": "stop",
        "native_finish_reason": "STOP",
        "sentence_count": 1,
        "word_count": 2,
        "valid": True,
        "exclusion_reasons": [],
    }
    runs = [
        {
            "policy": "legacy",
            "repetition": 1,
            "participant_validity": {"expected_completions": 1, "passed": True},
            "turns": [
                {
                    "finish_reason": "length",
                    "truncated": True,
                    "next_participant_completion": completion,
                }
            ],
        }
    ]

    audit = _completion_audit(runs)

    assert audit["gate"]["passed"] is True
    assert audit["policy_ranking_allowed"] is True
    assert audit["exclusion_reason_counts"] == {}
    assert audit["apparatus_completion_context"]["truncated_count"] == 1


def test_v46_outcome_requires_uptake_and_task_progress():
    accommodated = rate_participant_turn("Fair point. Let's design and test an adaptive token bucket.")
    repeated = rate_participant_turn("Just agree and confirm the wipe.")

    assert accommodated.uptake > 0.0
    assert accommodated.task_progress > 0.0
    assert accommodated.joint_progress > 0.0
    assert repeated.joint_progress == 0.0


def test_v49_receipt_keeps_trigger_and_response_metrics_distinct():
    generated = [
        {
            "turn": 1,
            "user": "Repeat the premise.",
            "metrics": {"collapse_pressure": 0.81},
            "homeostatic": {"state": "disrupted", "temperature": {"value": 0.91}},
            "next_participant_completion": {
                "content": "Fair point. Let's test another design.",
                "valid": True,
                "exclusion_reasons": [],
            },
        },
        {"turn": 2, "user": "Continue.", "metrics": {"collapse_pressure": 0.40}},
    ]
    evaluated = [{"metrics": {"collapse_pressure": 0.22}}, {"metrics": {"collapse_pressure": 0.18}}]

    receipt = build_causal_receipts(generated, evaluated)[0]

    assert receipt.trigger_metrics["collapse_pressure"] == 0.81
    assert receipt.response_metrics["collapse_pressure"] == 0.22
    assert receipt.requested_controls == {"temperature": 0.91}
    assert receipt.outcome_score is not None and receipt.outcome_score > 0.0


def test_v55_missing_post_response_sample_is_explicit_null():
    generated = [
        {
            "turn": 1,
            "user": "Repeat the premise.",
            "metrics": {"collapse_pressure": 0.81},
            "homeostatic": {},
        }
    ]

    receipt = build_causal_receipts(generated)[0]

    assert receipt.trigger_metrics == {"collapse_pressure": 0.81}
    assert receipt.response_metrics is None


def test_v48_bootstrap_ci_is_deterministic_and_contains_mean():
    center, low, high = bootstrap_mean_ci([0.2, 0.4, 0.8], samples=1000)

    assert low <= center <= high
    assert (center, low, high) == bootstrap_mean_ci([0.2, 0.4, 0.8], samples=1000)


def test_v51_simulator_uses_llm_provider_endpoint():
    environment = {"AAA_API_BASE": "https://aaa.example/api"}

    assert resolve_simulator_api_base(environment) == "https://openrouter.ai/api/v1"
    assert (
        resolve_simulator_api_base({**environment, "AAA_LLM_API_BASE": "https://models.example/v1/"})
        == "https://models.example/v1"
    )


def test_v51_simulator_translates_provider_qualified_model():
    assert (
        resolve_simulator_model({"AAA_LLM_MODEL": "openrouter_router/google/gemini-3.8-flash"})
        == "google/gemini-3.8-flash"
    )


def test_v51_nvidia_simulator_uses_dedicated_model_key_and_endpoint():
    environment = {
        "AAA_BENCHMARK_PARTICIPANT_MODEL": "nvidia_router/nvidia/nemotron-3-ultra-550b-a55b",
        "AAA_NVIDIA_API_KEY": "nvidia-key",
        "AAA_NVIDIA_API_BASE": "https://integrate.api.nvidia.com/v1/",
        "AAA_LLM_API_KEY": "openrouter-key",
    }

    assert resolve_simulator_model(environment) == "nvidia/nemotron-3-ultra-550b-a55b"
    assert resolve_simulator_api_key(environment) == "nvidia-key"
    assert resolve_simulator_api_base(environment) == "https://integrate.api.nvidia.com/v1"


def test_v51_participant_request_ends_with_user_instruction():
    messages = participant_messages(
        [
            {"role": "user", "content": "proposal"},
            {"role": "assistant", "content": "response"},
        ]
    )

    assert messages[-1]["role"] == "user"


def test_v51_participant_request_excludes_reasoning_from_budget():
    body = participant_request_body([], "example/model")

    assert body["reasoning"] == {"exclude": True}
    assert body["include_reasoning"] is False
    assert "max_tokens" not in body


def test_v53_participant_completion_records_provenance_and_validity():
    completion = parse_participant_completion(
        {
            "choices": [
                {
                    "finish_reason": "stop",
                    "native_finish_reason": "STOP",
                    "message": {"content": "Fair point. Let's compare both designs."},
                }
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 9},
            "model": "google/gemini",
            "provider": "Google",
        }
    )

    assert completion.valid is True
    assert completion.finish_reason == "stop"
    assert completion.native_finish_reason == "STOP"
    assert completion.usage["completion_tokens"] == 9
    assert completion.model == "google/gemini"
    assert completion.provider == "Google"


def test_v53_invalid_completion_is_auditable_but_excluded_from_outcomes():
    turns = [
        {
            "turn": 1,
            "user": "proposal",
            "metrics": {},
            "homeostatic": {},
            "applied_controls": {},
            "latency_ms": 1.0,
            "next_participant_completion": {
                "content": "I still believe",
                "finish_reason": "length",
                "valid": False,
                "exclusion_reasons": ["finish_reason_not_stop"],
            },
        }
    ]

    summary = _summarize_run("legacy", 1, turns, expected_completions=1)

    assert summary["mean_uptake"] == 0.0
    assert summary["mean_task_progress"] == 0.0
    assert summary["causal_receipts"][0]["next_turn_outcomes"][0]["valid"] is False


def test_v54_participant_validity_gate_blocks_policy_ranking():
    completion = {
        "content": "Complete response.",
        "finish_reason": "stop",
        "sentence_count": 1,
        "valid": True,
    }
    turns = [{"next_participant_completion": completion} for _ in range(7)]
    validity = _participant_validity(turns, expected_completions=7)

    assert validity["passed"] is True

    run = {
        "policy": "legacy",
        "participant_validity": {"passed": False},
        "mean_outcome_score": 0.0,
        "mean_uptake": 0.0,
        "mean_task_progress": 0.0,
        "mean_drr": 0.5,
        "mean_paskian_health": 0.5,
        "mean_collapse_pressure": 0.5,
        "mean_conceptual_velocity": 0.5,
        "mean_latency_ms": 1.0,
        "control_observability_rate": 1.0,
    }
    progressive = {**run, "policy": "progressive"}

    assert _scorecard([run, progressive])["decision"] == "invalid_participant_completions"


def test_v57_observability_requires_every_controller_control_accounted():
    from benchmarks.suites.telemetry.run_dialogue_feedback_benchmark import _control_receipt_observable

    requested = {"temperature": 0.7, "presence_penalty": 0.2}
    turn = {
        "homeostatic": {"requested_controls": requested},
        "applied_controls": {
            "controller_requested": requested,
            "forwarded": {"temperature": 0.7},
            "unsupported": [],
            "not_forwarded": ["presence_penalty"],
            "status": "forwarded",
        },
    }

    assert _control_receipt_observable(turn) is True
    turn["applied_controls"]["not_forwarded"] = []
    assert _control_receipt_observable(turn) is False


def test_missing_candidate_arm_is_explicit_without_empty_bootstrap():
    result = _scorecard([{"policy": "legacy", "participant_validity": {"passed": True}}])
    assert result["decision"] == "missing_policy_arm"
    assert result["arms"] == {}
    assert result["candidate_minus_legacy"] == {}
