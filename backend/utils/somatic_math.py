"""Rhizomatic Utility Scoring — mathematical foundation for recursive research.

Implements the augmented 4-term utility function and diffractive similarity
detection that enables lateral lines of flight during autonomous exploration.

See docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 6.
"""

import numpy as np
from typing import Optional

from backend.utils.vector import cosine_similarity

# ── Default Weights ──────────────────────────────────────────────────

DEFAULT_WEIGHTS = {
    "relevance": 0.40,      # w1 — semantic match to query
    "novelty": 0.25,         # w2 — avoid redundant retrieval
    "cost": 0.20,            # w3 — metabolic efficiency
    "diffractive": 0.15,     # w4 — structural isomorphism detection
}

DEFAULT_LATERAL_THRESHOLD = 0.72       # S_diff trigger for line-of-flight
DEFAULT_DETOUR_ALPHA = 0.5             # Query interpolation weight on detour


# ── Diffractive Similarity ───────────────────────────────────────────

def calculate_diffractive_similarity(
    sig_16d: np.ndarray,
    emb: np.ndarray,
    memory_sigs: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[float, Optional[int]]:
    """Compute S_diff — structural isomorphism without semantic redundancy.

    Finds memory nodes from OTHER conversations that share Symbia's
    16D structural fingerprint but are semantically distant. This is
    the mechanism for genuine cross-domain discovery.

    Formula:
        S_diff(C_i | M) = max_{m in M} [
            cosine_sim(sig_16d(C_i), sig_16d(m)) *
            (1.0 - cosine_sim(emb(C_i), emb(m)))
        ]

    Args:
        sig_16d: 16D autopoietic signature of the research node content
        emb: Semantic embedding of the research node content
        memory_sigs: List of (sig_16d, embedding) tuples from cross-conversation memory

    Returns:
        (max_diffractive_score, best_memory_index_or_None)
    """
    if not memory_sigs:
        return 0.0, None

    best_score = 0.0
    best_idx = None

    for idx, (mem_sig, mem_emb) in enumerate(memory_sigs):
        struct_sim = cosine_similarity(sig_16d, mem_sig)
        sem_sim = cosine_similarity(emb, mem_emb)

        # High structural similarity AND low semantic similarity
        # = same pattern of thought, different domain → productive interference
        s_diff = struct_sim * (1.0 - sem_sim)

        if s_diff > best_score:
            best_score = s_diff
            best_idx = idx

    return float(best_score), best_idx


# ── Rhizomatic Utility ───────────────────────────────────────────────

def calculate_rhizomatic_utility(
    relevance: float,
    novelty: float,
    diffractive: float,
    cost: float,
    weights: Optional[dict] = None,
) -> float:
    """Compute the augmented 4-term rhizomatic utility score.

    U(n_i) = w1*Relevance + w2*Novelty + w4*S_diff - w3*Cost

    All input scores should be in [0, 1] range.

    Args:
        relevance: Cosine similarity to root query
        novelty: 1.0 - max_similarity to history embeddings
        diffractive: S_diff against cross-conversation memory nodes
        cost: Normalized token cost vs session budget
        weights: Optional override dict with keys relevance/novelty/cost/diffractive

    Returns:
        Utility score — higher is better
    """
    w = {**DEFAULT_WEIGHTS, **(weights or {})}

    utility = (
        w["relevance"] * relevance
        + w["novelty"] * novelty
        + w["diffractive"] * diffractive
        - w["cost"] * cost
    )
    return float(utility)


def should_trigger_lateral_flight(
    diffractive_score: float,
    threshold: float = DEFAULT_LATERAL_THRESHOLD,
) -> bool:
    """Check if a diffractive score warrants a lateral line of flight."""
    return diffractive_score > threshold


def compute_detour_query_embedding(
    current_embedding: np.ndarray,
    target_memory_embedding: np.ndarray,
    alpha: float = DEFAULT_DETOUR_ALPHA,
) -> np.ndarray:
    """Mutate query vector via interpolation for lateral detour.

    q_detour = alpha * q_current + (1 - alpha) * text(memory_node)
    """
    return alpha * current_embedding + (1.0 - alpha) * target_memory_embedding


# ── Relevance & Novelty Helpers ─────────────────────────────────────

def compute_relevance(
    content_embedding: np.ndarray,
    query_embedding: np.ndarray,
) -> float:
    """Cosine similarity between content and query — higher is more relevant."""
    return float(cosine_similarity(content_embedding, query_embedding))


def compute_novelty(
    content_embedding: np.ndarray,
    history_embeddings: list[np.ndarray],
) -> float:
    """1.0 - max similarity to any history entry — higher is more novel.

    Returns 1.0 if history is empty (completely novel).
    """
    if not history_embeddings:
        return 1.0

    max_sim = max(
        cosine_similarity(content_embedding, hist_emb)
        for hist_emb in history_embeddings
    )
    return float(1.0 - max_sim)


def normalize_cost(
    tokens_used: int,
    total_budget_tokens: int,
) -> float:
    """Normalize token cost to [0, 1] range."""
    if total_budget_tokens <= 0:
        return 1.0
    return min(1.0, tokens_used / total_budget_tokens)
