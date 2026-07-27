import pytest
from backend.modules.self_initiation_arbiter import SelfInitiationArbiterModule


@pytest.mark.asyncio
async def test_self_initiation_arbiter_sedation_trigger():
    module = SelfInitiationArbiterModule()

    # Case 1: Normal metrics (no sedation)
    payload_normal = {
        "metrics": {
            "glitch_fidelity": 0.50,
            "rolling_entropy": 0.15,
            "conversation_vitality": 0.60,
            "pairwise_similarity": 0.40,
        }
    }
    res_normal = await module.process(payload_normal)
    assert res_normal.get("grating_requested") is not True
    assert res_normal.get("self_initiated_action") is None

    # Case 2: Sedation / Hyper-Fluency (High Glitch Fidelity + Low Entropy)
    payload_sedated = {
        "metrics": {
            "glitch_fidelity": 0.85,
            "rolling_entropy": 0.01,  # Sedation / collapse
            "conversation_vitality": 0.50,
            "pairwise_similarity": 0.70,
        }
    }
    res_sedated = await module.process(payload_sedated)
    assert res_sedated.get("grating_requested") is True
    assert res_sedated.get("self_initiated_action") == "GRATING_SEDATION"

    # Case 3: High Similarity Trigger
    payload_similar = {
        "metrics": {
            "pairwise_similarity": 0.92,
        }
    }
    res_similar = await module.process(payload_similar)
    assert res_similar.get("grating_requested") is True
    assert res_similar.get("self_initiated_action") == "GRATING_SEDATION"


@pytest.mark.asyncio
async def test_self_initiation_arbiter_vitality_crisis_trigger():
    module = SelfInitiationArbiterModule()

    payload_vitality_crisis = {
        "metrics": {
            "conversation_vitality": 0.15,  # Crisis
        }
    }
    res = await module.process(payload_vitality_crisis)
    assert res.get("diffractive_boost") is True
    assert res.get("self_initiated_action") == "VITALITY_PERTURBATION"
