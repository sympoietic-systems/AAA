"""Resonance & Manifold Spectral Metrics (Audit #1, #2, #3).

# ponytail: simple modular grouping for similarity, novelty, and manifold entropy
"""

import numpy as np


def _compute_pairwise_similarity(
    current_vec: np.ndarray,
    current_speaker: str,
    recent_history: list[dict],
    decay_lambda: float = 0.15,
) -> float | None:
    """# ponytail: compute reciprocal perturbation coherence with exponential decay and speaker weighting."""
    if not recent_history:
        return None

    sims = []
    c_norm = np.linalg.norm(current_vec)
    c_vec = current_vec / c_norm if c_norm > 0 else current_vec

    for i, item in enumerate(recent_history):
        v = item.get("embedding")
        if v is None:
            continue
        v_norm = np.linalg.norm(v)
        v_vec = v / v_norm if v_norm > 0 else v

        dot_sim = float(np.dot(c_vec, v_vec))
        cos_sim = max(0.0, min(1.0, dot_sim))

        speaker = item.get("speaker", "human")
        speaker_factor = 0.8 if speaker == current_speaker else 1.2
        decay = float(np.exp(-decay_lambda * i))

        sims.append(cos_sim * decay * speaker_factor)

    if not sims:
        return None

    weighted_sim = float(np.mean(sims))
    return max(0.0, min(1.0, weighted_sim))


def _compute_conceptual_novelty(
    current_vec: np.ndarray,
    recent_history: list[dict],
    prior_centroid: np.ndarray | None = None,
    alpha: float = 0.3,
) -> tuple[float | None, np.ndarray]:
    """# ponytail: compute sediment drift magnitude from context centroid and scatter."""
    c_norm = np.linalg.norm(current_vec)
    c_vec = current_vec / c_norm if c_norm > 0 else current_vec

    if not recent_history:
        return None, c_vec

    hist_vecs = []
    for item in recent_history:
        v = item.get("embedding")
        if v is not None:
            norm = np.linalg.norm(v)
            hist_vecs.append(v / norm if norm > 0 else v)

    if not hist_vecs:
        return None, c_vec

    # Update context centroid EMA
    if prior_centroid is None:
        new_centroid = c_vec
    else:
        new_centroid = (alpha * c_vec) + ((1.0 - alpha) * prior_centroid)
        norm_cent = np.linalg.norm(new_centroid)
        if norm_cent > 0:
            new_centroid = new_centroid / norm_cent

    # Compute raw drift distance from centroid
    drift_raw = 1.0 - max(0.0, min(1.0, float(np.dot(c_vec, new_centroid))))

    # Compute scatter standard deviation across history turns relative to centroid
    scatters = [1.0 - max(0.0, min(1.0, float(np.dot(hv, new_centroid)))) for hv in hist_vecs]
    sigma_context = float(np.std(scatters)) if len(scatters) > 1 else 0.10

    # Normalized drift distance
    drift_norm = float(np.tanh(drift_raw / (sigma_context + 0.01)))

    # Compute velocity relative to prior history turn drift
    prior_drift = scatters[0] if scatters else 0.01
    velocity = min(1.0, abs(drift_raw - prior_drift) / max(0.01, prior_drift))

    # Combined novelty score (0.7 drift + 0.3 velocity)
    novelty = (0.7 * drift_norm) + (0.3 * velocity)
    novelty = max(0.0, min(1.0, float(novelty)))

    return round(novelty, 3), new_centroid


def _compute_rolling_entropy(
    current_vec: np.ndarray,
    recent_history: list[dict],
    window: int = 8,
    eps_reg: float = 1e-8,
) -> float | None:
    """# ponytail: compute manifold spectral entropy from embedding Gram matrix eigendecomposition."""
    if not recent_history:
        return 0.5

    c_norm = np.linalg.norm(current_vec)
    c_vec = current_vec / c_norm if c_norm > 0 else current_vec

    hist_vecs = [c_vec]
    for item in recent_history[: window - 1]:
        v = item.get("embedding")
        if v is not None:
            norm = np.linalg.norm(v)
            hist_vecs.append(v / norm if norm > 0 else v)

    K = len(hist_vecs)
    if K < 2:
        return 0.5

    # Center matrix E (K x D)
    E = np.stack(hist_vecs)
    mu_E = np.mean(E, axis=0)
    E_centered = E - mu_E

    # Gram matrix C' = (1/K) * E_centered * E_centered^T (K x K)
    gram = (1.0 / K) * np.dot(E_centered, E_centered.T)
    gram_trace = float(np.trace(gram))

    if gram_trace < 1e-6:
        return 0.0

    try:
        eigvals = np.linalg.eigvalsh(gram)
        eigvals = np.maximum(eigvals, eps_reg)
        p = eigvals / np.sum(eigvals)
        h_raw = float(-np.sum(p * np.log(p)))
        max_h = float(np.log(K))
        entropy = h_raw / max_h if max_h > 0 else 0.5
        return round(max(0.0, min(1.0, float(entropy))), 4)
    except Exception:
        return 0.5
