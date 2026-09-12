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

    vel, phase_trans = _compute_conceptual_velocity(current_vec=v2, all_recent=[v0, v1])

    assert vel is not None and phase_trans is not None
    assert 0.0 <= vel <= 1.0
    assert 0.0 <= phase_trans <= 1.0


def test_conceptual_velocity_stagnant_vs_active():
    """Verify that small displacements in repetitive stagnation yield low velocity, while active leaps yield high velocity."""
    base = np.array([1.0] + [0.0] * 383, dtype=np.float32)

    # Stagnant conversation: embeddings barely budge (step ~ 0.05)
    stagnant_history = []
    for i in range(5):
        noise = np.zeros(384, dtype=np.float32)
        noise[0] = 1.0
        noise[1] = 0.02 * i
        stagnant_history.append(noise / np.linalg.norm(noise))

    curr_stagnant = stagnant_history[-1].copy()
    curr_stagnant[1] += 0.02
    curr_stagnant /= np.linalg.norm(curr_stagnant)

    vel_stag, phase_stag = _compute_conceptual_velocity(curr_stagnant, stagnant_history)
    assert vel_stag is not None
    assert vel_stag <= 0.30, f"Expected stagnant velocity <= 0.30, got {vel_stag}"

    # Active conversation: large displacements between consecutive turns (step ~ 1.0)
    active_history = []
    for i in range(5):
        vec = np.zeros(384, dtype=np.float32)
        vec[i] = 1.0
        active_history.append(vec)

    curr_active = np.zeros(384, dtype=np.float32)
    curr_active[5] = 1.0

    vel_active, phase_active = _compute_conceptual_velocity(curr_active, active_history)
    assert vel_active is not None
    assert vel_active >= 0.65, f"Expected active velocity >= 0.65, got {vel_active}"
    assert vel_active > vel_stag, f"Expected active ({vel_active}) > stagnant ({vel_stag})"


def test_predictive_surprise_early_turn_no_saturation():
    """Verify that early turns with standard displacements do not artificially saturate at 1.000."""
    v0 = np.array([1.0, 0.0] + [0.0] * 382, dtype=np.float32)
    # 45-degree displacement (~0.765 distance)
    v1 = np.array([0.7071, 0.7071] + [0.0] * 382, dtype=np.float32)

    s1 = _compute_surprise_index(current_vec=v1, all_recent=[v0])
    assert s1 is not None
    assert 0.20 <= s1 <= 0.70, f"Expected early turn surprise to be in [0.20, 0.70], got {s1}"


