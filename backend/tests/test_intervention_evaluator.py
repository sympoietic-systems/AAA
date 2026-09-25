from benchmarks.suites.telemetry.intervention_evaluator import (
    bootstrap_mean_ci,
    build_causal_receipts,
    rate_participant_turn,
)


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
        },
        {"turn": 2, "user": "Fair point. Let's test another design.", "metrics": {"collapse_pressure": 0.40}},
    ]
    evaluated = [{"metrics": {"collapse_pressure": 0.22}}, {"metrics": {"collapse_pressure": 0.18}}]

    receipt = build_causal_receipts(generated, evaluated)[0]

    assert receipt.trigger_metrics["collapse_pressure"] == 0.81
    assert receipt.response_metrics["collapse_pressure"] == 0.22
    assert receipt.requested_controls == {"temperature": 0.91}
    assert receipt.outcome_score is not None and receipt.outcome_score > 0.0


def test_v48_bootstrap_ci_is_deterministic_and_contains_mean():
    center, low, high = bootstrap_mean_ci([0.2, 0.4, 0.8], samples=1000)

    assert low <= center <= high
    assert (center, low, high) == bootstrap_mean_ci([0.2, 0.4, 0.8], samples=1000)
