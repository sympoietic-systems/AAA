import numpy as np
import pytest
from backend.modules.conversation_metrics import (
    _compute_forward_perturbation,
    _compute_mutual_perturbation,
    _compute_reverse_perturbation,
)


def test_reverse_perturbation_directional_vs_non_sequitur():
    h_prev = np.array([1.0, 0.0] + [0.0] * 382, dtype=np.float32)
    a_prev = np.array([0.0, 1.0] + [0.0] * 382, dtype=np.float32)

    # 1. Productive human engagement: moves toward a_prev gap
    h_curr_aligned = np.array([0.5, 0.5] + [0.0] * 382, dtype=np.float32)
    rp_aligned = _compute_reverse_perturbation(
        h_curr_aligned, [h_prev], [a_prev]
    )

    # 2. Non-sequitur / orthogonal displacement: moves into dimension 2 (unrelated)
    h_curr_orthogonal = np.array([1.0, 0.0, 1.0] + [0.0] * 381, dtype=np.float32)
    rp_orthogonal = _compute_reverse_perturbation(
        h_curr_orthogonal, [h_prev], [a_prev]
    )

    assert rp_aligned is not None and rp_orthogonal is not None
    assert (
        rp_aligned > rp_orthogonal
    ), f"Expected aligned rP ({rp_aligned}) > orthogonal rP ({rp_orthogonal})"


def test_mutual_perturbation_geometric_mean():
    # 1. High bilateral influence
    mpi_high = _compute_mutual_perturbation(rp_t=0.8, fp_t=0.8)

    # 2. Asymmetric / zero influence
    mpi_zero = _compute_mutual_perturbation(rp_t=0.0, fp_t=0.8)

    assert mpi_high is not None and mpi_zero is not None
    assert mpi_high > 0.7, f"Expected high MPI, got {mpi_high}"
    assert mpi_zero == 0.0, f"Expected zero MPI, got {mpi_zero}"
