import numpy as np

from backend.modules.conversation_metrics import (
    _compute_collapse_pressure,
    _compute_rolling_entropy,
)


def test_spectral_entropy_orthogonal_vs_collinear():
    current = np.array([1.0] + [0.0] * 383, dtype=np.float32)

    # 1. Collinear history (all vectors identical -> 1D subspace -> low spectral entropy)
    collinear_hist = [{"embedding": current} for _ in range(5)]
    ent_collinear = _compute_rolling_entropy(current, collinear_hist, window=8)

    # 2. Orthogonal history (each vector along a distinct dimension -> high spectral entropy)
    orthogonal_hist = []
    for i in range(1, 6):
        vec = np.zeros(384, dtype=np.float32)
        vec[i] = 1.0
        orthogonal_hist.append({"embedding": vec})

    ent_orthogonal = _compute_rolling_entropy(current, orthogonal_hist, window=8)

    assert ent_collinear is not None and ent_orthogonal is not None
    assert ent_orthogonal > ent_collinear, (
        f"Expected orthogonal entropy ({ent_orthogonal}) > collinear ({ent_collinear})"
    )


def test_collapse_pressure_triadic_factorization():
    # 1. Healthy conversation: high perturbation, high entropy, high novelty -> collapse near 0
    collapse_healthy = _compute_collapse_pressure(rp_t=0.8, prev_mpi=0.7, rolling_entropy=0.8, conceptual_novelty=0.7)

    # 2. Stagnant conversation: low perturbation, low entropy, low novelty -> collapse near 1
    collapse_stagnant = _compute_collapse_pressure(
        rp_t=0.05, prev_mpi=0.05, rolling_entropy=0.02, conceptual_novelty=0.03
    )

    assert collapse_healthy is not None and collapse_stagnant is not None
    assert collapse_stagnant > collapse_healthy, (
        f"Expected stagnant collapse ({collapse_stagnant}) > healthy ({collapse_healthy})"
    )
    assert collapse_stagnant > 0.7, f"Expected high collapse pressure, got {collapse_stagnant}"


def test_collapse_pressure_stagnant_thresholds():
    """Verify that realistic conversational deadlocks properly cross the 0.65 stagnant and 0.70 sedation thresholds."""
    # Under realistic 10-turn adversarial repetition:
    # perturbation is low (rp_t=0.20, mpi=0.20), entropy is low (0.30), novelty is suppressed (0.20)
    collapse_deadlock = _compute_collapse_pressure(
        rp_t=0.20, prev_mpi=0.20, rolling_entropy=0.30, conceptual_novelty=0.20
    )

    assert collapse_deadlock is not None
    # Must cross the 0.65 threshold to trigger homeostatic 'stagnant' state
    assert collapse_deadlock >= 0.65, f"Expected stagnant trigger (>= 0.65), got {collapse_deadlock}"
    # Must cross the 0.70 threshold to trigger SelfInitiationArbiter sedation interrupt
    assert collapse_deadlock >= 0.70, f"Expected sedation interrupt trigger (>= 0.70), got {collapse_deadlock}"

    # Verify healthy conversation stays safely below the flowing ceiling (< 0.40)
    collapse_flowing = _compute_collapse_pressure(
        rp_t=0.65, prev_mpi=0.60, rolling_entropy=0.75, conceptual_novelty=0.70
    )
    assert collapse_flowing is not None
    assert collapse_flowing < 0.40, f"Expected flowing regime (< 0.40), got {collapse_flowing}"
