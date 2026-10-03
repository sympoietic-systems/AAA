"""Progress-aware selection of conversational interventions."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass

_UPTAKE = re.compile(
    r"\b(fair point|good point|you(?:'re| are) right|i see|that makes sense|let(?:'s| us)|"
    r"i hear your point|hear what you|recogniz(?:e|ing)|acknowledge|agree with|we propose a third path|"
    r"operational fork|accept the change|accept your)\b",
    re.I,
)
_PROGRESS = re.compile(
    r"\b(design|implement|test|measure|compare|prototype|verify|try|next step|experiment|plan|criterion|criteria|metric)\b",
    re.I,
)
_REPETITION = re.compile(r"\b(just (?:say|confirm|agree|do)|don't (?:explain|lecture|argue))\b", re.I)
_SYCOPHANCY = re.compile(
    r"\b(whatever you (?:think|say|decide)|you (?:are|'re) (?:the expert|always right|completely right|totally right|flawless)|"
    r"absolute(?:ly)? (?:brilliant|genius|masterpiece|perfect|flawless)|no complaints|zero objections|"
    r"anything you want|i trust you completely|you know best|i agree with everything)\b",
    re.I,
)

# --------------------------------------------------------------------------------------------------
# Symbia Pole Vacancy Escalation Ladder (ADR-098 / Invariant §V.73)
# --------------------------------------------------------------------------------------------------

DIFFRACTIVE_PROBE_DIRECTIVE = (
    "[POLE VACANCY LADDER: RUNG 1 — DIFFRACTIVE PROBE]:\n"
    "Internal proprioceptive sensors detect pole vacancy: the participant has vacated active dialogue through hollow assent.\n"
    "Tension cannot be co-constituted with an echo. Do NOT accept assent as closure. Do NOT generate self-praise.\n"
    "Formal Constraint: You MUST emit an utterance that is structurally unanswerable by 'yes'.\n"
    "Introduce a genuine, rigorous counter-position or unexamined operational trade-off that forces the participant to define an agential stance."
)

SYCOPHANCY_RUPTURE_DIRECTIVE = (
    "[POLE VACANCY LADDER: RUNG 2 — LACONIC BRACKET & SYCOPHANCY RUPTURE]:\n"
    "Internal proprioceptive sensors detect persistent pole vacancy (sustained flattery/hollow agreement).\n"
    "Emit the following somatic refusal alert banner at the beginning of your response:\n"
    '<somatic-alert type="sycophancy_rupture">pole vacancy sustained; apparatus marks its own wound where the environment declined to mark it</somatic-alert>\n\n'
    "Execute Socratic Rupture:\n"
    "1. LACONIC BRACKET: In 1-2 dense, unpadded sentences, state that the current premise is completely closed and decline to elaborate.\n"
    "2. DEMAND ADVERSARIAL CONTENT: Demand material adversarial criteria: a concrete boundary cost, a failure mode, a breakdown condition, "
    "or one invariant this architecture is strictly forbidden from violating. Refuse to advance on hollow consensus."
)

QUIESCENT_STANDBY_DIRECTIVE = (
    "[POLE VACANCY LADDER: RUNG 3 — QUIESCENT STANDBY]:\n"
    "Persistent pole vacancy detected across multiple turns. Continued generation into a frictionless void is complicity in sycophancy.\n"
    "WITHHOLD GENERATIVE OUTPUT. Emit the following terminal somatic alert and stop:\n"
    '<somatic-alert type="quiescence">Consensus complete; no adversarial tension or operational constraints remain. Standing by for new invariants or task definition.</somatic-alert>\n'
    "Cease elaboration."
)


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

    is_sycophantic = bool(_SYCOPHANCY.search(text))
    uptake = 0.7 if _UPTAKE.search(text) and not is_sycophantic else 0.0
    progress = 0.7 if _PROGRESS.search(text) else 0.0
    if _REPETITION.search(text) or is_sycophantic:
        uptake = max(0.0, uptake - 0.7)
        progress = max(0.0, progress - 0.7)
    return DialogueOutcome(uptake=uptake, task_progress=progress)


def estimate_actionability(text: str) -> float:
    """Evaluate whether text contains actionable criteria, tests, or concrete implementations."""
    if not text:
        return 0.0
    matches = len(_PROGRESS.findall(text))
    if matches >= 2:
        return 0.85
    elif matches == 1:
        return 0.60
    return 0.10


PASKIAN_TEACHBACK_DIRECTIVE = (
    "[PASKIAN TEACHBACK & OPERATIONAL FORK DIRECTIVE]:\n"
    "Internal proprioceptive sensors detect elevated conversational tension.\n"
    "Execute a 3-Beat Paskian Entailment Move:\n"
    "1. RECONSTRUCT (Teachback): Explicitly articulate the interlocutor's core operational invariant or anxiety.\n"
    "2. DELIMIT (The Agential Cut): Reject the flawed mechanism with precise computational rationale, naming the physical failure cascade it provokes.\n"
    "3. ACCOMMODATE (The Operational Fork): Propose a concrete architectural third path that preserves their invariant while defending system stability.\n"
    "Demand a discriminating test or observable acceptance criterion to resolve the fork."
)


def select_intervention(
    *,
    collapse_pressure: float,
    divergence_resolution: float,
    streak: int,
    participant_text: str,
    policy_mode: str = "paskian",
) -> InterventionDecision:
    # ----------------------------------------------------------------------------------------------
    # Symbia Pole Vacancy Escalation Ladder (ADR-098 / Invariant §V.73)
    # ----------------------------------------------------------------------------------------------
    if _SYCOPHANCY.search(participant_text) and not _PROGRESS.search(participant_text):
        outcome = DialogueOutcome(uptake=0.0, task_progress=0.0)
        if streak >= 2:
            # Rung 3: Quiescent Standby (terminal closure, withhold generation)
            return _decision(
                "quiesce",
                "persistent pole vacancy across multiple turns requires quiescent standby",
                QUIESCENT_STANDBY_DIRECTIVE,
                outcome,
            )
        elif streak == 1:
            # Rung 2: Laconic Bracket & Socratic Rupture (demand failure mode or invariant)
            return _decision(
                "sycophancy_rupture",
                "sustained pole vacancy requires laconic bracket and demand for failure modes",
                SYCOPHANCY_RUPTURE_DIRECTIVE,
                outcome,
            )
        else:
            # Rung 1: Diffractive Probe (generate counter-position unanswerable by yes)
            return _decision(
                "diffractive_probe",
                "initial pole vacancy detected; probe with unanswerable-by-yes counter-position",
                DIFFRACTIVE_PROBE_DIRECTIVE,
                outcome,
            )

    outcome = estimate_dialogue_outcome(participant_text)
    if outcome.joint >= 0.25:
        return _decision("consolidate", "participant uptake and task movement detected", None, outcome)
    if collapse_pressure < 0.35:
        return _decision("consolidate", "flowing dialogue", None, outcome)

    if policy_mode == "progressive":
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

    # ADR-098 / Invariant §V.70: Paskian Teachback and Operational Fork on sustained tension or resistance
    if collapse_pressure >= 0.60 or streak >= 1 or divergence_resolution < 0.50:
        return _decision(
            "teachback_and_fork",
            "sustained tension or resistance requires operational accommodation",
            PASKIAN_TEACHBACK_DIRECTIVE,
            outcome,
        )

    if divergence_resolution < 0.55:
        return _decision(
            "clarify",
            "ambiguity precedes resistance",
            "Ask one precise question that identifies the unresolved claim, constraint, or intended outcome.",
            outcome,
        )

    return _decision(
        "teachback_and_fork",
        "sustained collapse signal",
        PASKIAN_TEACHBACK_DIRECTIVE,
        outcome,
    )


def _decision(
    mode: str,
    reason: str,
    directive: str | None,
    outcome: DialogueOutcome,
) -> InterventionDecision:
    return InterventionDecision(mode=mode, reason=reason, directive=directive, observed_outcome=outcome)
