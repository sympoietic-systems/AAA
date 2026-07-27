import numpy as np
import pytest
from backend.modules.conversation_metrics import (
    _compute_conceptual_novelty,
    _compute_pairwise_similarity,
)


def test_pairwise_similarity_speaker_weighting_and_decay():
    current_vec = np.ones(384, dtype=np.float32) / np.sqrt(384)
    past_vec = np.ones(384, dtype=np.float32) / np.sqrt(384)

    # Turn history: same speaker vs cross speaker
    same_speaker_hist = [{"embedding": past_vec, "speaker": "apparatus"}]
    cross_speaker_hist = [{"embedding": past_vec, "speaker": "human"}]

    sim_same = _compute_pairwise_similarity(
        current_vec=current_vec,
        current_speaker="apparatus",
        recent_history=same_speaker_hist,
    )
    sim_cross = _compute_pairwise_similarity(
        current_vec=current_vec,
        current_speaker="apparatus",
        recent_history=cross_speaker_hist,
    )

    assert sim_same is not None and sim_cross is not None
    # Cross-speaker similarity should be weighted higher (1.2) than same-speaker (0.8)
    assert sim_cross > sim_same, f"Expected cross ({sim_cross}) > same ({sim_same})"


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
