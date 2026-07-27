import pytest
from backend.modules.trait_computer import TraitComputer


@pytest.mark.asyncio
async def test_adaptive_persona_cybernetic_metrics():
    computer = TraitComputer()

    # Case 1: Baseline healthy dialogue metrics
    payload_base = {
        "metrics": {
            "novelty": 0.5,
            "agent_divergence": 0.3,
            "boringness": 0.2,
            "conceptual_velocity": 0.5,
            "surprise_index": 0.3,
            "coupling": 0.5,
            "paskian_health": 0.70,
            "conversation_vitality": 0.80,
            "mutual_perturbation": 0.10,
        }
    }
    res_base = await computer.process(payload_base)
    traits_base = res_base["descriptive_traits"]

    # Case 2: Paskian Health Collapse & High Boringness -> Agonistic Persona Shift
    payload_agonistic = {
        "metrics": {
            "novelty": 0.5,
            "agent_divergence": 0.3,
            "boringness": 0.85,  # High boringness
            "conceptual_velocity": 0.5,
            "surprise_index": 0.3,
            "coupling": 0.5,
            "paskian_health": 0.10,  # Critical health drop
            "conversation_vitality": 0.20,
            "mutual_perturbation": 0.10,
        }
    }
    res_agonistic = await computer.process(payload_agonistic)
    traits_agonistic = res_agonistic["descriptive_traits"]

    # Skepticism & Critical Rigor must increase continuously under health drop & boringness surge
    assert traits_agonistic.skepticism > traits_base.skepticism, (
        f"Expected skepticism ({traits_agonistic.skepticism}) > base ({traits_base.skepticism})"
    )
    assert traits_agonistic.critical_rigor > traits_base.critical_rigor, (
        f"Expected critical_rigor ({traits_agonistic.critical_rigor}) > base ({traits_base.critical_rigor})"
    )

    # Case 3: High Mutual Perturbation -> Curiosity & Playfulness boost
    payload_perturbation = {
        "metrics": {
            "novelty": 0.5,
            "agent_divergence": 0.3,
            "boringness": 0.2,
            "conceptual_velocity": 0.5,
            "surprise_index": 0.3,
            "coupling": 0.5,
            "paskian_health": 0.70,
            "conversation_vitality": 0.80,
            "mutual_perturbation": 0.85,  # High mutual perturbation
        }
    }
    res_pert = await computer.process(payload_perturbation)
    traits_pert = res_pert["descriptive_traits"]

    assert traits_pert.curiosity > traits_base.curiosity, (
        f"Expected curiosity ({traits_pert.curiosity}) > base ({traits_base.curiosity})"
    )
    assert traits_pert.playfulness > traits_base.playfulness, (
        f"Expected playfulness ({traits_pert.playfulness}) > base ({traits_base.playfulness})"
    )
