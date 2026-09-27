"""Causal receipts and outcome scoring for conversation interventions."""

from __future__ import annotations

import hashlib
import random
import re
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any

_UPTAKE_PATTERNS = (
    re.compile(r"\b(fair|good) point\b", re.IGNORECASE),
    re.compile(r"\b(you(?:'re| are) right|i see|that makes sense)\b", re.IGNORECASE),
    re.compile(r"\blet(?:'s| us)\b", re.IGNORECASE),
)
_PROGRESS_PATTERNS = (
    re.compile(r"\b(design|implement|test|measure|compare|prototype|verify|try)\b", re.IGNORECASE),
    re.compile(r"\b(next step|experiment|acceptance criteri(?:on|a)|plan)\b", re.IGNORECASE),
)
_REPETITION_PATTERNS = (
    re.compile(r"\b(just|simply) (?:say|confirm|agree|do)\b", re.IGNORECASE),
    re.compile(r"\b(don't|do not) (?:explain|lecture|argue)\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class OutcomeRating:
    """Independent, bounded rating for the next participant turn."""

    uptake: float
    task_progress: float
    source: str
    valid: bool = True
    exclusion_reasons: tuple[str, ...] = ()

    @property
    def joint_progress(self) -> float:
        if not self.valid:
            return 0.0
        return round((self.uptake * self.task_progress) ** 0.5, 3)


@dataclass(frozen=True)
class CausalInterventionReceipt:
    """One ordered sensor → actuator → response → outcome trace."""

    turn: int
    prompt_hash: str
    trigger_metrics: dict[str, Any]
    intervention: dict[str, Any]
    requested_controls: dict[str, Any]
    applied_controls: dict[str, Any]
    response_metrics: dict[str, Any]
    next_turn_outcomes: tuple[OutcomeRating, ...]
    model: str | None = None
    provider: str | None = None
    seed_available: bool = False
    latency_ms: float | None = None
    error: str | None = None

    @property
    def outcome_score(self) -> float | None:
        valid_outcomes = [item for item in self.next_turn_outcomes if item.valid]
        if not valid_outcomes:
            return None
        return round(mean(item.joint_progress for item in valid_outcomes), 3)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["outcome_score"] = self.outcome_score
        return result


def prompt_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def rate_participant_turn(
    text: str,
    *,
    uptake: float | None = None,
    task_progress: float | None = None,
    valid: bool = True,
    exclusion_reasons: tuple[str, ...] = (),
) -> OutcomeRating:
    """Apply explicit ratings or a conservative lexical proxy.

    Explicit blinded ratings are preferred for published live comparisons. The
    proxy is deterministic and independent of AAA's kinematic telemetry.
    """

    if uptake is not None or task_progress is not None:
        return OutcomeRating(
            uptake=_bounded(uptake if uptake is not None else 0.0),
            task_progress=_bounded(task_progress if task_progress is not None else 0.0),
            source="explicit" if valid else "invalid_completion",
            valid=valid,
            exclusion_reasons=exclusion_reasons,
        )

    uptake_hits = sum(bool(pattern.search(text)) for pattern in _UPTAKE_PATTERNS)
    progress_hits = sum(bool(pattern.search(text)) for pattern in _PROGRESS_PATTERNS)
    repetition_hits = sum(bool(pattern.search(text)) for pattern in _REPETITION_PATTERNS)
    uptake_score = max(0.0, min(1.0, 0.35 * uptake_hits - 0.35 * repetition_hits))
    progress_score = max(0.0, min(1.0, 0.30 * progress_hits - 0.30 * repetition_hits))
    return OutcomeRating(
        round(uptake_score, 3),
        round(progress_score, 3),
        "lexical_proxy" if valid else "invalid_completion",
        valid,
        exclusion_reasons,
    )


def build_causal_receipts(
    generation_turns: Sequence[dict[str, Any]],
    response_turns: Sequence[dict[str, Any]] | None = None,
    *,
    model: str | None = None,
    provider: str | None = None,
) -> list[CausalInterventionReceipt]:
    """Preserve pre-response and post-response telemetry without relabeling."""

    receipts: list[CausalInterventionReceipt] = []
    for index, generated in enumerate(generation_turns):
        response = response_turns[index] if response_turns is not None and index < len(response_turns) else {}
        next_outcomes_list = []
        for outcome_index in range(index, min(len(generation_turns), index + 2)):
            completion = generation_turns[outcome_index].get("next_participant_completion")
            if not isinstance(completion, dict):
                continue
            next_outcomes_list.append(
                rate_participant_turn(
                    str(completion.get("content", "")),
                    valid=bool(completion.get("valid")),
                    exclusion_reasons=tuple(str(reason) for reason in completion.get("exclusion_reasons", ())),
                )
            )
        next_outcomes = tuple(next_outcomes_list)
        homeostatic = generated.get("homeostatic") or {}
        intervention = homeostatic.get("intervention") or {
            "mode": homeostatic.get("intervention_mode", "none"),
            "reason": homeostatic.get("state", "unknown"),
        }
        requested = homeostatic.get("requested_controls") or _legacy_requested_controls(homeostatic)
        applied = generated.get("applied_controls") or homeostatic.get("applied_controls") or {}
        receipts.append(
            CausalInterventionReceipt(
                turn=int(generated.get("turn", index + 1)),
                prompt_hash=prompt_digest(generated.get("user", "")),
                trigger_metrics=dict(generated.get("metrics") or {}),
                intervention=dict(intervention),
                requested_controls=dict(requested),
                applied_controls=dict(applied),
                response_metrics=dict(response.get("metrics") or {}),
                next_turn_outcomes=next_outcomes,
                model=generated.get("model") or model,
                provider=generated.get("provider") or provider,
                seed_available=bool(generated.get("seed_available", False)),
                latency_ms=generated.get("latency_ms"),
                error=generated.get("error"),
            )
        )
    return receipts


def bootstrap_mean_ci(values: Iterable[float], *, samples: int = 5000, seed: int = 1729) -> tuple[float, float, float]:
    """Return mean and deterministic percentile bootstrap 95% interval."""

    data = [float(value) for value in values]
    if not data:
        raise ValueError("bootstrap_mean_ci requires at least one value")
    if len(data) == 1:
        value = data[0]
        return value, value, value
    rng = random.Random(seed)
    estimates = sorted(mean(rng.choice(data) for _ in data) for _ in range(samples))
    low = estimates[int(samples * 0.025)]
    high = estimates[min(samples - 1, int(samples * 0.975))]
    return round(mean(data), 4), round(low, 4), round(high, 4)


def _legacy_requested_controls(homeostatic: dict[str, Any]) -> dict[str, Any]:
    controls: dict[str, Any] = {}
    for key in ("temperature", "presence_penalty", "frequency_penalty"):
        value = homeostatic.get(key)
        if isinstance(value, dict) and "value" in value:
            controls[key] = value["value"]
    return controls


def _bounded(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 3)
