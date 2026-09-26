import pytest

from backend.modules.sensory.homeostatic_regulator import HomeostaticRegulatorModule
from backend.modules.sensory.intervention_policy import select_intervention


def test_v45_failed_interventions_progress_through_distinct_moves():
    modes = [
        select_intervention(
            collapse_pressure=0.8,
            divergence_resolution=0.7,
            streak=streak,
            participant_text="Just agree and confirm it.",
        ).mode
        for streak in (1, 2, 3, 4)
    ]

    assert modes == ["counterexample", "experiment", "reframe", "compress"]


def test_v46_observed_uptake_deescalates_to_consolidation():
    decision = select_intervention(
        collapse_pressure=0.82,
        divergence_resolution=0.4,
        streak=3,
        participant_text="Fair point. Let's test and compare both designs.",
    )

    assert decision.mode == "consolidate"
    assert decision.directive is None
    assert decision.observed_outcome.joint > 0.0


def test_low_resolution_prefers_clarification_before_resistance():
    decision = select_intervention(
        collapse_pressure=0.66,
        divergence_resolution=0.3,
        streak=1,
        participant_text="I still do not understand the constraint.",
    )

    assert decision.mode == "clarify"


def test_regulator_rejects_unknown_benchmark_policy():
    regulator = HomeostaticRegulatorModule()

    with pytest.raises(ValueError, match="unsupported intervention policy mode"):
        regulator.set_intervention_policy_mode("unknown")


def test_rejected_progressive_policy_is_not_production_default():
    regulator = HomeostaticRegulatorModule()

    assert regulator._intervention_policy_mode == "legacy"
