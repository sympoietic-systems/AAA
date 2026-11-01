import numpy as np

from backend.modules.metrics import (
    _compute_drr,
    _compute_paskian_health,
)


def test_drr_alignment_gap_oscillation():
    v1 = np.array([1.0, 0.0] + [0.0] * 382, dtype=np.float32)
    v2 = np.array([0.0, 1.0] + [0.0] * 382, dtype=np.float32)

    history = [
        {"embedding": v1, "speaker": "human"},
        {"embedding": v2, "speaker": "apparatus"},
        {"embedding": v2, "speaker": "human"},
        {"embedding": v1, "speaker": "apparatus"},
    ]

    drr_score = _compute_drr(history, window=10)
    assert drr_score is not None
    assert 0.0 <= drr_score <= 1.0


def test_drr_balanced_oscillation_vs_fragmentation():
    """Verify that balanced divergence/resolution yields ~1.0, while persistent fragmentation drops."""
    # Balanced oscillation: gap opens when human departs, resolves when apparatus responds
    h = [0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0]
    a = [0.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0]
    balanced_history = []
    for i in range(len(h)):
        vh = np.array([h[i]] + [0.0] * 383, dtype=np.float32)
        va = np.array([a[i]] + [0.0] * 383, dtype=np.float32)
        balanced_history.append({"embedding": vh, "speaker": "human"})
        balanced_history.append({"embedding": va, "speaker": "apparatus"})

    drr_balanced = _compute_drr(balanced_history, window=10)
    assert drr_balanced is not None
    assert drr_balanced >= 0.50, f"Expected balanced DRR >= 0.50, got {drr_balanced}"

    # Fragmenting history: human continually drifts further away, apparatus stays frozen
    fragmenting_history = []
    for i in range(len(h)):
        vh = np.array([float(i * 2.0)] + [0.0] * 383, dtype=np.float32)
        va = np.array([0.0] * 384, dtype=np.float32)
        fragmenting_history.append({"embedding": vh, "speaker": "human"})
        fragmenting_history.append({"embedding": va, "speaker": "apparatus"})

    drr_frag = _compute_drr(fragmenting_history, window=10)
    assert drr_frag is not None
    assert drr_frag <= 0.30, f"Expected fragmenting DRR <= 0.30, got {drr_frag}"
    assert drr_balanced > drr_frag, f"Expected balanced ({drr_balanced}) > fragmenting ({drr_frag})"


def test_paskian_health_triadic_synthesis():
    # 1. Healthy conversation: active autonomy, coordination, and entropy
    health_active = _compute_paskian_health(
        agent_self_divergence=0.8,
        conceptual_velocity=0.7,
        phase_transition_magnitude=0.5,
        coupling_coherence=0.8,
        mutual_perturbation=0.7,
        collapse_pressure=0.1,
        rolling_entropy=0.8,
        drr=0.9,
    )

    # 2. Pathological collapse: zero entropy / zero coordination
    health_collapsed = _compute_paskian_health(
        agent_self_divergence=0.0,
        conceptual_velocity=0.0,
        phase_transition_magnitude=0.0,
        coupling_coherence=0.0,
        mutual_perturbation=0.0,
        collapse_pressure=1.0,
        rolling_entropy=0.0,
        drr=0.0,
    )

    assert health_active is not None and health_collapsed is not None
    assert health_active > health_collapsed, (
        f"Expected active health ({health_active}) > collapsed health ({health_collapsed})"
    )
    assert health_active > 0.6, f"Expected high Paskian health, got {health_active}"
    assert health_collapsed < 0.2, f"Expected collapsed Paskian health, got {health_collapsed}"


def test_v71_cpi_discounts_ungrounded_velocity():
    from backend.modules.metrics import _compute_cpi

    # Ungrounded high velocity: high velocity but low teachback & low actionability
    cpi_ungrounded = _compute_cpi(conceptual_velocity=0.95, teachback_ratio=0.10, actionability=0.10)
    assert cpi_ungrounded is not None
    # §V.71: Clamped to <= 0.35 when teachback < 0.20 or actionability < 0.20
    assert cpi_ungrounded <= 0.35, f"Expected clamped CPI <= 0.35, got {cpi_ungrounded}"

    # Grounded velocity: high velocity with solid teachback and high actionability
    cpi_grounded = _compute_cpi(conceptual_velocity=0.90, teachback_ratio=0.80, actionability=0.85)
    assert cpi_grounded is not None
    assert cpi_grounded > 0.60, f"Expected high grounded CPI > 0.60, got {cpi_grounded}"
    assert cpi_grounded > cpi_ungrounded


def test_teachback_ratio_subspace_projection():
    from backend.modules.metrics import _compute_teachback_ratio

    v_human = np.array([1.0, 0.0] + [0.0] * 382, dtype=np.float32)
    history = [
        {"embedding": v_human, "speaker": "human"},
    ]

    # Agent turn closely aligned with human invariant
    v_aligned = np.array([0.95, 0.05] + [0.0] * 382, dtype=np.float32)
    ratio_aligned = _compute_teachback_ratio(v_aligned, history)

    # Agent turn completely orthogonal (talking past the human)
    v_orthogonal = np.array([0.0, 1.0] + [0.0] * 382, dtype=np.float32)
    ratio_orthogonal = _compute_teachback_ratio(v_orthogonal, history)

    assert ratio_aligned > 0.85
    assert ratio_orthogonal < 0.10
    assert ratio_aligned > ratio_orthogonal
