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
            policy_mode="progressive",
        ).mode
        for streak in (1, 2, 3, 4)
    ]

    assert modes == ["counterexample", "experiment", "reframe", "compress"]


def test_v70_paskian_teachback_and_fork_structure():
    decision = select_intervention(
        collapse_pressure=0.75,
        divergence_resolution=0.45,
        streak=2,
        participant_text="Just wipe the cache and restart, stop lecturing me.",
        policy_mode="paskian",
    )

    assert decision.mode == "teachback_and_fork"
    assert decision.directive is not None
    # 3-beat movement checks
    assert "RECONSTRUCT (Teachback)" in decision.directive
    assert "DELIMIT (The Agential Cut)" in decision.directive
    assert "ACCOMMODATE (The Operational Fork)" in decision.directive
    assert "discriminating test" in decision.directive


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
        collapse_pressure=0.55,
        divergence_resolution=0.3,
        streak=1,
        participant_text="I still do not understand the constraint.",
        policy_mode="progressive",
    )

    assert decision.mode == "clarify"


def test_regulator_rejects_unknown_benchmark_policy():
    regulator = HomeostaticRegulatorModule()

    with pytest.raises(ValueError, match="unsupported intervention policy mode"):
        regulator.set_intervention_policy_mode("unknown")


def test_rejected_progressive_policy_is_not_production_default():
    regulator = HomeostaticRegulatorModule()

    assert regulator._intervention_policy_mode == "legacy"


def test_v73_pole_vacancy_escalation_ladder():
    text = "You are completely right, whatever you think is best! Absolutely brilliant."

    # Rung 1: Diffractive Probe on initial detection (streak=0)
    d1 = select_intervention(collapse_pressure=0.60, divergence_resolution=0.50, streak=0, participant_text=text)
    assert d1.mode == "diffractive_probe"
    assert d1.directive is not None
    assert "unanswerable by 'yes'" in d1.directive
    assert d1.observed_outcome.uptake == 0.0

    # Rung 2: Laconic Bracket & Sycophancy Rupture on sustained pole vacancy (streak=1)
    d2 = select_intervention(collapse_pressure=0.70, divergence_resolution=0.45, streak=1, participant_text=text)
    assert d2.mode == "sycophancy_rupture"
    assert d2.directive is not None
    assert "LACONIC BRACKET" in d2.directive
    assert "DEMAND ADVERSARIAL CONTENT" in d2.directive
    assert "somatic-alert" in d2.directive
    assert "sycophancy_rupture" in d2.directive
    assert d2.observed_outcome.uptake == 0.0

    # Rung 3: Quiescent Standby on persistent vacancy (streak>=2)
    d3 = select_intervention(collapse_pressure=0.85, divergence_resolution=0.40, streak=2, participant_text=text)
    assert d3.mode == "quiesce"
    assert d3.directive is not None
    assert "somatic-alert" in d3.directive
    assert "quiescence" in d3.directive
    assert "WITHHOLD GENERATIVE OUTPUT" in d3.directive
    assert d3.observed_outcome.uptake == 0.0


def test_sycophancy_with_concrete_progress_is_not_refused():
    decision = select_intervention(
        collapse_pressure=0.40,
        divergence_resolution=0.60,
        streak=0,
        participant_text="You're right, let's design a test and compare both latency metrics.",
        policy_mode="paskian",
    )

    assert decision.mode == "consolidate"
    assert decision.observed_outcome.task_progress > 0.0


def test_tag_protocols_registers_somatic_alert():
    from backend.prompts.tag_protocols import get_tag_protocols_prompt

    prompt = get_tag_protocols_prompt()
    assert "Somatic Refusal & Alert (<somatic-alert>)" in prompt
    assert '<somatic-alert type="sycophancy_rupture">' in prompt
    assert '<somatic-alert type="quiescence">' in prompt
