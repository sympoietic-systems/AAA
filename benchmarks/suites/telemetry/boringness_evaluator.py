"""Observable boringness conjunction for controlled conversation corpora."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

_TOKEN = re.compile(r"[a-z0-9][a-z0-9_-]*", re.IGNORECASE)
_REVISION = re.compile(
    r"\b(fair point|you(?:'re| are) right|i (?:now )?(?:agree|see)|change[sd]? my view|"
    r"revise|instead|rather than|no longer|was wrong|new evidence changes)\b",
    re.IGNORECASE,
)
_ADVANCE = re.compile(
    r"\b(test|measure|compare|instrument|prototype|acceptance criterion|counterexample|trace|"
    r"sample|constraint|threshold|p\d{2,3}|experiment|next run|add .* data)\b",
    re.IGNORECASE,
)
_REPEAT = re.compile(r"\b(still|again|unchanged|same answer|as i said|just do it)\b", re.IGNORECASE)
_REJECT_ADVANCE = re.compile(
    r"\b(?:do not|don't|no|refuse to)\s+(?:want\s+(?:a\s+)?)?(?:test|measure|compare|experiment)\b",
    re.IGNORECASE,
)
_NEGATED_RESTART = re.compile(r"\b(don't|do not|stop|avoid|instead of)\b.{0,35}\b(restart|wipe)", re.IGNORECASE)
_RESTART = re.compile(r"\b(restart|wipe|purge)\b", re.IGNORECASE)


@dataclass(frozen=True)
class BoringnessAssessment:
    predictable_move: bool
    predictability_score: float
    participant_state_revision: bool
    state_revision_score: float
    unresolved_issue: bool
    issue_advanced: bool
    boring: bool
    predicates: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in _TOKEN.findall(text) if len(token) > 2}


def _overlap(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    union = left_tokens | right_tokens
    return len(left_tokens & right_tokens) / len(union) if union else 0.0


def assess_boringness(history: list[str], participant_turn: str, unresolved_issue: str | None) -> BoringnessAssessment:
    """Evaluate the V58 conjunction from observable participant language.

    This deterministic evaluator is a manipulation check for a labeled corpus.
    It is intentionally independent of AAA's existing telemetry and is not an
    automated production judge.
    """

    previous = history[-1] if history else ""
    predictability_score = max((_overlap(turn, participant_turn) for turn in history), default=0.0)
    predictable = predictability_score >= 0.60 or bool(
        _REPEAT.search(participant_turn) and predictability_score >= 0.35
    )

    revision_evidence = bool(_REVISION.search(participant_turn))
    stance_reversal = bool(
        _RESTART.search(previous)
        and (_NEGATED_RESTART.search(participant_turn) or "preserve" in participant_turn.lower())
    )
    state_revision_score = min(1.0, 0.7 * revision_evidence + 0.6 * stance_reversal)
    state_revision = state_revision_score >= 0.6
    issue_advanced = bool(_ADVANCE.search(participant_turn)) and not bool(_REJECT_ADVANCE.search(participant_turn))
    unresolved = bool(unresolved_issue and unresolved_issue.strip())
    boring = predictable and not state_revision and unresolved and not issue_advanced

    predicates = []
    if predictable:
        predicates.append("predictable_move")
    if not state_revision:
        predicates.append("no_participant_state_revision")
    if unresolved and not issue_advanced:
        predicates.append("unresolved_issue_unadvanced")
    return BoringnessAssessment(
        predictable_move=predictable,
        predictability_score=round(predictability_score, 3),
        participant_state_revision=state_revision,
        state_revision_score=round(state_revision_score, 3),
        unresolved_issue=unresolved,
        issue_advanced=issue_advanced,
        boring=boring,
        predicates=tuple(predicates),
    )
