"""Calibrated diffractive retrieval activation policy: proposal 3."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActivationDecision:
    score: float
    active: bool
    reason: str


def decide_diffractive_activation(
    *,
    collapse_pressure: float,
    rolling_entropy: float,
    vitality: float,
    streak: int = 0,
    currently_active: bool = False,
) -> ActivationDecision:
    """Proposal 3: pressure with persistence gain and hysteretic release."""

    del rolling_entropy, vitality
    score = min(1.0, collapse_pressure + 0.08 * max(0, streak - 1))
    threshold = 0.55 if currently_active else 0.75
    active = score >= threshold
    return ActivationDecision(round(score, 4), active, "adaptive_persistence")
