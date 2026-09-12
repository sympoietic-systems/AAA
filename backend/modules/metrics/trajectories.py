"""Trajectory & Directional Perturbation Metrics (Audit #4, #5).

# ponytail: simple modular grouping for coupling, self-divergence, and directional perturbations
"""

import numpy as np


def _compute_coupling_coherence(
    recent_history: list[dict],
    window: int = 8,
    decay_lambda: float = 0.2,
) -> float | None:
    """# Proposal 3: Harmonic Resonant Entrainment (Directional Agonism + Velocity Cadence)."""
    if not recent_history or len(recent_history) < 2:
        return None

    valid_items = []
    for item in recent_history:
        v = item.get("embedding")
        if v is not None:
            norm = float(np.linalg.norm(v))
            v_norm = v / norm if norm > 0 else v
            valid_items.append({
                "speaker": item.get("speaker", "human"),
                "embedding": v_norm,
            })

    if len(valid_items) < 2:
        return None

    interactions = []
    prior_speaker_vecs = {}

    for item in valid_items:
        spk = item["speaker"]
        vec = item["embedding"]
        other_spks = [s for s in prior_speaker_vecs if s != spk]
        if other_spks:
            other_spk = other_spks[-1]
            other_vec = prior_speaker_vecs[other_spk]
            if spk in prior_speaker_vecs:
                curr_prev = prior_speaker_vecs[spk]
                u = other_vec - curr_prev
                v = vec - curr_prev
                u_n = float(np.linalg.norm(u))
                v_n = float(np.linalg.norm(v))
                if u_n > 1e-6 and v_n > 1e-6:
                    rho = abs(float(np.dot(u / u_n, v / v_n)))
                    dir_score = float(np.tanh(2.5 * rho))
                    cadence = 1.0 - (abs(v_n - u_n) / (v_n + u_n + 1e-4))
                    h_score = (2.0 * dir_score * cadence) / (dir_score + cadence + 1e-4)
                    interactions.append(max(0.0, min(1.0, h_score)))
        prior_speaker_vecs[spk] = vec

    if not interactions:
        disps = [valid_items[i]["embedding"] - valid_items[i - 1]["embedding"] for i in range(1, len(valid_items))]
        if len(disps) >= 2:
            d_curr = disps[-1]
            d_prev = disps[-2]
            dc_n = float(np.linalg.norm(d_curr))
            dp_n = float(np.linalg.norm(d_prev))
            if dc_n > 1e-6 and dp_n > 1e-6:
                cos_val = abs(float(np.dot(d_curr / dc_n, d_prev / dp_n)))
                cadence = 1.0 - (abs(dc_n - dp_n) / (dc_n + dp_n + 1e-4))
                h_score = (2.0 * cos_val * cadence) / (cos_val + cadence + 1e-4)
                interactions.append(max(0.0, min(1.0, h_score)))
        else:
            return 0.5

    recent_inters = interactions[-window:]
    weighted_scores = []
    weights = []
    for i, s in enumerate(reversed(recent_inters)):
        w = float(np.exp(-decay_lambda * i))
        weighted_scores.append(s * w)
        weights.append(w)

    if not weights or sum(weights) == 0:
        return 0.5

    score = sum(weighted_scores) / sum(weights)
    return round(max(0.0, min(1.0, float(score))), 3)



def _compute_agent_self_divergence(
    current_vec: np.ndarray,
    current_speaker: str,
    prior_agent: list[np.ndarray],
    max_recent_window: int = 5,
    beta: float = 0.25,
) -> float | None:
    """# ponytail: compute agent self-divergence via recency-decayed max self-similarity and repeat penalty."""
    if current_speaker not in ("agent", "apparatus"):
        return None

    if not prior_agent:
        return 0.5

    c_norm = np.linalg.norm(current_vec)
    c_vec = current_vec / c_norm if c_norm > 0 else current_vec

    agent_norms = []
    for v in prior_agent:
        norm = np.linalg.norm(v)
        agent_norms.append(v / norm if norm > 0 else v)

    # Evaluate recency-decayed self-similarity from newest prior agent utterance backward
    recent_agents = agent_norms[-max_recent_window:]
    s_self_scores = []
    for i, v in enumerate(reversed(recent_agents)):
        cos_sim = max(0.0, min(1.0, float(np.dot(c_vec, v))))
        w = float(np.exp(-beta * i))
        s_self_scores.append(cos_sim * w)

    s_self = max(s_self_scores) if s_self_scores else 0.0

    # Long-range repeat penalty applies to utterances older than max_recent_window
    penalty = 0.0
    if len(agent_norms) > max_recent_window:
        older_agents = agent_norms[:-max_recent_window]
        long_sims = [float(np.dot(c_vec, v)) for v in older_agents]
        max_long = max(long_sims) if long_sims else 0.0
        if max_long > 0.85:
            penalty = 0.3 * min(1.0, (max_long - 0.85) / 0.15)

    divergence = 1.0 - s_self - penalty
    return round(max(0.0, min(1.0, float(divergence))), 3)


def _compute_reverse_perturbation(
    current_vec: np.ndarray,
    prior_human: list[np.ndarray],
    prior_agent: list[np.ndarray],
    gamma: float = 1.2,
    tau_pert: float = 1.35,
) -> float | None:
    """# Proposal 1: Transverse Vector Shear Perturbation."""
    if not prior_human or not prior_agent:
        return None

    h_curr = current_vec / (np.linalg.norm(current_vec) + 1e-8)
    h_prev = prior_human[-1] / (np.linalg.norm(prior_human[-1]) + 1e-8)
    a_prev = prior_agent[-1] / (np.linalg.norm(prior_agent[-1]) + 1e-8)

    g = a_prev - h_prev
    g_norm = float(np.linalg.norm(g))
    if g_norm < 1e-5:
        return 0.0
    g_hat = g / g_norm

    v_h = h_curr - h_prev
    v_parallel = float(np.dot(v_h, g_hat))
    v_perp = v_h - v_parallel * g_hat
    v_perp_norm = float(np.linalg.norm(v_perp))

    shear_mag = float(np.sqrt(v_parallel ** 2 + gamma * (v_perp_norm ** 2)))
    rp_t = float(np.tanh(shear_mag / tau_pert))
    return round(max(0.0, min(1.0, rp_t)), 3)


def _compute_forward_perturbation(
    current_vec: np.ndarray,
    prior_human: list[np.ndarray],
    prior_agent: list[np.ndarray],
    gamma: float = 1.2,
    tau_pert: float = 1.35,
) -> float | None:
    """# Proposal 1: Transverse Vector Shear Perturbation."""
    if not prior_human or not prior_agent:
        return None

    a_curr = current_vec / (np.linalg.norm(current_vec) + 1e-8)
    h_curr = prior_human[-1] / (np.linalg.norm(prior_human[-1]) + 1e-8)
    a_prev = prior_agent[-1] / (np.linalg.norm(prior_agent[-1]) + 1e-8)

    g = h_curr - a_prev
    g_norm = float(np.linalg.norm(g))
    if g_norm < 1e-5:
        return 0.0
    g_hat = g / g_norm

    v_a = a_curr - a_prev
    v_parallel = float(np.dot(v_a, g_hat))
    v_perp = v_a - v_parallel * g_hat
    v_perp_norm = float(np.linalg.norm(v_perp))

    shear_mag = float(np.sqrt(v_parallel ** 2 + gamma * (v_perp_norm ** 2)))
    fp_t = float(np.tanh(shear_mag / tau_pert))
    return round(max(0.0, min(1.0, fp_t)), 3)


def _compute_mutual_perturbation(
    rp_t: float | None,
    fp_t: float | None,
) -> float | None:
    """# Proposal 1: Non-annihilating Power Mean MPI (p=0.5)."""
    if rp_t is None and fp_t is None:
        return None
    r_val = rp_t if rp_t is not None else 0.5
    f_val = fp_t if fp_t is not None else 0.5
    mpi = float(((np.sqrt(max(0.0, r_val)) + np.sqrt(max(0.0, f_val))) / 2.0) ** 2)
    return round(max(0.0, min(1.0, mpi)), 3)
