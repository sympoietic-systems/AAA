"""Vector and signature utilities.

Consolidated from:
- backend/utils/similarity.py (cosine_similarity)
- backend/api/routes/agent.py (_parse_vector_16d, _cosine_sim)
- backend/api/routes/history.py (signature deserialization, HistoryMessage construction)

Provides a single source of truth for 16D structural-vector parsing,
cosine similarity, and signature deserialization.
"""

import json

import numpy as np

from backend.api.schemas import HistoryMessage

# ── Vector parsing ─────────────────────────────────────────────────────


def parse_vector_16d(vector_json: str) -> list[float] | None:
    """Parse a JSON 16D vector string into a list of floats, or None.

    Handles multiple serialization formats:
    - JSON list: [0.1, 0.2, ...]
    - JSON dict with key 'v16d' or 'v384d': {"v16d": [0.1, ...]}
    - Empty string or "[]" → None
    - Invalid JSON → None
    """
    if not vector_json or vector_json == "[]":
        return None
    try:
        data = json.loads(vector_json)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(data, dict):
        for key in ("v16d", "v384d"):
            if key in data and data[key]:
                return [float(x) for x in data[key]]
        return None
    if isinstance(data, list) and len(data) == 16:
        return [float(x) for x in data]
    return None


# ── Cosine similarity ──────────────────────────────────────────────────


def cosine_similarity(
    a: list[float] | np.ndarray,
    b: list[float] | np.ndarray,
) -> float:
    """Cosine similarity between two vectors (list or numpy array).

    Centralized version — replaces both:
    - backend/utils/similarity.py:cosine_similarity (numpy arrays)
    - backend/api/routes/agent.py:_cosine_sim (lists)

    Returns 0.0 if vectors have mismatched shapes or zero norms.
    """
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    if va.shape != vb.shape:
        return 0.0
    na = float(np.linalg.norm(va))
    nb = float(np.linalg.norm(vb))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


# ── Signature deserialization ──────────────────────────────────────────


def deserialize_structural_signature(
    sig_bytes: bytes | None,
) -> list[float] | None:
    """Deserialize a structural_signature blob from the database.

    Replaces the duplicated inline pattern in history.py (lines 24-32 and 95-103)
    and agent.py (recalculate endpoints).
    """
    if not sig_bytes:
        return None
    try:
        arr = np.frombuffer(sig_bytes, dtype=np.float32)
        return arr.tolist()
    except Exception:
        return None


# ── HistoryMessage construction ────────────────────────────────────────


def build_history_message(
    row: dict,
    metrics,
    justification: str | None = None,
) -> HistoryMessage:
    """Build a HistoryMessage from a database row dict.

    Handles structural_signature deserialization and fallback justification.
    Replaces the duplicated construction blocks in history.py.
    """
    from backend.modules.structural_engine import get_justification

    sig_list = deserialize_structural_signature(row.get("structural_signature"))
    if justification is None:
        justification = row.get("structural_justification") or get_justification(row.get("content", ""))

    return HistoryMessage(
        id=row["id"],
        timestamp=row["timestamp"],
        speaker=row["speaker"],
        content=row["content"],
        thinking=None,
        context_sent=None,
        has_context=bool(row.get("has_context")),
        content_tokens=row.get("content_tokens", 0),
        thinking_tokens=row.get("thinking_tokens"),
        metrics=metrics,
        model_used=row.get("model_used"),
        provider_used=row.get("provider_used"),
        structural_signature=sig_list,
        structural_justification=justification,
        parent_message_id=row.get("parent_message_id"),
    )
