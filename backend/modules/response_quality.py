"""Response-local quality observation; never edits structural metrics or beliefs."""

from __future__ import annotations

import math
from typing import Any, Protocol

from backend.utils.message_quality import content_hash

SAMPLE_VERSION = "prefix450-tail2500-v1"
MIN_CONFIDENCE = 0.7


class QualityEvaluator(Protocol):
    async def evaluate(self, state: dict[str, Any], questions: dict[str, Any]) -> dict[str, Any]: ...


def quality_sample(text: str) -> str:
    if len(text) <= 3000:
        return text
    return text[:450] + "\n[Middle omitted; ending follows]\n" + text[-2500:]


QUALITY_QUESTION: dict[str, Any] = {
    "type": "choice",
    "instructions": (
        "Assess only the assistant reply's local coherence and responsiveness to current_user_message. "
        "The sample includes the beginning and ending, with the middle omitted when long. "
        "Mark degraded for unmistakable runaway lexical chaining, repeated filler, exposed unfinished "
        "answer-planning instead of an answer, or semantic breakdown. Dense philosophical prose, "
        "unusual vocabulary, disagreement and unconventional style alone are not degradation. "
        "Use uncertain for ambiguous cases. Never infer conversation collapse or belief validity."
    ),
    "criteria": {
        "sound": "Coherent, meaningfully responsive reply.",
        "degraded": "Clear semantic breakdown, runaway chaining, or unfinished planning instead of an answer.",
        "uncertain": "Mixed or insufficient evidence.",
    },
}


async def assess_quality(
    evaluator: QualityEvaluator, text: str, user_text: str, *, reasoning: str | None = None
) -> dict[str, Any]:
    result = await evaluator.evaluate(
        state={"text": quality_sample(text), "char_count": len(text), "current_user_message": user_text[-1500:]},
        questions={"response_quality": QUALITY_QUESTION},
    )
    answer = (result.get("answers") or {}).get("response_quality", {})
    verdict = answer.get("choice")
    raw_confidence = answer.get("confidence")
    confidence = (
        float(raw_confidence)
        if isinstance(raw_confidence, (int, float))
        and not isinstance(raw_confidence, bool)
        and math.isfinite(raw_confidence)
        and 0 <= raw_confidence <= 1
        else None
    )
    available = bool(result.get("success")) and verdict in {"sound", "uncertain", "degraded"}
    status = "uncertain"
    if available and confidence is not None and confidence >= MIN_CONFIDENCE:
        status = verdict
    # Exact duplication identifies missing final content independently of evaluator taste.
    reason = "jev_assessment" if available else "assessment_unavailable"
    if text.strip() and reasoning and text.strip() == reasoning.strip():
        status, reason = "degraded", "reasoning_only"
    elif any(marker in text for marker in ("<|tool_call_begin|>", "<|tool_call_end|>", "<|tool_sep|>")):
        status, reason = "degraded", "provider_control_token_leak"
    return {
        "status": status,
        "verdict": verdict if available else None,
        "confidence": confidence,
        "probabilities": answer.get("probabilities") if available else None,
        "reason": reason,
        "model": result.get("model"),
        "source": "jev",
        "sample_version": SAMPLE_VERSION,
        "content_hash": content_hash(text),
        "excluded_from_context": status == "degraded",
    }
