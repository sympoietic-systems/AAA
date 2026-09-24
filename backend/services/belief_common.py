import json
import logging
from typing import Any

from backend.modules.structural_engine import CompositeStructuralScorer

logger = logging.getLogger(__name__)

BeliefResult = dict[str, Any]


class BeliefUseCase:
    _state: Any


async def _score_statement_16d(state: Any, statement: str, fallback: str | None = None) -> str:
    """Score a statement as 16D vector and return JSON-serialized v16d dict."""
    try:
        provider = (
            getattr(state, "structural_provider", None)
            or getattr(state, "background_provider", None)
            or getattr(state, "llm_provider", None)
        )
        scorer = CompositeStructuralScorer(llm_provider=provider)
        use_llm = True if provider is not None else None
        v16d = await scorer.score_async(statement, use_llm_scorer=use_llm)
        return json.dumps({"v16d": v16d.tolist() if hasattr(v16d, "tolist") else list(v16d)})
    except Exception as e:
        logger.error("Failed to score statement: %s", e)
        return fallback or "[]"
