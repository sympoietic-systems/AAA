"""Beliefs v2 contracts only: bounded records, advisory relations, no write ports."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from backend.utils.belief_candidate import statement_key

Identifier = Annotated[str, StringConstraints(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_.:-]+$")]
AgentId = Annotated[str, StringConstraints(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
Statement = Annotated[str, StringConstraints(min_length=1, max_length=4000)]
Scope = Annotated[str, StringConstraints(max_length=500)]
TemporalScope = Annotated[str, StringConstraints(max_length=250)]
Reason = Annotated[str, StringConstraints(max_length=2000)]
Confidence = Annotated[float, Field(strict=True, ge=0, le=1)]
ReviewState = Literal["candidate", "awaiting_context", "under_review", "adopted", "deferred", "declined", "superseded"]
Relation = Literal["equivalent", "extension", "contradiction", "distinct", "insufficient_context"]
Origin = Literal[
    "explicit_chat",
    "explicit_dream",
    "passive_chat",
    "passive_dream",
    "passive_research",
    "document",
    "shared_note",
    "web",
    "conversation_pattern",
    "scar_fold",
]
ADAPTER_VERSION: Literal["belief-relation-adapter-v1"] = "belief-relation-adapter-v1"


class FrozenRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    schema_version: Literal[2] = 2

    @field_validator("*", mode="after")
    @classmethod
    def utc_timestamp(cls, value: object) -> object:
        return value.astimezone(UTC) if isinstance(value, datetime) else value


class SourceReference(FrozenRecord):
    source_type: str = Field(min_length=1, max_length=64)
    context_status: Literal["available", "missing", "stale", "ambiguous"]
    activity: Literal["internal", "external", "unknown"] = "unknown"
    source_id: str | None = Field(default=None, min_length=1, max_length=200)
    source_version: str | None = Field(default=None, min_length=1, max_length=200)
    source_sha256: Sha256 | None = None
    source_timestamp: AwareDatetime | None = None
    quote: str = Field(default="", max_length=2000)
    reference: str = Field(default="", max_length=500)
    unavailable_reason: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def binding(self) -> Self:
        if self.context_status == "available":
            if not self.source_id or not self.source_sha256 or not (self.quote.strip() or self.reference.strip()):
                raise ValueError("Available context requires source identity/hash and quote or reference")
        elif not self.unavailable_reason.strip():
            raise ValueError("Unavailable context requires a reason")
        return self


class LineageEntry(FrozenRecord):
    source_id: str = Field(min_length=1, max_length=200)
    source_sha256: Sha256 | None = None
    parent_sources: tuple[Identifier, ...] = Field(default=(), max_length=50)
    independence_status: Literal["independent", "derived", "internal", "unknown"] = "unknown"
    uncertainty: Scope = ""


class Encounter(FrozenRecord):
    id: Identifier
    agent_id: AgentId
    origin: Origin
    segment_id: str = Field(min_length=1, max_length=100)
    received_at: AwareDatetime
    statement: Statement
    statement_sha256: Sha256
    scope: Scope = ""
    temporal_scope: TemporalScope = ""
    source: SourceReference
    lineage: tuple[LineageEntry, ...] = Field(default=(), max_length=50)
    candidate_id: Identifier | None = None
    trigger: Literal["insight", "conflict", "counterexample", "evidence", "unknown"] = "unknown"

    @model_validator(mode="after")
    def internal_warrant(self) -> Self:
        if self.statement_sha256 != hashlib.sha256(self.statement.encode()).hexdigest():
            raise ValueError("Encounter statement hash mismatch")
        if self.source.activity == "internal" and any(
            e.source_id == self.source.source_id and e.independence_status == "independent" for e in self.lineage
        ):
            raise ValueError("Internal activity cannot mint independent warrant")
        return self


class ComparisonSnapshot(FrozenRecord):
    record_id: Identifier
    agent_id: AgentId
    record_kind: Literal["proposal", "belief", "skill_projection"]
    statement: Statement
    statement_sha256: Sha256
    scope: Scope = ""
    temporal_scope: TemporalScope = ""
    review_state: ReviewState | None = None
    review_version: int | None = Field(default=None, ge=0, strict=True)
    legacy_status: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def statement_binding(self) -> Self:
        if self.statement_sha256 != hashlib.sha256(self.statement.encode()).hexdigest():
            raise ValueError("Comparison statement hash mismatch")
        return self


class RelationObservation(FrozenRecord):
    comparison_id: Identifier
    comparison_statement_sha256: Sha256
    relation: Relation
    scope: Scope = ""
    temporal_scope: TemporalScope = ""
    adapter_version: Literal["belief-relation-adapter-v1"] = ADAPTER_VERSION
    raw_relation: str | None = Field(default=None, max_length=64)
    raw_contract: str | None = Field(default=None, max_length=64)
    assessment_confidence: Confidence | None = None
    reason: Scope = ""


class WarrantDimension(FrozenRecord):
    name: str = Field(min_length=1, max_length=64)
    basis: str = Field(default="", max_length=1000)
    source_refs: tuple[Identifier, ...] = Field(default=(), max_length=50)
    independence_status: Literal["independent", "derived", "internal", "unknown"] = "unknown"
    uncertainty: Scope = ""
    challenge: Scope = ""


class Assessment(FrozenRecord):
    id: Identifier
    agent_id: AgentId
    encounter_id: Identifier
    policy_version: Identifier
    rubric_version: Identifier
    context_hash: Sha256
    referent_status: Literal["validated", "missing", "stale", "ambiguous", "unknown"]
    comparison_snapshots: tuple[ComparisonSnapshot, ...] = Field(default=(), max_length=10)
    relations: tuple[RelationObservation, ...] = Field(default=(), max_length=10)
    warrant_dimensions: tuple[WarrantDimension, ...] = Field(default=(), max_length=16)
    consequence_or_tension: str = Field(default="", max_length=1000)
    challenge: str = Field(default="", max_length=1000)
    exclusions: tuple[Scope, ...] = Field(default=(), max_length=20)
    evaluator_status: Literal["pending", "evaluated", "abstained", "unavailable", "stale", "failed"]
    started_at: AwareDatetime
    completed_at: AwareDatetime | None = None
    candidate_id: Identifier | None = None
    previous_assessment_id: Identifier | None = None
    requested_model: str | None = Field(default=None, max_length=200)
    returned_model: str | None = Field(default=None, max_length=200)
    assessment_confidence: Confidence | None = None
    abstain_reason: Scope = ""

    @model_validator(mode="after")
    def snapshot_binding(self) -> Self:
        comparisons = {c.record_id: c for c in self.comparison_snapshots}
        if len(comparisons) != len(self.comparison_snapshots):
            raise ValueError("Duplicate comparison snapshot")
        if any(c.agent_id != self.agent_id for c in self.comparison_snapshots):
            raise ValueError("Comparison belongs to another agent")
        if len({r.comparison_id for r in self.relations}) != len(self.relations):
            raise ValueError("Duplicate relation observation")
        for relation in self.relations:
            comparison = comparisons.get(relation.comparison_id)
            if comparison is None or comparison.statement_sha256 != relation.comparison_statement_sha256:
                raise ValueError("Relation lacks matching comparison snapshot")
            if relation.relation != "insufficient_context" and (
                self.referent_status != "validated"
                or not comparison.scope.strip()
                or not comparison.temporal_scope.strip()
            ):
                raise ValueError("Semantic relation requires validated context and scope/time")
        if self.evaluator_status == "pending":
            if self.completed_at is not None:
                raise ValueError("Pending assessment cannot be completed")
        elif self.completed_at is None or self.completed_at < self.started_at:
            raise ValueError("Completed assessment requires ordered timestamps")
        if self.evaluator_status != "evaluated" and any(r.relation != "insufficient_context" for r in self.relations):
            raise ValueError("Unavailable evaluator cannot establish semantic relations")
        return self


class Actor(FrozenRecord):
    kind: Literal["operator", "system", "agent"]
    principal_id: Identifier
    auth_context_id: Identifier | None = None


class ParticipantPosition(FrozenRecord):
    participant_id: Identifier
    position: Literal["assent", "dissent", "undetermined"]
    attribution: Literal["declared", "interpreted", "unknown"]
    rationale: Reason = ""
    declaration_source_id: Identifier | None = None

    @model_validator(mode="after")
    def declaration(self) -> Self:
        if self.attribution == "declared" and self.declaration_source_id is None:
            raise ValueError("Declared position requires attributable source")
        return self


class ReviewDecision(FrozenRecord):
    id: Identifier
    agent_id: AgentId
    record_id: Identifier
    statement_sha256: Sha256
    actor: Actor
    authority: Literal["operator_review", "intake_bookkeeping"]
    policy_version: Identifier
    expected_review_version: int = Field(ge=0, strict=True)
    previous_state: ReviewState | None
    next_state: ReviewState
    scope: str = Field(min_length=1, max_length=500)
    rationale: str = Field(min_length=1, max_length=2000)
    consequence: str = Field(min_length=1, max_length=1000)
    challenge: str = Field(min_length=1, max_length=1000)
    positions: tuple[ParticipantPosition, ...] = Field(default=(), max_length=20)
    dissent: tuple[Reason, ...] = Field(default=(), max_length=20)
    assessment_ids: tuple[Identifier, ...] = Field(default=(), max_length=50)
    timestamp: AwareDatetime

    @model_validator(mode="after")
    def authority_boundary(self) -> Self:
        if any(not getattr(self, name).strip() for name in ("scope", "rationale", "consequence", "challenge")):
            raise ValueError("Review fields cannot be blank")
        if self.authority == "operator_review":
            if self.actor.kind != "operator" or not self.actor.auth_context_id:
                raise ValueError("Operator review requires server-owned authorization context")
        elif (
            self.actor.kind != "system"
            or self.next_state not in {"candidate", "awaiting_context", "under_review", "deferred"}
            or self.previous_state in {"adopted", "declined", "superseded"}
        ):
            raise ValueError("Intake cannot adopt, decline or supersede a commitment")
        return self


class SkillProjection(FrozenRecord):
    kind: Literal["skill_projection"] = "skill_projection"
    agent_id: AgentId
    belief_id: Identifier
    skill_id: Identifier
    skill_version: int | None = Field(default=None, ge=1, strict=True)
    skill_statement_sha256: Sha256 | None = None
    application_authority: Literal["human_skill_application", "autonomous_skill_application", "legacy_unknown"]
    semantic_adoption_authority: Literal["none"] = "none"
    skill_event_id: Identifier | None = None
    application_actor: Actor | None = None

    @model_validator(mode="after")
    def application_binding(self) -> Self:
        if self.application_authority != "legacy_unknown":
            if (
                self.skill_version is None
                or not self.skill_statement_sha256
                or not self.skill_event_id
                or not self.application_actor
            ):
                raise ValueError("Known skill application requires version/hash/event/actor provenance")
            if self.application_authority == "human_skill_application":
                if self.application_actor.kind != "operator" or not self.application_actor.auth_context_id:
                    raise ValueError("Human skill application requires operator authorization context")
            elif self.application_actor.kind not in ("agent", "system"):
                raise ValueError("Autonomous application requires its actual application actor")
        return self


class LegacyProjection(FrozenRecord):
    legacy_status: str = Field(max_length=64)
    workflow_hint: str = Field(max_length=64)
    review_state: None = None
    decision_id: None = None


class SituatedStanding(FrozenRecord):
    """Participation standing is bound to the actual decision and current statement."""

    kind: Literal["legacy_sediment", "skill_projection", "situated_candidate", "reviewed_commitment"]
    agent_id: AgentId
    record_id: Identifier
    statement_sha256: Sha256
    scope: Scope = ""
    review_state: ReviewState | None = None
    decision: ReviewDecision | None = None
    adoption_decision: ReviewDecision | None = None
    projection: SkillProjection | None = None
    challenges: tuple[Scope, ...] = Field(default=(), max_length=20)
    warrant_dimensions: tuple[WarrantDimension, ...] = Field(default=(), max_length=16)
    permitted_modes: tuple[
        Literal["question", "comparison", "experiment_proposal", "scoped_dissent", "provisional_premise"], ...
    ] = Field(default=(), max_length=5)
    tool_authority: Literal["none"] = "none"

    @model_validator(mode="after")
    def standing_binding(self) -> Self:
        for receipt in (self.decision, self.adoption_decision):
            if receipt is not None and (
                receipt.agent_id != self.agent_id
                or receipt.record_id != self.record_id
                or receipt.statement_sha256 != self.statement_sha256
                or receipt.scope != self.scope
            ):
                raise ValueError("Standing receipt must match agent, record, statement and scope")
        if self.decision is not None and self.review_state != self.decision.next_state:
            raise ValueError("Current standing must match its latest decision")
        if self.kind == "reviewed_commitment":
            if self.review_state not in ("adopted", "superseded") or self.decision is None:
                raise ValueError("Reviewed commitment requires an attributable current decision")
            adoption = self.decision if self.review_state == "adopted" else self.adoption_decision
            if adoption is None or adoption.next_state != "adopted" or adoption.authority != "operator_review":
                raise ValueError("Reviewed commitment requires its adoption receipt")
        elif self.kind == "legacy_sediment":
            if self.review_state is not None or self.decision is not None or self.adoption_decision is not None:
                raise ValueError("Legacy sediment cannot invent reviewed standing")
        elif self.kind == "skill_projection":
            if (
                not self.projection
                or self.projection.agent_id != self.agent_id
                or self.projection.belief_id != self.record_id
            ):
                raise ValueError("Skill standing requires matching projection provenance")
            if self.review_state is not None or self.decision is not None or self.adoption_decision is not None:
                raise ValueError("Skill application cannot transfer semantic adoption")
        elif self.review_state is None or self.review_state == "adopted" or self.adoption_decision is not None:
            raise ValueError("Candidate standing cannot masquerade as adopted")
        return self


def project_legacy(status: str) -> LegacyProjection:
    hints = {
        "pending": "candidate",
        "refined": "reviewed_formulation",
        "rejected": "legacy_rejected",
        "adopted": "legacy_adopted",
    }
    return LegacyProjection(legacy_status=status, workflow_hint=hints.get(status, "legacy_unknown"))


def adapt_relation(contract: str, raw: str, *, context_validated: bool) -> tuple[Relation, str]:
    if not context_validated:
        return "insufficient_context", "unvalidated_context"
    maps: dict[str, dict[str, Relation]] = {
        "admission-v1": {
            "equivalent": "equivalent",
            "extension": "extension",
            "contradiction": "contradiction",
            "independent": "distinct",
            "insufficient": "insufficient_context",
        },
        "triage-v1": {"contradiction": "contradiction", "orthogonal": "distinct", "abstain": "insufficient_context"},
    }
    if contract == "triage-v1" and raw == "endorsement":
        return "insufficient_context", "support_does_not_resolve_equivalence_vs_extension"
    relation = maps.get(contract, {}).get(raw)
    return (relation, "adapted") if relation else ("insufficient_context", "unknown_contract_or_relation")


def encounter_key(encounter: Encounter) -> str | None:
    if not encounter.source.source_id or not encounter.source.source_sha256:
        return None
    values = [
        encounter.agent_id,
        encounter.origin,
        encounter.source.source_type,
        encounter.source.source_id,
        encounter.source.source_version,
        encounter.source.source_sha256,
        encounter.segment_id,
    ]
    return hashlib.sha256(json.dumps(values, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def claim_key(statement: str, scope: str, temporal_scope: str) -> str | None:
    if not scope.strip() or not temporal_scope.strip():
        return None
    values = [statement_key(statement), scope, temporal_scope]
    return hashlib.sha256(json.dumps(values, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


class ReviewLimits(FrozenRecord):
    queue_capacity: int = Field(default=128, ge=1, le=1024, strict=True)
    workers: int = Field(default=2, ge=1, le=4, strict=True)
    lease_seconds: int = Field(default=60, ge=15, le=300, strict=True)
    capacity_wait_seconds: float = Field(default=2, ge=0, le=5)
    evaluator_timeout_seconds: float = Field(default=10, ge=1, le=30)
    comparisons: int = Field(default=10, ge=1, le=10, strict=True)
    adopted_scan: int = Field(default=100, ge=0, le=100, strict=True)
    pending_scan: int = Field(default=64, ge=0, le=64, strict=True)
    deferred_scan: int = Field(default=32, ge=0, le=32, strict=True)
    history_scan: int = Field(default=4, ge=0, le=4, strict=True)
    exploratory_enabled: bool = False
    exploratory_slots: int = Field(default=0, ge=0, le=2, strict=True)

    @model_validator(mode="after")
    def participation(self) -> Self:
        if not self.exploratory_enabled and self.exploratory_slots:
            raise ValueError("Disabled participation requires zero exploratory slots")
        return self


def intake_mode(origin: Origin, *, promoted: bool, enabled: bool) -> str:
    if promoted:
        return "shadow" if enabled else "paused"
    if enabled:
        raise ValueError("Origin promotion must be recorded before enablement")
    return "legacy_admission" if origin in ("explicit_chat", "explicit_dream") else "legacy_unpromoted"
