"""Cybernetic Health, Deficit & Phase Shift Metrics (Audit #3, #7).

# ponytail: simple modular grouping for collapse pressure, DRR, Paskian health, deficit, and phase shifts
"""

import numpy as np

_DEFICIT_WEIGHTS = {
    "similarity": 0.30,
    "novelty": 0.25,
    "entropy": 0.20,
    "self_divergence": 0.25,
}

_VITALITY_WEIGHTS = {
    "novelty": 0.30,
    "entropy": 0.20,
    "self_divergence": 0.20,
    "reverse_perturbation": 0.15,
    "surprise": 0.15,
}


def _compute_collapse_pressure(
    rp_t: float | None,
    prev_mpi: float | None,
    rolling_entropy: float | None,
    conceptual_novelty: float | None,
    kappa: float = 6.0,
    d0: float = 0.55,
) -> float | None:
    """# Proposal 2: Sigmoidal Catastrophe Potential Well Collapse Pressure."""
    if rp_t is None:
        return None

    rp_val = float(rp_t)
    mpi_val = prev_mpi if prev_mpi is not None else 0.5
    entropy_val = rolling_entropy if rolling_entropy is not None else 0.5
    novelty_val = conceptual_novelty if conceptual_novelty is not None else 0.5

    v_pert = float(np.sqrt(max(0.0, rp_val * mpi_val)))
    v_ent = max(0.0, min(1.0, (entropy_val - 0.35) / (0.80 - 0.35)))
    v_nov = max(0.0, min(1.0, (novelty_val - 0.25) / (0.75 - 0.25)))

    v_sys = (v_pert ** 0.40) * (max(1e-4, v_ent) ** 0.30) * (max(1e-4, v_nov) ** 0.30)
    deficit = 1.0 - v_sys

    # Sigmoidal catastrophe transfer
    collapse = 1.0 / (1.0 + np.exp(-kappa * (deficit - d0)))
    return round(max(0.0, min(1.0, float(collapse))), 3)


def _compute_drr(
    recent_history: list[dict],
    window: int = 10,
    alpha: float = 0.4,
    gamma: float = 0.85,
    tau_flux: float = 0.04,
) -> float | None:
    """# Proposal 2: Geodesic Manifold Transport Ratio with Recency Weighting."""
    if not recent_history or len(recent_history) < 3:
        return 0.5

    human_vecs = []
    agent_vecs = []
    window_history = recent_history[-window * 2 :]
    for item in window_history:
        v = item.get("embedding")
        if v is None:
            continue
        norm = np.linalg.norm(v)
        v_norm = v / norm if norm > 0 else v
        if item.get("speaker") == "human":
            human_vecs.append(v_norm)
        else:
            agent_vecs.append(v_norm)

    if not human_vecs or not agent_vecs:
        return 0.5

    min_len = min(len(human_vecs), len(agent_vecs))
    if min_len < 2:
        return 0.5

    h_ema = human_vecs[0].copy()
    a_ema = agent_vecs[0].copy()

    def _calc_gap(h: np.ndarray, a: np.ndarray) -> float:
        nh = float(np.linalg.norm(h))
        na = float(np.linalg.norm(a))
        if nh > 1e-7 and na > 1e-7:
            cos_sim = float(np.dot(h / nh, a / na))
            return float(np.arccos(np.clip(cos_sim, -1.0, 1.0)))
        else:
            chord = float(np.linalg.norm(h - a))
            return float(2.0 * np.arcsin(min(1.0, 0.5 * chord)))

    gaps = [_calc_gap(h_ema, a_ema)]

    for i in range(1, min_len):
        h_ema = alpha * human_vecs[i] + (1.0 - alpha) * h_ema
        nh = np.linalg.norm(h_ema)
        if nh > 1e-7:
            h_ema = h_ema / nh
        a_ema = alpha * agent_vecs[i] + (1.0 - alpha) * a_ema
        na = np.linalg.norm(a_ema)
        if na > 1e-7:
            a_ema = a_ema / na
        gaps.append(_calc_gap(h_ema, a_ema))

    n_steps = len(gaps) - 1
    # Exponential recency weights: w_i = gamma^(n_steps - 1 - i)
    weights = [gamma ** (n_steps - 1 - i) for i in range(n_steps)]
    d_open = sum(weights[i] * max(0.0, gaps[i + 1] - gaps[i]) for i in range(n_steps))
    d_resolved = sum(weights[i] * max(0.0, gaps[i] - gaps[i + 1]) for i in range(n_steps))

    phi_flux = d_open + d_resolved
    gamma_flux = float(np.tanh(phi_flux / tau_flux))

    raw_ratio = d_resolved / (phi_flux + 1e-6)
    drr = (1.0 - gamma_flux) * 0.50 + gamma_flux * raw_ratio
    return round(max(0.0, min(1.0, float(drr))), 3)





def _compute_paskian_health(
    agent_self_divergence: float | None,
    conceptual_velocity: float | None,
    phase_transition_magnitude: float | None,
    coupling_coherence: float | None,
    mutual_perturbation: float | None,
    collapse_pressure: float | None,
    rolling_entropy: float | None,
    drr: float | None,
    epsilon: float = 0.08,
) -> float | None:
    """# Proposal 1: Regularized Generalized Power Mean (p=0.5) with Metabolic Floor."""
    div_val = agent_self_divergence if agent_self_divergence is not None else 0.5
    vel_val = conceptual_velocity if conceptual_velocity is not None else 0.5
    phase_val = phase_transition_magnitude if phase_transition_magnitude is not None else 0.0

    autonomy_index = (div_val + vel_val + phase_val) / 3.0

    coup_val = coupling_coherence if coupling_coherence is not None else 0.5
    mpi_val = mutual_perturbation if mutual_perturbation is not None else 0.5
    anti_collapse = 1.0 - (collapse_pressure if collapse_pressure is not None else 0.5)

    coordination_raw = (coup_val + mpi_val + anti_collapse) / 3.0
    drr_norm = drr if drr is not None else 0.5
    # Soft regularizer: DRR modulates coordination by at most 70%
    coordination_mod = coordination_raw * (0.30 + 0.70 * drr_norm)

    generativity_index = rolling_entropy if rolling_entropy is not None else 0.5

    # Power Mean with p = 0.5 and metabolic floor epsilon
    a_f = autonomy_index + epsilon
    c_f = coordination_mod + epsilon
    g_f = generativity_index + epsilon

    power_sum = (np.sqrt(a_f) + np.sqrt(c_f) + np.sqrt(g_f)) / 3.0
    pask_health = float((power_sum ** 2) - epsilon)
    return round(max(0.0, min(1.0, pask_health)), 3)


def _compute_deficit(
    s_t: float | None,
    novelty: float | None,
    rolling_entropy: float | None,
    agent_divergence: float | None,
) -> float | None:
    if s_t is None or novelty is None:
        return None

    ws = _DEFICIT_WEIGHTS["similarity"]
    wn = _DEFICIT_WEIGHTS["novelty"]
    we = _DEFICIT_WEIGHTS["entropy"]
    wd = _DEFICIT_WEIGHTS["self_divergence"]

    score = ws * s_t + wn * (1.0 - novelty)
    used_weight = ws + wn

    if rolling_entropy is not None:
        score += we * (1.0 - rolling_entropy)
        used_weight += we

    if agent_divergence is not None:
        score += wd * (1.0 - agent_divergence)
        used_weight += wd

    deficit = score / used_weight
    return round(max(0.0, min(1.0, float(deficit))), 3)


def _compute_vitality(
    novelty: float | None,
    rolling_entropy: float | None,
    agent_divergence: float | None,
    reverse_perturbation: float | None,
    surprise: float | None,
) -> float | None:
    """Vitality: how alive is this conversation right now?"""
    if novelty is None:
        return None

    wn = _VITALITY_WEIGHTS["novelty"]
    we = _VITALITY_WEIGHTS["entropy"]
    wd = _VITALITY_WEIGHTS["self_divergence"]
    wr = _VITALITY_WEIGHTS["reverse_perturbation"]
    ws = _VITALITY_WEIGHTS["surprise"]

    score = wn * novelty
    used_weight = wn

    if rolling_entropy is not None:
        score += we * rolling_entropy
        used_weight += we

    if agent_divergence is not None:
        score += wd * agent_divergence
        used_weight += wd

    if reverse_perturbation is not None:
        score += wr * reverse_perturbation
        used_weight += wr

    if surprise is not None:
        score += ws * surprise
        used_weight += ws

    score /= used_weight
    return round(max(0.0, min(1.0, float(score))), 3)


def _detect_phase_shifts(
    current: dict,
    prior: dict,
    threshold: float,
) -> list[dict]:
    """Detect abrupt metric changes that indicate reframing events."""
    shifts: list[dict] = []

    for key, label in [
        ("pairwise_similarity", "similarity_jump"),
        ("conceptual_novelty", "novelty_collapse"),
        ("reverse_perturbation", "perturbation_surge"),
        ("surprise_index", "surprise_spike"),
    ]:
        cur = current.get(key)
        prev = prior.get(key)
        if cur is not None and prev is not None:
            delta = abs(cur - prev)
            if delta > threshold:
                direction = "rise" if cur > prev else "drop"
                shifts.append(
                    {
                        "metric": key,
                        "event": label,
                        "delta": round(delta, 4),
                        "direction": direction,
                        "from": round(prev, 4),
                        "to": round(cur, 4),
                    }
                )

    return shifts
