import numpy as np
import pytest
from backend.modules.conversation_metrics import (
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
    assert (
        health_active > health_collapsed
    ), f"Expected active health ({health_active}) > collapsed health ({health_collapsed})"
    assert health_active > 0.6, f"Expected high Paskian health, got {health_active}"
    assert health_collapsed < 0.2, f"Expected collapsed Paskian health, got {health_collapsed}"
