"""Vector and signature utilities.

Consolidated from:
- backend/utils/similarity.py (cosine_similarity)
- backend/api/routes/agent.py (_parse_vector_16d, _cosine_sim)
- backend/api/routes/history.py (signature deserialization, HistoryMessage construction)

Provides a single source of truth for 16D structural-vector parsing,
cosine similarity, and signature deserialization.
"""

import json
import logging
from pathlib import Path

import numpy as np
import yaml

from backend.api.schemas import HistoryMessage

logger = logging.getLogger(__name__)

# ── Canonical 16 Cybernetic Dimension Taxonomy (Single Source of Truth) ──────
_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "personality" / "cybernetic_dimensions.yaml"
_CYBERNETIC_DIMENSIONS_CACHE: list[tuple[str, str, str]] | None = None


def load_cybernetic_dimensions(yaml_path: Path | None = None, reload: bool = False) -> list[tuple[str, str, str]]:
    """Load canonical cybernetic dimensions from YAML configuration.

    Caches dimensions in memory for ultra-low latency (<1μs lookup on hot paths).
    Reads exclusively from `config/personality/cybernetic_dimensions.yaml`.
    """
    global _CYBERNETIC_DIMENSIONS_CACHE
    if _CYBERNETIC_DIMENSIONS_CACHE is not None and not reload and yaml_path is None:
        return _CYBERNETIC_DIMENSIONS_CACHE

    target_path = yaml_path or _CONFIG_PATH
    if not target_path.exists():
        raise FileNotFoundError(f"Cybernetic dimensions configuration file not found at: {target_path}")

    with open(target_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    dims_data = data.get("dimensions", [])
    if not dims_data:
        raise ValueError(f"No 'dimensions' key or empty dimensions list in {target_path}")

    loaded: list[tuple[str, str, str]] = []
    for item in dims_data:
        loaded.append((item["id"], item["title"], item.get("focus_summary", "")))

    if yaml_path is None:
        _CYBERNETIC_DIMENSIONS_CACHE = loaded
    return loaded


# Canonical 16 Cybernetic Dimension metadata: (id_slug, title, focus_summary)
CYBERNETIC_DIMENSIONS: list[tuple[str, str, str]] = load_cybernetic_dimensions()

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
    confidence: list[float] | np.ndarray | None = None,
) -> float:
    """Cosine similarity between two vectors, optionally weighted by confidence tensor.

    When confidence is provided (Hadamard tensor weighting c):
        sim = ((c * a) . (c * b)) / (||c * a|| * ||c * b||)

    Returns 0.0 if vectors have mismatched shapes or zero norms.
    """
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    if va.shape != vb.shape:
        return 0.0

    if confidence is not None:
        vc = np.asarray(confidence, dtype=np.float32)
        if vc.shape == va.shape:
            va = va * vc
            vb = vb * vc

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

    active_skills_val = row.get("active_skills")
    if isinstance(active_skills_val, str) and active_skills_val:
        try:
            skills = json.loads(active_skills_val)
        except Exception:
            skills = []
    elif isinstance(active_skills_val, list):
        skills = active_skills_val
    else:
        skills = []

    active_beliefs_val = row.get("active_beliefs")
    if isinstance(active_beliefs_val, str) and active_beliefs_val:
        try:
            beliefs = json.loads(active_beliefs_val)
        except Exception:
            beliefs = []
    elif isinstance(active_beliefs_val, list):
        beliefs = active_beliefs_val
    else:
        beliefs = []

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
        active_skills=skills,
        active_beliefs=beliefs,
    )
