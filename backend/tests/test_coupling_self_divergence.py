import numpy as np
import pytest
from backend.modules.conversation_metrics import (
    _compute_agent_self_divergence,
    _compute_coupling_coherence,
)


def test_coupling_coherence_trajectory_correlation():
    v1 = np.array([1.0, 0.0] + [0.0] * 382, dtype=np.float32)
    v2 = np.array([0.0, 1.0] + [0.0] * 382, dtype=np.float32)
    v3 = np.array([0.5, 0.5] + [0.0] * 382, dtype=np.float32)

    # 1. Synchronized human & apparatus displacements
    history_aligned = [
        {"embedding": v2, "speaker": "apparatus"},
        {"embedding": v2, "speaker": "human"},
        {"embedding": v1, "speaker": "apparatus"},
        {"embedding": v1, "speaker": "human"},
    ]

    cc_aligned = _compute_coupling_coherence(history_aligned, window=8)
    assert cc_aligned is not None
    assert 0.0 <= cc_aligned <= 1.0


def test_agent_self_divergence_loops_and_evolution():
    c_vec = np.array([1.0] + [0.0] * 383, dtype=np.float32)

    # 1. Immediate self-repetition -> high self-similarity -> low divergence
    same_prior = [c_vec] * 5
    div_loop = _compute_agent_self_divergence(
        current_vec=c_vec, current_speaker="apparatus", prior_agent=same_prior
    )

    # 2. Evolving agent turns -> orthogonal to past turns -> high divergence
    diff_vec = np.array([0.0] + [1.0] + [0.0] * 382, dtype=np.float32)
    diff_prior = [diff_vec] * 5
    div_evolving = _compute_agent_self_divergence(
        current_vec=c_vec, current_speaker="apparatus", prior_agent=diff_prior
    )

    assert div_loop is not None and div_evolving is not None
    assert (
        div_evolving > div_loop
    ), f"Expected evolving divergence ({div_evolving}) > loop divergence ({div_loop})"
