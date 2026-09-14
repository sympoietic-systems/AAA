"""Resonance & Manifold Spectral Metrics (Audit #1, #2, #3).

# ponytail: simple modular grouping for similarity, novelty, and manifold entropy
"""

import numpy as np


def _compute_pairwise_similarity(
    current_vec: np.ndarray,
    current_speaker: str,
    recent_history: list[dict],
    decay_lambda: float = 0.15,
    gamma: float = 1.1,
) -> float | None:
    """# Proposal 1: Signed Polarity Alignment with Agential Tension."""
    if not recent_history:
        return None

    weighted_sims = []
    weights = []
    c_norm = np.linalg.norm(current_vec)
    c_vec = current_vec / c_norm if c_norm > 0 else current_vec

    recent_items = recent_history[-15:]
    for i, item in enumerate(reversed(recent_items)):
        v = item.get("embedding")
        if v is None:
            continue
        v_norm = np.linalg.norm(v)
        v_vec = v / v_norm if v_norm > 0 else v

        dot_sim = float(np.dot(c_vec, v_vec))
        signed_sim = float(np.sign(dot_sim) * (abs(dot_sim) ** gamma))

        speaker = item.get("speaker", "human")
        speaker_factor = 0.8 if speaker == current_speaker else 1.2
        decay = float(np.exp(-decay_lambda * i))
        w = decay * speaker_factor

        weighted_sims.append(signed_sim * w)
        weights.append(w)

    if not weights or sum(weights) == 0:
        return None

    weighted_sim = float(sum(weighted_sims) / sum(weights))
    return round(max(-1.0, min(1.0, weighted_sim)), 3)


def _compute_conceptual_novelty(
    current_vec: np.ndarray,
    recent_history: list[dict],
    prior_centroid: np.ndarray | dict | None = None,
    alpha_fast: float = 0.35,
    alpha_slow: float = 0.08,
    theta_nomad: float = 1.35,
) -> tuple[float | None, dict]:
    """# Proposal 1: Multi-Scale Decoupled Dual-Horizon Novelty."""
    c_norm = np.linalg.norm(current_vec)
    c_vec = current_vec / c_norm if c_norm > 0 else current_vec

    if not recent_history:
        return None, {"fast": c_vec, "slow": c_vec}

    if prior_centroid is None:
        c_fast = c_vec
        c_slow = c_vec
    elif isinstance(prior_centroid, dict):
        c_f = prior_centroid.get("fast", c_vec)
        c_s = prior_centroid.get("slow", c_vec)
        c_fast = (alpha_fast * c_vec) + ((1.0 - alpha_fast) * c_f)
        c_slow = (alpha_slow * c_vec) + ((1.0 - alpha_slow) * c_s)
    else:
        c_fast = (alpha_fast * c_vec) + ((1.0 - alpha_fast) * prior_centroid)
        c_slow = (alpha_slow * c_vec) + ((1.0 - alpha_slow) * prior_centroid)

    nf = float(np.linalg.norm(c_fast))
    if nf > 1e-8:
        c_fast = c_fast / nf
    ns = float(np.linalg.norm(c_slow))
    if ns > 1e-8:
        c_slow = c_slow / ns

    dot_f = max(-1.0, min(1.0, float(np.dot(c_vec, c_fast))))
    dot_s = max(-1.0, min(1.0, float(np.dot(c_vec, c_slow))))

    d_local = float(np.arccos(dot_f))
    d_global = float(np.arccos(dot_s))

    novelty_raw = float(np.sqrt(d_local * d_global))
    novelty = max(0.0, min(1.0, (novelty_raw - 0.45) / (1.25 - 0.45)))

    return round(float(novelty), 3), {"fast": c_fast, "slow": c_slow}


def _compute_rolling_entropy(
    current_vec: np.ndarray,
    recent_history: list[dict],
    window: int = 8,
    sigma_ref: float = 0.15,
) -> float | None:
    """# Proposal 1: Variance-Gated Participation Ratio Entropy."""
    if not recent_history:
        return 0.5

    c_norm = np.linalg.norm(current_vec)
    c_vec = current_vec / c_norm if c_norm > 0 else current_vec

    hist_vecs = [c_vec]
    for item in recent_history[-(window - 1) :]:
        v = item.get("embedding")
        if v is not None:
            norm = np.linalg.norm(v)
            hist_vecs.append(v / norm if norm > 0 else v)

    K = len(hist_vecs)
    if K < 2:
        return 0.5
    if K == 2:
        dot_val = max(-1.0, min(1.0, float(np.dot(hist_vecs[0], hist_vecs[1]))))
        return round(float(np.arccos(dot_val) / np.pi), 4)

    # Center matrix E (K x D)
    E = np.stack(hist_vecs)
    mu_E = np.mean(E, axis=0)
    E_centered = E - mu_E

    # Gram matrix C' = (1/K) * E_centered * E_centered^T (K x K)
    gram = (1.0 / K) * np.dot(E_centered, E_centered.T)
    tr_G = float(np.trace(gram))

    if tr_G < 1e-6:
        return 0.0

    # Tr(G^2) is sum of squares of elements of symmetric Gram matrix
    tr_G2 = float(np.sum(gram ** 2))
    d_eff = (tr_G ** 2) / (tr_G2 + 1e-8)

    # Normalize participation ratio to [0, 1]
    pr_norm = (d_eff - 1.0) / max(1.0, float(K - 1))
    var_gate = float(np.tanh(tr_G / sigma_ref))
    entropy = pr_norm * var_gate
    return round(max(0.0, min(1.0, float(entropy))), 4)
