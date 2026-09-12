"""Kinematics & Predictive Metrics (Audit #6).

# ponytail: simple modular grouping for predictive surprise and conceptual velocity
"""

import numpy as np


def _compute_surprise_index(
    current_vec: np.ndarray,
    all_recent: list[np.ndarray],
    alpha: float = 0.15,
    beta: float = 0.3,
    kappa: float = 1.2,
) -> float | None:
    """# Proposal 1: Spherical Geodesic SLERP Surprise on S^{D-1}."""
    if not all_recent:
        return 0.0

    c_norm = float(np.linalg.norm(current_vec))
    c_vec = current_vec / c_norm if c_norm > 1e-8 else current_vec

    history = []
    for v in all_recent[-12:]:
        norm = float(np.linalg.norm(v))
        history.append(v / norm if norm > 1e-8 else v)
    history.append(c_vec)

    if len(history) < 3:
        return 0.0

    # Compute sequence of step angular distances and online mean/variance
    # For predicting step i from i-2 and i-1 using SLERP extrapolation
    residuals = []
    for i in range(2, len(history)):
        p_prev = history[i - 2]
        p_curr = history[i - 1]
        target = history[i]

        dot_p = max(-1.0, min(1.0, float(np.dot(p_prev, p_curr))))
        theta = float(np.arccos(dot_p))

        if theta > 1e-5 and theta < np.pi - 1e-5:
            sin_t = float(np.sin(theta))
            # SLERP extrapolate forward by factor (1 + beta)
            w1 = float(np.sin(-beta * theta) / sin_t)
            w2 = float(np.sin((1.0 + beta) * theta) / sin_t)
            predicted = w1 * p_prev + w2 * p_curr
            p_norm = float(np.linalg.norm(predicted))
            if p_norm > 1e-8:
                predicted = predicted / p_norm
        else:
            predicted = p_curr

        # Geodesic angular distance on S^{D-1}
        dot_res = max(-1.0, min(1.0, float(np.dot(target, predicted))))
        delta = float(np.arccos(dot_res))
        residuals.append(delta)

    if not residuals:
        return 0.0

    # Running EMA of mean and variance across history residuals
    mu_delta = residuals[0]
    var_delta = 0.04  # baseline prior initialization

    for res in residuals[:-1]:
        var_delta = (1.0 - alpha) * var_delta + alpha * ((res - mu_delta) ** 2)
        mu_delta = (1.0 - alpha) * mu_delta + alpha * res

    final_res = residuals[-1]
    sigma = float(np.sqrt(max(1e-6, var_delta)))
    z_t = (final_res - mu_delta) / (sigma + 1e-5)

    # Dynamic logistic expansion
    surprise = float(1.0 / (1.0 + np.exp(-kappa * z_t)))
    return round(max(0.0, min(1.0, surprise)), 3)


def _compute_conceptual_velocity(
    current_vec: np.ndarray,
    all_recent: list[np.ndarray],
    phi: float = 0.4,
    v_ref: float = 1.0,
) -> tuple[float | None, float | None]:
    """# ponytail: compute instantaneous speed, calibrated velocity normalization, and phase transition magnitude."""
    if not all_recent:
        return 0.5, 0.0

    c_norm = np.linalg.norm(current_vec)
    c_vec = current_vec / c_norm if c_norm > 0 else current_vec

    # Assemble chronological trajectory: past history [-15:] followed by current vector
    history = []
    for v in all_recent[-15:]:
        norm = np.linalg.norm(v)
        history.append(v / norm if norm > 0 else v)
    history.append(c_vec)

    if len(history) < 2:
        return 0.5, 0.0

    displacements = [history[i] - history[i - 1] for i in range(1, len(history))]
    speeds = [float(np.linalg.norm(d)) for d in displacements]

    vel_ema = speeds[0]
    for s in speeds[1:]:
        vel_ema = phi * s + (1.0 - phi) * vel_ema

    # Anchor normalization to nominal reference scale v_ref (1.0) with adaptive expansion for high volatility
    v_scale = max(v_ref, float(np.percentile(speeds, 95)))
    norm_velocity = float(np.tanh(vel_ema / (v_scale + 1e-4)))
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

        # Geometric acceleration normalized by theoretical maximum bound (4.0)
        phase_trans = float((a_norm / (1.0 + vel_ema)) * turn_rate / 4.0)
        phase_trans = round(max(0.0, min(1.0, phase_trans)), 3)

    return norm_velocity, phase_trans

