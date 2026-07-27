import numpy as np
import pytest
from backend.modules.conversation_metrics import (
    _compute_conceptual_velocity,
    _compute_surprise_index,
)


def test_predictive_surprise_linear_vs_jump():
    # 1. Predictable linear progression
    v0 = np.array([0.1, 0.0] + [0.0] * 382, dtype=np.float32)
    v1 = np.array([0.2, 0.0] + [0.0] * 382, dtype=np.float32)
    v2 = np.array([0.3, 0.0] + [0.0] * 382, dtype=np.float32)

    s_linear = _compute_surprise_index(current_vec=v2, all_recent=[v1, v0])

    # 2. Sudden orthogonal jump
    v_jump = np.array([0.0, 1.0] + [0.0] * 382, dtype=np.float32)
    s_jump = _compute_surprise_index(current_vec=v_jump, all_recent=[v1, v0])

    assert s_linear is not None and s_jump is not None
    assert (
        s_jump > s_linear
    ), f"Expected jump surprise ({s_jump}) > linear surprise ({s_linear})"


def test_conceptual_velocity_and_phase_transition():
    v0 = np.array([1.0, 0.0] + [0.0] * 382, dtype=np.float32)
    v1 = np.array([0.0, 1.0] + [0.0] * 382, dtype=np.float32)
    v2 = np.array([-1.0, 0.0] + [0.0] * 382, dtype=np.float32)

    vel, phase_trans = _compute_conceptual_velocity(current_vec=v2, all_recent=[v1, v0])

    assert vel is not None and phase_trans is not None
    assert 0.0 <= vel <= 1.0
    assert phase_trans >= 0.0
