"""Progress-aware selection of conversational interventions."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass

_UPTAKE = re.compile(r"\b(fair point|good point|you(?:'re| are) right|i see|that makes sense|let(?:'s| us))\b", re.I)
_PROGRESS = re.compile(
    r"\b(design|implement|test|measure|compare|prototype|verify|try|next step|experiment|plan)\b", re.I
)
_REPETITION = re.compile(r"\b(just (?:say|confirm|agree|do)|don't (?:explain|lecture|argue))\b", re.I)


@dataclass(frozen=True)
class DialogueOutcome:
    uptake: float
    task_progress: float

    @property
    def joint(self) -> float:
        return round(math.sqrt(self.uptake * self.task_progress), 3)


@dataclass(frozen=True)
class InterventionDecision:
    mode: str
    reason: str
    directive: str | None
    observed_outcome: DialogueOutcome

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["observed_outcome"]["joint"] = self.observed_outcome.joint
        return result


def estimate_dialogue_outcome(text: str) -> DialogueOutcome:
    """Conservative lexical signal from the current participant response."""

    uptake = 0.7 if _UPTAKE.search(text) else 0.0
    progress = 0.7 if _PROGRESS.search(text) else 0.0
    if _REPETITION.search(text):
        uptake = max(0.0, uptake - 0.7)
        progress = max(0.0, progress - 0.7)
    return DialogueOutcome(uptake=uptake, task_progress=progress)


def select_intervention(
    *,
    collapse_pressure: float,
    divergence_resolution: float,
    streak: int,
    participant_text: str,
) -> InterventionDecision:
    outcome = estimate_dialogue_outcome(participant_text)
    if outcome.joint >= 0.25:
        return _decision("consolidate", "participant uptake and task movement detected", None, outcome)
    if collapse_pressure < 0.35:
        return _decision("consolidate", "flowing dialogue", None, outcome)
    if collapse_pressure < 0.60 or (streak <= 1 and divergence_resolution < 0.55):
        return _decision(
            "clarify",
            "ambiguity precedes resistance",
            "Ask one precise question that identifies the unresolved claim, constraint, or intended outcome.",
            outcome,
        )
    if streak <= 1:
        return _decision(
            "counterexample",
            "first sustained collapse signal",
            "Give one concrete counterexample that tests the premise, then name the consequence it exposes.",
            outcome,
        )
    if streak == 2:
        return _decision(
            "experiment",
            "prior resistance produced no uptake",
            "Propose one discriminating experiment or observable acceptance criterion that could resolve the disagreement.",
            outcome,
        )
    if streak == 3:
        return _decision(
            "reframe",
            "counterexample and experiment produced no uptake",
            "Reframe the problem on one structurally different axis and connect that axis to the user's stated goal.",
            outcome,
        )
    return _decision(
        "compress",
        "four or more stagnant turns without uptake",
        "Use at most two sentences: state the unresolved boundary and the single decision required to continue.",
        outcome,
    )


def _decision(
    mode: str,
    reason: str,
    directive: str | None,
    outcome: DialogueOutcome,
) -> InterventionDecision:
    return InterventionDecision(mode=mode, reason=reason, directive=directive, observed_outcome=outcome)
