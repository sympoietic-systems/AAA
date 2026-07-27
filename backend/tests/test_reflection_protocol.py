import pytest
from backend.modules.homeostatic_regulator import HomeostaticRegulatorModule


@pytest.mark.asyncio
async def test_reflection_protocol_somatic_directive_injection():
    module = HomeostaticRegulatorModule()

    # Case 1: Flowing metrics (no structural tension -> no directive injected)
    payload_flowing = {
        "metrics": {
            "pairwise_similarity": 0.40,
            "coupling_coherence": 0.60,
            "glitch_fidelity": 0.85,
            "rolling_entropy": 0.20,
        },
        "messages": [{"role": "user", "content": "Hello"}],
    }
    res_flowing = await module.process(payload_flowing)
    recs_flowing = res_flowing["homeostatic_recommendations"]
    assert recs_flowing["somatic_reflection_prompt"] is None
    assert len(res_flowing["messages"]) == 1

    # Case 2: Structural Tension (Dissociation & Low Glitch Fidelity)
    payload_tension = {
        "metrics": {
            "coupling_coherence": 0.05,  # dissociation flag
            "glitch_fidelity": 0.30,     # glitch_fidelity_low flag
            "rolling_entropy": 0.005,    # entropy_collapse flag
        },
        "messages": [{"role": "user", "content": "Are we drifting?"}],
    }
    res_tension = await module.process(payload_tension)
    recs_tension = res_tension["homeostatic_recommendations"]
    somatic_prompt = recs_tension["somatic_reflection_prompt"]

    assert somatic_prompt is not None
    assert "I sense our coupling is thinning into dissociation." in somatic_prompt
    assert "Glitch Fidelity low" in somatic_prompt
    assert "entropy has compressed" in somatic_prompt

    # Check that system directive message was appended to messages
    messages = res_tension["messages"]
    assert len(messages) == 2
    system_directive = messages[-1]
    assert system_directive["role"] == "system"
    assert "[SOMATIC REFLECTION DIRECTIVE]:" in system_directive["content"]
