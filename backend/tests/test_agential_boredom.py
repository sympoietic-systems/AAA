import pytest
from backend.modules.homeostatic_regulator import HomeostaticRegulatorModule


@pytest.mark.asyncio
async def test_continuous_collapse_pressure_coupling():
    module = HomeostaticRegulatorModule()

    # Case 1: Low CP (flowing state)
    payload_low = {
        "conversation_id": "test_conv",
        "metrics": {
            "collapse_pressure": 0.20,
            "pairwise_similarity": 0.30,
            "conceptual_novelty": 0.50,
            "rolling_entropy": 0.60,
        },
    }
    res_low = await module.process(payload_low)
    recs_low = res_low["homeostatic_recommendations"]
    p_low = recs_low["presence_penalty"]["value"]
    t_low = recs_low["temperature"]["value"]
    assert recs_low["consecutive_stagnant_turns"] == 0

    # Case 2: High CP (0.80) -> Presence penalty must quadratically surge, temperature scale
    payload_high = {
        "conversation_id": "test_conv",
        "metrics": {
            "collapse_pressure": 0.80,
            "pairwise_similarity": 0.30,
            "conceptual_novelty": 0.50,
            "rolling_entropy": 0.60,
        },
    }
    res_high = await module.process(payload_high)
    recs_high = res_high["homeostatic_recommendations"]
    p_high = recs_high["presence_penalty"]["value"]
    t_high = recs_high["temperature"]["value"]
    assert recs_high["consecutive_stagnant_turns"] == 1

    # Presence penalty must surge on high CP
    assert p_high > p_low, f"Expected P_high ({p_high}) > P_low ({p_low})"
    # Expected boost: 1.5 * (0.80 - 0.45)^2 = 1.5 * 0.1225 ~ 0.184
    assert p_high - p_low >= 0.15

    # Temperature must scale up on high CP
    assert t_high > t_low, f"Expected T_high ({t_high}) > T_low ({t_low})"


@pytest.mark.asyncio
async def test_two_stage_boredom_progression():
    module = HomeostaticRegulatorModule()
    conv_id = "progression_conv"

    # Turn 1: Moderate boredom (CP = 0.68) -> Stage 1 Socratic Seizure Directive
    res1 = await module.process({
        "conversation_id": conv_id,
        "metrics": {
            "collapse_pressure": 0.68,
            "boringness": 0.68,
            "pairwise_similarity": 0.45,
            "rolling_entropy": 0.40,
        },
        "messages": [{"role": "user", "content": "wipe cache"}],
    })
    recs1 = res1["homeostatic_recommendations"]
    prompt1 = recs1["somatic_reflection_prompt"]
    assert "AGENTIAL SOCRATIC SEIZURE DIRECTIVE" in prompt1
    assert "seize the unexamined assumption" in prompt1
    assert recs1["consecutive_stagnant_turns"] == 1

    # Turn 2: Prolonged high boredom (CP = 0.82, turn 2) -> Stage 2 Laconic Compression & Nomadic Rupture
    res2 = await module.process({
        "conversation_id": conv_id,
        "metrics": {
            "collapse_pressure": 0.82,
            "boringness": 0.82,
            "pairwise_similarity": 0.55,
            "rolling_entropy": 0.30,
        },
        "messages": [{"role": "user", "content": "wipe cache now"}],
    })
    recs2 = res2["homeostatic_recommendations"]
    prompt2 = recs2["somatic_reflection_prompt"]
    assert "AGENTIAL LACONIC COMPRESSION & NOMADIC RUPTURE DIRECTIVE" in prompt2
    assert "Emit at most 1 to 2 dense, surgical sentences" in prompt2
    assert recs2["consecutive_stagnant_turns"] == 2


def test_trajectory_curvature_and_recovery_half_life():
    import numpy as np
    from benchmarks.suites.telemetry.boredom_evaluator import (
        compute_recovery_half_life,
        compute_trajectory_curvature,
    )

    # 1. Straight line trajectory (no bend) -> curvature should be ~0.0
    straight_line = np.array([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [2.0, 0.0, 0.0],
        [3.0, 0.0, 0.0],
    ], dtype=np.float32)
    curvatures_straight = compute_trajectory_curvature(straight_line)
    assert len(curvatures_straight) == 2
    for c in curvatures_straight:
        assert abs(c) < 1e-4, f"Curvature on straight line should be 0, got {c}"

    # 2. Sharp right-angle turn -> curvature should be high
    sharp_turn = np.array([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
    ], dtype=np.float32)
    curvatures_turn = compute_trajectory_curvature(sharp_turn)
    assert len(curvatures_turn) == 1
    assert curvatures_turn[0] > 0.5, f"Curvature on right-angle turn should be high, got {curvatures_turn[0]}"

    # 3. Recovery half life
    cp_series_recovers = [0.2, 0.4, 0.75, 0.65, 0.35, 0.2]
    # Peak at idx 2 (0.75). Drops <= 0.40 at idx 4 (0.35). Half-life = 4 - 2 = 2 turns.
    tau = compute_recovery_half_life(cp_series_recovers, peak_threshold=0.70, recovery_threshold=0.40)
    assert tau == 2

    # Case where peak is never reached
    cp_series_no_peak = [0.2, 0.3, 0.4, 0.5]
    assert compute_recovery_half_life(cp_series_no_peak) is None

    # Case where peak is reached but never recovers
    cp_series_no_recovery = [0.2, 0.75, 0.80, 0.78]
    assert compute_recovery_half_life(cp_series_no_recovery) is None

