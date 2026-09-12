import numpy as np
import pytest
from backend.modules.conversation_metrics import (
    _compute_conceptual_novelty,
    _compute_pairwise_similarity,
)


def test_pairwise_similarity_speaker_weighting_and_decay():
    current_vec = np.ones(384, dtype=np.float32) / np.sqrt(384)
    past_vec = np.ones(384, dtype=np.float32) / np.sqrt(384)
    ortho_vec = np.zeros(384, dtype=np.float32)
    ortho_vec[0] = 1.0
    ortho_vec[1:] = -1.0 / 383.0
    ortho_vec = ortho_vec / np.linalg.norm(ortho_vec)

    # Turn history with matching and non-matching messages:
    # Case A: Matching message is cross-speaker (human), non-matching is same-speaker (apparatus)
    cross_match_hist = [
        {"embedding": ortho_vec, "speaker": "apparatus"},
        {"embedding": past_vec, "speaker": "human"},
    ]
    # Case B: Matching message is same-speaker (apparatus), non-matching is cross-speaker (human)
    same_match_hist = [
        {"embedding": ortho_vec, "speaker": "human"},
        {"embedding": past_vec, "speaker": "apparatus"},
    ]

    sim_cross = _compute_pairwise_similarity(
        current_vec=current_vec,
        current_speaker="apparatus",
        recent_history=cross_match_hist,
    )
    sim_same = _compute_pairwise_similarity(
        current_vec=current_vec,
        current_speaker="apparatus",
        recent_history=same_match_hist,
    )

    assert sim_same is not None and sim_cross is not None
    # Cross-speaker similarity should carry higher relative weight (1.2) than same-speaker (0.8)
    assert sim_cross > sim_same, f"Expected cross ({sim_cross}) > same ({sim_same})"


def test_pairwise_similarity_identical_vectors_unity():
    """Verify that a sequence of identical vectors evaluates to 1.000 rather than suppressed 0.420."""
    v = np.ones(384, dtype=np.float32) / np.sqrt(384)
    history = [{"speaker": "human" if i % 2 == 0 else "apparatus", "embedding": v} for i in range(15)]
    sim = _compute_pairwise_similarity(v, "apparatus", history)
    assert sim == 1.0, f"Expected 1.0 for identical vectors, got {sim}"


def test_pairwise_similarity_recency_decay_ordering():
    """Verify that the immediate preceding message contributes more similarity weight than older messages."""
    c_vec = np.array([1.0] + [0.0] * 383, dtype=np.float32)
    diff_vec = np.array([0.0, 1.0] + [0.0] * 382, dtype=np.float32)

    # Case A: Identical vector is immediate preceding (end of chronological list)
    hist_immediate = [
        {"embedding": diff_vec, "speaker": "human"},
        {"embedding": diff_vec, "speaker": "human"},
        {"embedding": c_vec, "speaker": "human"},
    ]
    sim_immediate = _compute_pairwise_similarity(c_vec, "apparatus", hist_immediate)

    # Case B: Identical vector is oldest (start of chronological list)
    hist_ancient = [
        {"embedding": c_vec, "speaker": "human"},
        {"embedding": diff_vec, "speaker": "human"},
        {"embedding": diff_vec, "speaker": "human"},
    ]
    sim_ancient = _compute_pairwise_similarity(c_vec, "apparatus", hist_ancient)

    assert sim_immediate is not None and sim_ancient is not None
    assert sim_immediate > sim_ancient, (
        f"Expected immediate similarity ({sim_immediate}) > ancient similarity ({sim_ancient})"
    )



def test_conceptual_novelty_centroid_drift():
    v1 = np.array([1.0] + [0.0] * 383, dtype=np.float32)
    v2 = np.array([0.0, 1.0] + [0.0] * 382, dtype=np.float32)

    hist = [{"embedding": v1, "speaker": "human"}]

    novelty_1, centroid_1 = _compute_conceptual_novelty(
        current_vec=v1, recent_history=hist, prior_centroid=None
    )

    novelty_2, centroid_2 = _compute_conceptual_novelty(
        current_vec=v2, recent_history=hist, prior_centroid=centroid_1
    )

    assert novelty_1 is not None and novelty_2 is not None
    # Orthogonal turn v2 relative to v1 centroid should yield higher conceptual novelty
    assert novelty_2 > novelty_1, f"Expected novelty_2 ({novelty_2}) > novelty_1 ({novelty_1})"


def test_conceptual_novelty_repetitive_basin_suppression():
    """Verify that tight semantic clustering suppresses novelty, while orthogonal drift expands it."""
    base = np.array([1.0] + [0.0] * 383, dtype=np.float32)
    
    # Simulate a tight repetitive dialogue basin (small perturbations around base)
    history = []
    for i in range(5):
        noise = np.zeros(384, dtype=np.float32)
        noise[0] = 1.0
        noise[1] = 0.05 * (i + 1)
        noise = noise / np.linalg.norm(noise)
        history.append({"embedding": noise, "speaker": "human" if i % 2 == 0 else "apparatus"})
    
    # 1. Repetitive turn: slight paraphrase within the cluster
    near_turn = np.zeros(384, dtype=np.float32)
    near_turn[0] = 1.0
    near_turn[1] = 0.08
    near_turn = near_turn / np.linalg.norm(near_turn)
    
    novelty_near, _ = _compute_conceptual_novelty(
        current_vec=near_turn, recent_history=history, prior_centroid=base
    )
    
    # 2. Orthogonal turn: completely new conceptual direction
    ortho_turn = np.zeros(384, dtype=np.float32)
    ortho_turn[2] = 1.0
    
    novelty_ortho, _ = _compute_conceptual_novelty(
        current_vec=ortho_turn, recent_history=history, prior_centroid=base
    )
    
    assert novelty_near is not None and novelty_ortho is not None
    # Repetitive turn should remain suppressed (<= 0.35)
    assert novelty_near <= 0.35, f"Expected suppressed novelty in repetitive basin, got {novelty_near}"
    # Orthogonal turn should register strong novelty (>= 0.70) under ADR-084 dual-horizon attractor
    assert novelty_ortho >= 0.70, f"Expected high novelty for orthogonal shift, got {novelty_ortho}"
    assert novelty_ortho > novelty_near * 2, "Orthogonal novelty should be significantly higher than near novelty"

