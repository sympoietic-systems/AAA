"""Trajectory & Directional Perturbation Metrics (Audit #4, #5).

# ponytail: simple modular grouping for coupling, self-divergence, and directional perturbations
"""

import numpy as np


def _compute_coupling_coherence(
    recent_history: list[dict],
    window: int = 8,
    decay_lambda: float = 0.2,
) -> float | None:
    """# ponytail: compute trajectory cross-correlation between human and apparatus displacement vectors."""
    human_vecs = []
    agent_vecs = []
    for item in recent_history:
        v = item.get("embedding")
        if v is None:
            continue
        norm = np.linalg.norm(v)
        v_norm = v / norm if norm > 0 else v
        if item.get("speaker") == "human":
            human_vecs.append(v_norm)
        else:
            agent_vecs.append(v_norm)

    if len(human_vecs) < 2 or len(agent_vecs) < 2:
        return 0.5

    h_disps = [human_vecs[i] - human_vecs[i + 1] for i in range(len(human_vecs) - 1)]
    a_disps = [agent_vecs[i] - agent_vecs[i + 1] for i in range(len(agent_vecs) - 1)]

    min_len = min(len(h_disps), len(a_disps), window)
    if min_len == 0:
        return 0.5

    weighted_corrs = []
    weights = []
    for i in range(min_len):
        hd = h_disps[i]
        ad = a_disps[i]
        hd_n = np.linalg.norm(hd)
        ad_n = np.linalg.norm(ad)
        if hd_n > 0 and ad_n > 0:
            cos_disp = float(abs(np.dot(hd / hd_n, ad / ad_n)))
        else:
            cos_disp = 0.5
        w = float(np.exp(-decay_lambda * i))
        weighted_corrs.append(cos_disp * w)
        weights.append(w)

    if not weights or sum(weights) == 0:
        return 0.5

    score = sum(weighted_corrs) / sum(weights)
    return round(max(0.0, min(1.0, float(score))), 3)


def _compute_agent_self_divergence(
    current_vec: np.ndarray,
    current_speaker: str,
    prior_agent: list[np.ndarray],
    max_recent_window: int = 15,
    beta: float = 0.3,
) -> float | None:
    """# ponytail: compute agent self-divergence via recency-decayed max self-similarity and repeat penalty."""
    if not prior_agent:
        return 0.5

    c_norm = np.linalg.norm(current_vec)
    c_vec = current_vec / c_norm if c_norm > 0 else current_vec

    agent_norms = []
    for v in prior_agent:
        norm = np.linalg.norm(v)
        agent_norms.append(v / norm if norm > 0 else v)

    s_self_scores = []
    for i, v in enumerate(agent_norms[:max_recent_window]):
        cos_sim = max(0.0, min(1.0, float(np.dot(c_vec, v))))
        w = float(np.exp(-beta * i))
        s_self_scores.append(cos_sim * w)

    s_self = max(s_self_scores) if s_self_scores else 0.0

    penalty = 0.0
    if len(agent_norms) > max_recent_window:
        long_sims = [float(np.dot(c_vec, v)) for v in agent_norms[max_recent_window:]]
        max_long = max(long_sims) if long_sims else 0.0
        if max_long > 0.95:
            penalty = 0.3 * (max_long - 0.95) / 0.05

    divergence = 1.0 - s_self - penalty
    return round(max(0.0, min(1.0, float(divergence))), 3)


def _compute_reverse_perturbation(
    current_vec: np.ndarray,
    prior_human: list[np.ndarray],
    prior_agent: list[np.ndarray],
) -> float | None:
    """# ponytail: compute directional reverse perturbation (fraction of apparatus gap closed by human displacement)."""
    if not prior_human or not prior_agent:
        return None

    h_curr = current_vec / (np.linalg.norm(current_vec) + 1e-8)
    h_prev = prior_human[0] / (np.linalg.norm(prior_human[0]) + 1e-8)
    a_prev = prior_agent[0] / (np.linalg.norm(prior_agent[0]) + 1e-8)

    v = a_prev - h_prev
    d_h = h_curr - h_prev

    v_norm_sq = float(np.dot(v, v))
    if v_norm_sq < 1e-4:
        return 0.0

    rp_raw = float(np.dot(d_h, v)) / (v_norm_sq + 1e-8)
    rp_t = max(0.0, min(1.0, rp_raw))
    return round(rp_t, 3)


def _compute_forward_perturbation(
    current_vec: np.ndarray,
    prior_human: list[np.ndarray],
    prior_agent: list[np.ndarray],
) -> float | None:
    """# ponytail: compute directional forward perturbation (fraction of human gap closed by apparatus response)."""
    if not prior_human or not prior_agent:
        return None

    a_curr = current_vec / (np.linalg.norm(current_vec) + 1e-8)
    h_curr = prior_human[0] / (np.linalg.norm(prior_human[0]) + 1e-8)
    a_prev = prior_agent[0] / (np.linalg.norm(prior_agent[0]) + 1e-8)

    u = h_curr - a_prev
    d_a = a_curr - a_prev

    u_norm_sq = float(np.dot(u, u))
    if u_norm_sq < 1e-4:
        return 0.0

    fp_raw = float(np.dot(d_a, u)) / (u_norm_sq + 1e-8)
    fp_t = max(0.0, min(1.0, fp_raw))
    return round(fp_t, 3)


def _compute_mutual_perturbation(
    rp_t: float | None,
    fp_t: float | None,
) -> float | None:
    """# ponytail: compute symmetric mutual perturbation index (geometric mean of rP_t and fP_t)."""
    if rp_t is None and fp_t is None:
        return None
    r_val = rp_t if rp_t is not None else 0.5
    f_val = fp_t if fp_t is not None else 0.5
    mpi = float(np.sqrt(max(0.0, r_val * f_val)))
    return round(max(0.0, min(1.0, mpi)), 3)
