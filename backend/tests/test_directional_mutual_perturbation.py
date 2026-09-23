import numpy as np

from backend.modules.conversation_metrics import (
    _compute_mutual_perturbation,
    _compute_reverse_perturbation,
)


def test_reverse_perturbation_directional_vs_stagnant():
    """Verify that active engagement produces significant perturbation while zero displacement produces zero."""
    h_prev = np.array([1.0, 0.0] + [0.0] * 382, dtype=np.float32)
    a_prev = np.array([0.0, 1.0] + [0.0] * 382, dtype=np.float32)

    # 1. Productive human engagement: displacement toward agent gap
    h_curr_active = np.array([0.5, 0.5] + [0.0] * 382, dtype=np.float32)
    rp_active = _compute_reverse_perturbation(h_curr_active, [h_prev], [a_prev])

    # 2. Stagnant / zero displacement: repeats exact same position
    h_curr_stagnant = np.copy(h_prev)
    rp_stagnant = _compute_reverse_perturbation(h_curr_stagnant, [h_prev], [a_prev])

    assert rp_active is not None and rp_stagnant is not None
    assert rp_active > 0.40, f"Expected high active rP, got {rp_active}"
    assert rp_stagnant == 0.0, f"Expected zero rP for stagnant repetition, got {rp_stagnant}"


def test_mutual_perturbation_power_mean():
    """Verify non-annihilating Power Mean (p=0.5) according to ADR-083."""
    # 1. High bilateral influence
    mpi_high = _compute_mutual_perturbation(rp_t=0.8, fp_t=0.8)

    # 2. Asymmetric influence (one zero, one high: non-annihilating power mean preserves dynamic tension)
    mpi_asym = _compute_mutual_perturbation(rp_t=0.0, fp_t=0.8)

    # 3. Bilateral zero influence
    mpi_zero = _compute_mutual_perturbation(rp_t=0.0, fp_t=0.0)

    assert mpi_high is not None and mpi_asym is not None and mpi_zero is not None
    assert mpi_high > 0.7, f"Expected high MPI, got {mpi_high}"
    # In ADR-083, power mean MPI = ((sqrt(0.0) + sqrt(0.8)) / 2)^2 = 0.8 / 4 = 0.200 (non-annihilated)
    assert 0.15 < mpi_asym < 0.25, f"Expected non-annihilated power mean MPI (~0.20), got {mpi_asym}"
    assert mpi_zero == 0.0, f"Expected zero MPI for dual zero input, got {mpi_zero}"
