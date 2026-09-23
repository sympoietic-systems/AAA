import numpy as np

from backend.modules.metrics import (
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
    div_loop = _compute_agent_self_divergence(current_vec=c_vec, current_speaker="apparatus", prior_agent=same_prior)

    # 2. Evolving agent turns -> orthogonal to past turns -> high divergence
    diff_vec = np.array([0.0] + [1.0] + [0.0] * 382, dtype=np.float32)
    diff_prior = [diff_vec] * 5
    div_evolving = _compute_agent_self_divergence(
        current_vec=c_vec, current_speaker="apparatus", prior_agent=diff_prior
    )

    assert div_loop is not None and div_evolving is not None
    assert div_evolving > div_loop, f"Expected evolving divergence ({div_evolving}) > loop divergence ({div_loop})"


def test_agent_self_divergence_recency_decay():
    """Verify that immediate prior repetition penalizes more heavily than ancient repetition."""
    c_vec = np.array([1.0] + [0.0] * 383, dtype=np.float32)
    diff_vec = np.array([0.0, 1.0] + [0.0] * 382, dtype=np.float32)

    # Case A: Repeated utterance is immediate prior (index -1 in chronological history)
    # prior = [diff_vec, ..., diff_vec, c_vec]
    prior_immediate = [diff_vec] * 5 + [c_vec]
    div_immediate = _compute_agent_self_divergence(
        current_vec=c_vec, current_speaker="apparatus", prior_agent=prior_immediate
    )

    # Case B: Repeated utterance is ancient (index 0 in chronological history)
    # prior = [c_vec, diff_vec, ..., diff_vec]
    prior_ancient = [c_vec] + [diff_vec] * 5
    div_ancient = _compute_agent_self_divergence(
        current_vec=c_vec, current_speaker="apparatus", prior_agent=prior_ancient
    )

    assert div_immediate is not None and div_ancient is not None
    # Immediate echo should have lower divergence (heavier penalty) than ancient echo
    assert div_ancient > div_immediate, (
        f"Expected ancient repetition divergence ({div_ancient}) > immediate ({div_immediate})"
    )


def test_coupling_coherence_directional_alignment_vs_opposition():
    """Verify that aligned and agonistic counter-displacements yield high coherence, while orthogonal dissociation yields 0.0."""
    v_orig = np.array([0.0, 0.0] + [0.0] * 382, dtype=np.float32)
    v_pos = np.array([1.0, 0.0] + [0.0] * 382, dtype=np.float32)
    v_neg = np.array([-1.0, 0.0] + [0.0] * 382, dtype=np.float32)
    v_orth = np.array([0.0, 1.0] + [0.0] * 382, dtype=np.float32)

    # 1. Aligned displacements: both move in +x direction
    history_aligned = [
        {"embedding": v_orig, "speaker": "human"},
        {"embedding": v_orig, "speaker": "agent"},
        {"embedding": v_pos, "speaker": "human"},
        {"embedding": v_pos, "speaker": "agent"},
    ]
    cc_aligned = _compute_coupling_coherence(history_aligned)

    # 2. Agonistic counter-steering: human moves +x, agent anchors -x (active dialectical tension)
    history_opposed = [
        {"embedding": v_orig, "speaker": "human"},
        {"embedding": v_orig, "speaker": "agent"},
        {"embedding": v_pos, "speaker": "human"},
        {"embedding": v_neg, "speaker": "agent"},
    ]
    cc_opposed = _compute_coupling_coherence(history_opposed)

    # 3. Orthogonal dissociation: human moves +x, agent makes non-sequitur move in +y
    history_orth = [
        {"embedding": v_orig, "speaker": "human"},
        {"embedding": v_orig, "speaker": "agent"},
        {"embedding": v_pos, "speaker": "human"},
        {"embedding": v_orth, "speaker": "agent"},
    ]
    cc_orth = _compute_coupling_coherence(history_orth)

    assert cc_aligned is not None and cc_opposed is not None and cc_orth is not None
    assert cc_aligned > 0.8, f"Expected high aligned coherence, got {cc_aligned}"
    assert cc_opposed > 0.8, f"Expected high agonistic coherence, got {cc_opposed}"
    assert cc_orth == 0.0, f"Expected 0.0 orthogonal dissociation coherence, got {cc_orth}"


def test_agent_self_divergence_speaker_awareness():
    """Verify that self-divergence is only computed for agent/apparatus, returning None on human turns."""
    vec = np.array([1.0] + [0.0] * 383, dtype=np.float32)
    prior = [vec] * 3

    div_human = _compute_agent_self_divergence(current_vec=vec, current_speaker="human", prior_agent=prior)
    div_agent = _compute_agent_self_divergence(current_vec=vec, current_speaker="agent", prior_agent=prior)

    assert div_human is None
    assert div_agent is not None
