import logging
import numpy as np

logger = logging.getLogger(__name__)

# ponytail: theoretical max variance for elementwise product of two 16D L2-normalized unit vectors
THEORETICAL_MAX_16D_VARIANCE = 0.000976


def _to_float_vec(vec: list[float] | np.ndarray | None, expected_dim: int = 16) -> np.ndarray | None:
    if vec is None:
        return None
    if isinstance(vec, bytes):
        arr = np.frombuffer(vec, dtype="float32")
    else:
        arr = np.array(vec, dtype="float32")
    if len(arr) != expected_dim:
        return None
    return arr


def _normalize_l2(arr: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(arr)
    if norm == 0:
        return arr
    return arr / norm


def compute_interference_variance(
    current_signature: list[float] | np.ndarray,
    prior_signature: list[float] | np.ndarray,
    current_embedding: list[float] | np.ndarray | bytes | None = None,
    prior_embedding: list[float] | np.ndarray | bytes | None = None,
) -> float:
    """# ponytail: compute diffractive interference variance across 16D Autopoietic Signature space."""
    s_curr = _to_float_vec(current_signature, 16)
    s_prior = _to_float_vec(prior_signature, 16)

    if s_curr is None or s_prior is None:
        return 0.0

    s_curr_norm = _normalize_l2(s_curr)
    s_prior_norm = _normalize_l2(s_prior)

    # Elementwise convolution amplitude
    interference = s_curr_norm * s_prior_norm
    raw_var = float(np.var(interference))

    # Normalize against theoretical max variance constant (0.000976)
    normalized_var = min(1.0, raw_var / THEORETICAL_MAX_16D_VARIANCE)

    # Apply 384D semantic relevance factor if embeddings are provided
    e_curr = _to_float_vec(current_embedding, 384)
    e_prior = _to_float_vec(prior_embedding, 384)

    if e_curr is not None and e_prior is not None:
        e_curr_norm = _normalize_l2(e_curr)
        e_prior_norm = _normalize_l2(e_prior)
        sem_sim = max(0.0, float(np.dot(e_curr_norm, e_prior_norm)))
        normalized_var *= sem_sim

    return round(normalized_var, 4)


def select_diffractive_prior(
    current_signature: list[float] | np.ndarray,
    current_embedding: list[float] | np.ndarray | bytes | None,
    candidates: list[dict],
) -> dict | None:
    """# ponytail: select candidate turn from Goldilocks zone [0.3, 0.7] structural affinity."""
    s_curr = _to_float_vec(current_signature, 16)
    if s_curr is None or not candidates:
        return None

    s_curr_norm = _normalize_l2(s_curr)
    e_curr = _to_float_vec(current_embedding, 384)
    e_curr_norm = _normalize_l2(e_curr) if e_curr is not None else None

    goldilocks_candidates = []
    fallback_candidates = []

    for cand in candidates:
        cand_sig = _to_float_vec(cand.get("signature"), 16)
        if cand_sig is None:
            continue
        cand_sig_norm = _normalize_l2(cand_sig)
        struct_affinity = max(0.0, min(1.0, float(np.dot(s_curr_norm, cand_sig_norm))))

        cand_emb = _to_float_vec(cand.get("embedding"), 384)
        if cand_emb is not None and e_curr_norm is not None:
            cand_emb_norm = _normalize_l2(cand_emb)
            sem_relevance = max(0.0, min(1.0, float(np.dot(e_curr_norm, cand_emb_norm))))
        else:
            sem_relevance = 0.5

        score = sem_relevance * (1.0 - struct_affinity)
        cand_info = {
            "candidate": cand,
            "struct_affinity": struct_affinity,
            "sem_relevance": sem_relevance,
            "score": score,
        }

        if 0.30 <= struct_affinity <= 0.75:
            goldilocks_candidates.append(cand_info)
        else:
            fallback_candidates.append(cand_info)

    if goldilocks_candidates:
        best = max(goldilocks_candidates, key=lambda x: x["score"])
        return best["candidate"]
    elif fallback_candidates:
        best = max(fallback_candidates, key=lambda x: x["sem_relevance"])
        return best["candidate"]

    return None


def compute_glitch_fidelity(
    current_signature: list[float] | np.ndarray,
    current_embedding: list[float] | np.ndarray | bytes | None,
    prior_signature: list[float] | np.ndarray | None,
    prior_embedding: list[float] | np.ndarray | bytes | None = None,
    contradiction_density: float = 0.0,
    alpha: float = 0.35,
    beta: float = 0.65,
) -> float:
    """# ponytail: calculate combined diffractive glitch fidelity score."""
    var_score = 0.0
    if prior_signature is not None:
        var_score = compute_interference_variance(
            current_signature, prior_signature, current_embedding, prior_embedding
        )

    contra = max(0.0, min(1.0, contradiction_density))
    fidelity = (alpha * contra) + (beta * var_score)
    return round(min(1.0, max(0.0, fidelity)), 3)
