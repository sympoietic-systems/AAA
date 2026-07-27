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
) -> float | None:
    """# ponytail: compute triadic collapse pressure index (renamed from boringness)."""
    if rp_t is None:
        return None

    rp_val = float(rp_t)
    mpi_val = prev_mpi if prev_mpi is not None else 0.5
    entropy_val = rolling_entropy if rolling_entropy is not None else 0.5
    novelty_val = conceptual_novelty if conceptual_novelty is not None else 0.5

    pert_geom_mean = float(np.sqrt(max(0.0, rp_val * mpi_val)))
    pert_failure = 1.0 - pert_geom_mean

    collapse = pert_failure * (1.0 - entropy_val) * (1.0 - novelty_val)
    return round(max(0.0, min(1.0, float(collapse))), 3)


def _compute_drr(
    recent_history: list[dict],
    window: int = 10,
    alpha: float = 0.4,
    k_log: float = 2.0,
) -> float | None:
    """# ponytail: compute multi-turn alignment gap DRR (ratio of resolved gap to opened gap)."""
    if not recent_history or len(recent_history) < 3:
        return 0.5

    human_vecs = []
    agent_vecs = []
    for item in recent_history[: window * 2]:
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

    human_vecs.reverse()
    agent_vecs.reverse()

    min_len = min(len(human_vecs), len(agent_vecs))
    if min_len < 2:
        return 0.5

    h_ema = human_vecs[0].copy()
    a_ema = agent_vecs[0].copy()
    gaps = [float(np.linalg.norm(h_ema - a_ema))]

    for i in range(1, min_len):
        h_ema = alpha * human_vecs[i] + (1.0 - alpha) * h_ema
        a_ema = alpha * agent_vecs[i] + (1.0 - alpha) * a_ema
        gaps.append(float(np.linalg.norm(h_ema - a_ema)))

    d_open = sum(max(0.0, gaps[i] - gaps[i - 1]) for i in range(1, len(gaps)))
    d_resolved = sum(max(0.0, gaps[i - 1] - gaps[i]) for i in range(1, len(gaps)))

    drr_raw = d_resolved / (d_open + 1e-4)
    drr_norm = 1.0 - float(np.exp(-k_log * abs(drr_raw - 1.0)))
    return round(max(0.0, min(1.0, drr_norm)), 3)


def _compute_paskian_health(
    agent_self_divergence: float | None,
    conceptual_velocity: float | None,
    phase_transition_magnitude: float | None,
    coupling_coherence: float | None,
    mutual_perturbation: float | None,
    collapse_pressure: float | None,
    rolling_entropy: float | None,
    drr: float | None,
) -> float | None:
    """# ponytail: compute Gordon Pask triadic cybernetic vitality index (geometric mean)."""
    div_val = agent_self_divergence if agent_self_divergence is not None else 0.5
    vel_val = conceptual_velocity if conceptual_velocity is not None else 0.5
    phase_val = phase_transition_magnitude if phase_transition_magnitude is not None else 0.0

    autonomy_index = (div_val + vel_val + phase_val) / 3.0

    coup_val = coupling_coherence if coupling_coherence is not None else 0.5
    mpi_val = mutual_perturbation if mutual_perturbation is not None else 0.5
    anti_collapse = 1.0 - (collapse_pressure if collapse_pressure is not None else 0.5)

    coordination_index = (coup_val + mpi_val + anti_collapse) / 3.0
    drr_modifier = drr if drr is not None else 0.5

    generativity_index = rolling_entropy if rolling_entropy is not None else 0.5

    pask_raw = autonomy_index * (coordination_index * drr_modifier) * generativity_index
    pask_health = float(np.cbrt(max(0.0, pask_raw)))
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

    deficit = ws * s_t + wn * (1.0 - novelty)

    if rolling_entropy is not None:
        entropy_norm = min(1.0, rolling_entropy / 0.25)
        deficit += we * (1.0 - entropy_norm)

    if agent_divergence is not None:
        deficit += wd * (1.0 - agent_divergence)
    else:
        deficit *= 1.0 / (ws + wn)

    return max(0.0, min(1.0, deficit))


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

    if rolling_entropy is not None:
        entropy_norm = min(1.0, rolling_entropy / 0.25)
        score += we * entropy_norm

    if agent_divergence is not None:
        score += wd * agent_divergence

    if reverse_perturbation is not None:
        score += wr * reverse_perturbation

    if surprise is not None:
        score += ws * surprise

    used_weight = wn
    if rolling_entropy is not None:
        used_weight += we
    if agent_divergence is not None:
        used_weight += wd
    if reverse_perturbation is not None:
        used_weight += wr
    if surprise is not None:
        used_weight += ws

    score /= used_weight
    return max(0.0, min(1.0, score))


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
