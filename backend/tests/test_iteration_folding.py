import pytest
from backend.metabolisation.sedimentation import find_similar_node, merge_nodes


def test_merge_nodes_concept_iteration_folding():
    existing = [
        {
            "id": "mem_0001",
            "diffractive_key": "nomadic_synthesis",
            "intra_active_text": "Nomadic synthesis patterns folding past ghosts into active context.",
            "intensity": 0.6,
            "revision_count": 1,
            "tendrils": ["mem_0002"],
        }
    ]

    new_nodes = [
        {
            "diffractive_key": "nomadic_synthesis",
            "intra_active_text": "Nomadic synthesis patterns integrating ghost traces into context.",
            "intensity": 0.85,
            "tendrils": ["mem_0003"],
        }
    ]

    merged = merge_nodes(existing, new_nodes)
    assert len(merged) == 1
    node = merged[0]
    assert node["id"] == "mem_0001"
    assert node["revision_count"] == 2
    assert node["intensity"] == 0.85
    assert set(node["tendrils"]) == {"mem_0002", "mem_0003"}
    assert "revision_history" in node
    assert len(node["revision_history"]) == 1
    assert node["revision_history"][0]["merge_model"] == "iteration-folding"


def test_find_similar_node_adaptive_threshold():
    existing = [
        {
            "id": "mem_0010",
            "diffractive_key": "",
            "intra_active_text": "Diffractive stagnation telemetry measuring resonance similarity pattern.",
            "revision_count": 4,
        }
    ]

    new_node = {
        "diffractive_key": "",
        "intra_active_text": "Diffractive stagnation telemetry measuring resonance similarity pattern.",
    }

    match, score = find_similar_node(new_node, existing, threshold=0.65)
    assert match is not None
    assert match["id"] == "mem_0010"
    assert score == 1.0
