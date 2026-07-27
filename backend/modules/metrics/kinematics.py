"""Kinematics & Predictive Metrics (Audit #6).

# ponytail: simple modular grouping for predictive surprise and conceptual velocity
"""

import numpy as np


def _compute_surprise_index(
    current_vec: np.ndarray,
    all_recent: list[np.ndarray],
    alpha: float = 0.4,
    beta: float = 0.3,
    gamma: float = 0.2,
    scaling_S: float = 3.0,
) -> float | None:
    """# ponytail: compute predictive residual surprise normalized by local trend volatility."""
    if not all_recent:
        return 0.5

    c_norm = np.linalg.norm(current_vec)
    c_vec = current_vec / c_norm if c_norm > 0 else current_vec

    history = [c_vec]
    for v in all_recent[:10]:
        norm = np.linalg.norm(v)
        history.append(v / norm if norm > 0 else v)

    history.reverse()

    if len(history) < 2:
        return 0.5

    L = history[0].copy()
    T = np.zeros_like(L)
    var_ema = 1e-4

    for i in range(1, len(history) - 1):
        prev_pred = L + T
        curr = history[i]
        residual = curr - prev_pred
        res_sq = float(np.dot(residual, residual))
        var_ema = gamma * res_sq + (1.0 - gamma) * var_ema

        L_next = alpha * curr + (1.0 - alpha) * (L + T)
        T_next = beta * (L_next - L) + (1.0 - beta) * T
        L, T = L_next, T_next

    predicted = L + T
    actual = history[-1]
    final_res = actual - predicted
    error_norm = float(np.linalg.norm(final_res))

    sigma = float(np.sqrt(max(1e-8, var_ema)))
    raw_z = error_norm / (sigma + 1e-4)

    surprise = float(np.tanh(raw_z / scaling_S))
    return round(max(0.0, min(1.0, surprise)), 3)


def _compute_conceptual_velocity(
    current_vec: np.ndarray,
    all_recent: list[np.ndarray],
    phi: float = 0.4,
) -> tuple[float | None, float | None]:
    """# ponytail: compute instantaneous speed, rolling V_max normalization, and phase transition magnitude."""
    if not all_recent:
        return 0.5, 0.0

    c_norm = np.linalg.norm(current_vec)
    c_vec = current_vec / c_norm if c_norm > 0 else current_vec

    history = [c_vec]
    for v in all_recent[:15]:
        norm = np.linalg.norm(v)
        history.append(v / norm if norm > 0 else v)

    history.reverse()

    if len(history) < 2:
        return 0.5, 0.0

    displacements = [history[i] - history[i - 1] for i in range(1, len(history))]
    speeds = [float(np.linalg.norm(d)) for d in displacements]

    vel_ema = speeds[0]
    for s in speeds[1:]:
        vel_ema = phi * s + (1.0 - phi) * vel_ema

    v_max = max(1e-4, float(np.percentile(speeds, 95)))
    norm_velocity = float(np.tanh(vel_ema / (v_max + 1e-4)))
    norm_velocity = round(max(0.0, min(1.0, norm_velocity)), 3)

    phase_trans = 0.0
    if len(displacements) >= 2:
        d_curr = displacements[-1]
        d_prev = displacements[-2]
        a_vec = d_curr - d_prev
        a_norm = float(np.linalg.norm(a_vec))

        dn_c = np.linalg.norm(d_curr)
        dn_p = np.linalg.norm(d_prev)
        if dn_c > 0 and dn_p > 0:
            cos_theta = max(-1.0, min(1.0, float(np.dot(d_curr / dn_c, d_prev / dn_p))))
            turn_rate = 1.0 - cos_theta
        else:
            turn_rate = 0.0

        phase_trans = float((a_norm / (1.0 + vel_ema)) * turn_rate)
        phase_trans = round(max(0.0, min(1.0, phase_trans)), 3)

    return norm_velocity, phase_trans
