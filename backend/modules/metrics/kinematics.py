"""Kinematics & Predictive Metrics (Audit #6).

# ponytail: simple modular grouping for predictive surprise and conceptual velocity
"""

import numpy as np


def _compute_surprise_index(
    current_vec: np.ndarray,
    all_recent: list[np.ndarray],
    alpha: float = 0.20,
    beta: float = 0.85,
    kappa: float = 1.95,
) -> float | None:
    """# Proposal 2: Epistemic Indeterminacy Baseline + Online Adaptive Geodesic SLERP."""
    if not all_recent:
        return 0.500

    c_norm = float(np.linalg.norm(current_vec))
    c_vec = current_vec / c_norm if c_norm > 1e-8 else current_vec

    history = []
    for v in all_recent[-12:]:
        norm = float(np.linalg.norm(v))
        history.append(v / norm if norm > 1e-8 else v)
    history.append(c_vec)

    if len(history) < 2:
        return 0.500

    if len(history) == 2:
        # Step 1: single-step angular displacement scaled across ambient bounds [0.30, 1.20]
        dot_p = max(-1.0, min(1.0, float(np.dot(history[0], history[1]))))
        theta = float(np.arccos(dot_p))
        s1 = np.clip((theta - 0.30) / (1.20 - 0.30), 0.10, 0.90)
        return round(float(s1), 3)

    # Compute sequence of step angular distances and online residual
    residuals = []
    for i in range(1, len(history)):
        if i == 1:
            predicted = history[0]
        else:
            p_prev = history[i - 2]
            p_curr = history[i - 1]
            dot_p = max(-1.0, min(1.0, float(np.dot(p_prev, p_curr))))
            theta = float(np.arccos(dot_p))

            if theta > 1e-5 and theta < np.pi - 1e-5:
                sin_t = float(np.sin(theta))
                # SLERP extrapolate forward along geodesic with momentum beta
                w1 = float(np.sin(-beta * theta) / sin_t)
                w2 = float(np.sin((1.0 + beta) * theta) / sin_t)
                predicted = w1 * p_prev + w2 * p_curr
                p_norm = float(np.linalg.norm(predicted))
                if p_norm > 1e-8:
                    predicted = predicted / p_norm
            else:
                predicted = p_curr

        # Geodesic angular distance on S^{D-1}
        dot_res = max(-1.0, min(1.0, float(np.dot(history[i], predicted))))
        delta = float(np.arccos(dot_res))
        residuals.append(delta)

    if not residuals:
        return 0.500

    # Online adaptive EMA tracking of residual mean and variance
    mu_delta = residuals[0]
    var_delta = 0.04

    for res in residuals[:-1]:
        var_delta = (1.0 - alpha) * var_delta + alpha * ((res - mu_delta) ** 2)
        mu_delta = (1.0 - alpha) * mu_delta + alpha * res

    final_res = residuals[-1]
    sigma = float(np.sqrt(max(1e-6, var_delta)))
    z_t = (final_res - mu_delta) / (sigma + 0.015)

    # Dynamic logistic expansion
    surprise = float(1.0 / (1.0 + np.exp(-kappa * z_t)))
    return round(max(0.0, min(1.0, surprise)), 3)


def _compute_conceptual_velocity(
    current_vec: np.ndarray,
    all_recent: list[np.ndarray],
    phi: float = 0.4,
) -> tuple[float | None, float | None]:
    """# Proposal 2: Tangent Parallel Transport and Acceleration Burst."""
    if not all_recent:
        return 0.5, 0.0

    c_norm = float(np.linalg.norm(current_vec))
    c_vec = current_vec / c_norm if c_norm > 1e-8 else current_vec

    history = []
    for v in all_recent[-20:]:
        norm = float(np.linalg.norm(v))
        history.append(v / norm if norm > 1e-8 else v)
    history.append(c_vec)

    if len(history) < 2:
        return 0.5, 0.0

    # Geodesic arc-lengths on S^{D-1}
    thetas = []
    for i in range(1, len(history)):
        dot_p = max(-1.0, min(1.0, float(np.dot(history[i], history[i - 1]))))
        thetas.append(float(np.arccos(dot_p)))

    # Tangent velocities v_i in T_{e_{i-1}} S^{D-1}
    curr_theta = thetas[-1]
    # Anchor to ambient 10th-90th quantile scale with dispersion protection
    if len(thetas) >= 4:
        p10 = float(np.percentile(thetas, 10))
        p90 = float(np.percentile(thetas, 90))
        q_low = min(p10, 0.45)
        q_high = max(p90, q_low + 0.35, 1.15)
    else:
        q_low = 0.40
        q_high = 1.15
    norm_velocity = (curr_theta - q_low) / (q_high - q_low + 1e-4)
    norm_velocity = round(max(0.0, min(1.0, float(norm_velocity))), 3)

    phase_trans = 0.0
    if len(history) >= 3:
        e_p2 = history[-3]
        e_p1 = history[-2]
        e_c = history[-1]

        # v_{t-1} in T_{e_{t-2}}
        v_prev = e_p1 - float(np.dot(e_p1, e_p2)) * e_p2
        nv_p = float(np.linalg.norm(v_prev))
        if nv_p > 1e-6:
            v_prev = v_prev / nv_p

        # Parallel transport v_{t-1} to T_{e_{t-1}} along geodesic from e_{t-2} to e_{t-1}
        dot_trans = float(np.dot(e_p1, v_prev))
        denom = 1.0 + float(np.dot(e_p2, e_p1))
        if abs(denom) > 1e-5:
            v_transported = v_prev - (dot_trans / denom) * (e_p2 + e_p1)
        else:
            v_transported = v_prev
        nv_trans = float(np.linalg.norm(v_transported))
        if nv_trans > 1e-6:
            v_transported = v_transported / nv_trans

        # v_t in T_{e_{t-1}}
        v_curr = e_c - float(np.dot(e_c, e_p1)) * e_p1
        nv_c = float(np.linalg.norm(v_curr))
        if nv_c > 1e-6:
            v_curr = v_curr / nv_c

        cos_psi = max(-1.0, min(1.0, float(np.dot(v_curr, v_transported))))
        omega = float(np.arccos(cos_psi) / np.pi)
        phase_trans = round(max(0.0, min(1.0, float(omega * np.sqrt(norm_velocity)))), 3)

    return norm_velocity, phase_trans

