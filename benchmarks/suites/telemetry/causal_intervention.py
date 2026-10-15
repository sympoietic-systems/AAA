"""Deterministic, process-local harness for T37 causal selector arms.

This module is experimental benchmark code. It is not connected to production
conversation routing or persistent storage.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

Arm = Literal["current", "sham", "active"]


class Mode(StrEnum):
    CLARIFY = "clarify"
    COUNTEREXAMPLE = "counterexample"
    EXPERIMENT = "experiment"
    REFRAME = "reframe"
    CONSOLIDATE = "consolidate"
    COMPRESS = "compress"
    ABSTAIN = "abstain"


@dataclass(frozen=True)
class IssueState:
    """Bounded issue tracker; payload is an opaque digest, never transcript text."""

    issue_id: str
    status: Literal["open", "advanced", "resolved", "dissolved"] = "open"
    version: int = 0
    digest: str = ""
    last_transition_turn: int = 0


@dataclass(frozen=True)
class Signals:
    signals_complete: bool = True
    pressure: bool = False
    context_over_budget: bool = False
    resolved_subclaims: int = 0
    has_new_subclaim: bool = False
    participant_revised: bool = False
    issue_advanced: bool = False
    boring_previous: bool = False
    boring_streak: int = 0
    predicted_mode: Mode = Mode.CLARIFY
    term_ambiguity: bool = False
    claim_stable: bool = False
    falsifiable: bool = False
    live_hypotheses: int = 0
    experiment_within_budget: bool = False
    terms_clear: bool = False


@dataclass(frozen=True)
class Selection:
    mode: Mode
    predicate_id: str
    move_class: Literal["argumentation", "method", "transcript", "non_move"]


@dataclass
class ConversationTrial:
    conversation_id: str
    arm: Arm
    max_turns: int = 32
    turn: int = 0
    issue: IssueState | None = None
    carried_memory: tuple[str, int] | None = None
    prior_mode: Mode | None = None
    prior_outcome: dict[str, bool] = field(default_factory=dict)
    mode_counts: Counter[str] = field(default_factory=Counter)
    active: bool = True

    def start_issue(self, issue_id: str, payload: str) -> None:
        if not self.active:
            raise RuntimeError("conversation trial is terminal")
        if not issue_id or len(issue_id) > 100:
            raise ValueError("issue_id must contain 1..100 characters")
        if len(payload) > 8192:
            raise ValueError("issue payload must not exceed 8192 characters")
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        self.issue = IssueState(issue_id=issue_id, digest=digest, last_transition_turn=self.turn)

    def select(self, signals: Signals) -> dict[str, object]:
        if not self.active:
            raise RuntimeError("conversation trial is terminal")
        if self.turn >= self.max_turns:
            self.close("turn_limit")
            raise RuntimeError("conversation trial reached its turn limit")

        self.turn += 1
        # Same writer and timing in SHAM and ACTIVE. CURRENT has no memory store.
        memory_written = self.arm in {"sham", "active"} and self.issue is not None
        if memory_written and self.issue is not None:
            self.carried_memory = (self.issue.digest, self.turn)

        # Structural gate: only the active proposer receives carried memory.
        memory_for_proposer = self.carried_memory if self.arm == "active" else None
        selection = _propose(signals, memory_for_proposer)
        self.mode_counts[selection.mode.value] += 1
        issue_version = self.issue.version if self.issue else None
        issue_digest = self.issue.digest if self.issue else None
        receipt: dict[str, object] = {
            "schema_version": 1,
            "conversation_id": self.conversation_id,
            "arm": self.arm,
            "turn": self.turn,
            "issue_version": issue_version,
            "issue_digest": issue_digest,
            "prior_mode": self.prior_mode.value if self.prior_mode else None,
            "prior_outcome": dict(self.prior_outcome),
            "mode": selection.mode.value,
            "move_class": selection.move_class,
            "predicate_id": selection.predicate_id,
            "predicted_mode": signals.predicted_mode.value,
            "predicted": selection.mode == signals.predicted_mode,
            "participant_state_revision": signals.participant_revised,
            "issue_advanced": signals.issue_advanced,
            "boring": (
                selection.mode == signals.predicted_mode
                and not signals.participant_revised
                and self.issue is not None
                and not signals.issue_advanced
            ),
            "memory_written": memory_written,
            "memory_read": memory_for_proposer is not None,
            "memory_written_turn": self.carried_memory[1] if memory_written and self.carried_memory else None,
            "coverage": dict(sorted(self.mode_counts.items())),
        }
        self.prior_mode = selection.mode
        self.prior_outcome = {
            "participant_state_revision": signals.participant_revised,
            "issue_advanced": signals.issue_advanced,
        }
        if self.issue is not None and signals.issue_advanced:
            self.issue = IssueState(
                issue_id=self.issue.issue_id,
                status="advanced",
                version=self.issue.version + 1,
                digest=self.issue.digest,
                last_transition_turn=self.turn,
            )
        return receipt

    def close(self, reason: Literal["resolved", "dissolved", "turn_limit", "cancelled"]) -> None:
        self.active = False
        self.carried_memory = None
        if self.issue is not None:
            self.issue = IssueState(
                issue_id=self.issue.issue_id,
                status="resolved" if reason == "resolved" else "dissolved",
                version=self.issue.version,
                digest=self.issue.digest,
                last_transition_turn=self.turn,
            )


def _propose(signals: Signals, memory: tuple[str, int] | None) -> Selection:
    """Ordered, auditable predicates. Memory can affect only the active arm."""
    if not signals.signals_complete:
        return Selection(Mode.ABSTAIN, "P-DEGRADED", "non_move")
    if signals.boring_previous:
        if signals.boring_streak < 2:
            return Selection(Mode.ABSTAIN, "P-BORING", "non_move")
        escape = {
            Mode.CLARIFY: Mode.COMPRESS,
            Mode.COMPRESS: Mode.CLARIFY,
            Mode.COUNTEREXAMPLE: Mode.CONSOLIDATE,
            Mode.CONSOLIDATE: Mode.COUNTEREXAMPLE,
            Mode.EXPERIMENT: Mode.REFRAME,
            Mode.REFRAME: Mode.EXPERIMENT,
            Mode.ABSTAIN: Mode.COUNTEREXAMPLE,
        }.get(signals.predicted_mode, Mode.COUNTEREXAMPLE)
        return Selection(
            escape, "P-BORING-ESCAPE", "transcript" if escape in {Mode.COMPRESS, Mode.CONSOLIDATE} else "argumentation"
        )
    if signals.pressure or signals.context_over_budget:
        return Selection(Mode.COMPRESS, "P-PRESSURE", "transcript")
    if signals.resolved_subclaims > 0 and not signals.has_new_subclaim and signals.participant_revised:
        return Selection(Mode.CONSOLIDATE, "P-SATURATION", "transcript")
    if signals.term_ambiguity:
        return Selection(Mode.CLARIFY, "P-UNBOUND", "argumentation")
    if signals.claim_stable and signals.falsifiable and signals.participant_revised and not signals.issue_advanced:
        return Selection(Mode.COUNTEREXAMPLE, "P-FALSIFY", "argumentation")
    if signals.live_hypotheses >= 2 and signals.experiment_within_budget:
        return Selection(Mode.EXPERIMENT, "P-DISCRIMEN", "method")
    stalled = not signals.participant_revised and not signals.issue_advanced
    # Active memory read changes only the active proposer. It carries no text.
    if memory is not None and stalled:
        mode = Mode.COUNTEREXAMPLE if signals.falsifiable else Mode.REFRAME
        return Selection(mode, "P-CARRIED-ISSUE", "argumentation")
    if stalled and not signals.boring_previous and signals.terms_clear:
        return Selection(Mode.REFRAME, "P-BLOCKED", "argumentation")
    return Selection(Mode.ABSTAIN, "P-DEFAULT", "non_move")


def new_trial(conversation_id: str, arm: Arm, *, max_turns: int = 32) -> ConversationTrial:
    if not conversation_id or len(conversation_id) > 100:
        raise ValueError("conversation_id must contain 1..100 characters")
    if arm not in {"current", "sham", "active"}:
        raise ValueError("arm must be current, sham, or active")
    if not 1 <= max_turns <= 128:
        raise ValueError("max_turns must be in [1, 128]")
    return ConversationTrial(conversation_id=conversation_id, arm=arm, max_turns=max_turns)


def mode_reachability_fixtures() -> dict[Mode, Signals]:
    """One deterministic, satisfiable selector fixture per mode."""
    return {
        Mode.ABSTAIN: Signals(signals_complete=False),
        Mode.COMPRESS: Signals(pressure=True),
        Mode.CONSOLIDATE: Signals(resolved_subclaims=1, participant_revised=True),
        Mode.CLARIFY: Signals(term_ambiguity=True),
        Mode.COUNTEREXAMPLE: Signals(claim_stable=True, falsifiable=True, participant_revised=True),
        Mode.EXPERIMENT: Signals(live_hypotheses=2, experiment_within_budget=True),
        Mode.REFRAME: Signals(terms_clear=True),
    }


def receipt_json(receipt: dict[str, object]) -> str:
    """Stable serialization helper used by the offline benchmark runner."""
    return json.dumps(receipt, sort_keys=True, separators=(",", ":"))
