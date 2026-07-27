import pytest
from backend.modules.homeostatic_regulator import HomeostaticRegulatorModule


@pytest.mark.asyncio
async def test_continuous_sensorimotor_parameter_modulation():
    module = HomeostaticRegulatorModule()

    # Case 1: Baseline metrics
    payload_base = {
        "metrics": {
            "pairwise_similarity": 0.5,
            "conceptual_novelty": 0.3,
            "agent_self_divergence": 0.4,
            "glitch_fidelity": 0.85,
            "conversation_vitality": 0.6,
            "rolling_entropy": 0.2,
        }
    }
    res_base = await module.process(payload_base)
    recs_base = res_base["homeostatic_recommendations"]
    t_base = recs_base["temperature"]["value"]
    p_base = recs_base["presence_penalty"]["value"]
    f_base = recs_base["frequency_penalty"]["value"]

    # Case 2: Low Glitch Fidelity (over-smoothing bias detected)
    payload_low_gf = {
        "metrics": {
            "pairwise_similarity": 0.5,
            "conceptual_novelty": 0.3,
            "agent_self_divergence": 0.4,
            "glitch_fidelity": 0.20,  # Low fidelity
            "conversation_vitality": 0.6,
            "rolling_entropy": 0.2,
        }
    }
    res_gf = await module.process(payload_low_gf)
    recs_gf = res_gf["homeostatic_recommendations"]
    t_gf = recs_gf["temperature"]["value"]
    p_gf = recs_gf["presence_penalty"]["value"]

    # Temperature and presence_penalty must continuously increase under low Glitch Fidelity
    assert t_gf > t_base, f"Expected T_gf ({t_gf}) > T_base ({t_base})"
    assert p_gf > p_base, f"Expected P_gf ({p_gf}) > P_base ({p_base})"

    # Case 3: Entropy collapse
    payload_entropy = {
        "metrics": {
            "pairwise_similarity": 0.5,
            "rolling_entropy": 0.01,  # Entropy collapse
        }
    }
    res_entropy = await module.process(payload_entropy)
    recs_entropy = res_entropy["homeostatic_recommendations"]
    f_entropy = recs_entropy["frequency_penalty"]["value"]
    p_entropy = recs_entropy["presence_penalty"]["value"]

    # Penalties must increase continuously on entropy collapse
    assert f_entropy > f_base, f"Expected F_entropy ({f_entropy}) > F_base ({f_base})"
    assert p_entropy > p_base, f"Expected P_entropy ({p_entropy}) > P_base ({p_base})"
