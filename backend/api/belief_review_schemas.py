"""Frozen v2 request contracts and bounded export response projections."""

from typing import Any, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from backend.modules.sensory.belief_context import ClaimContext
from backend.services.belief_review_contracts import (
    AgentId,
    FrozenRecord,
    Identifier,
    ParticipantPosition,
    Reason,
    ReviewState,
    Sha256,
    TeachbackFork,
    WorkshopRelation,
)


class ReviewDecisionRequest(FrozenRecord):
    action: Literal[
        "adopt", "decline", "defer", "request_context", "request_review", "revise", "merge", "supersede", "resurface"
    ]
    expected_review_version: int = Field(ge=0, strict=True)
    expected_statement_sha256: Sha256
    expected_state: ReviewState | None
    scope: str = Field(min_length=1, max_length=500)
    rationale: str = Field(min_length=1, max_length=2000)
    consequence: str = Field(min_length=1, max_length=1000)
    challenge: str = Field(min_length=1, max_length=1000)
    dissent: tuple[Reason, ...] = Field(default=(), max_length=20)
    positions: tuple[ParticipantPosition, ...] = Field(default=(), max_length=20)
    target_record_id: Identifier | None = None
    expected_target_review_version: int | None = Field(default=None, ge=0, strict=True)
    expected_target_statement_sha256: Sha256 | None = None
    statement: str | None = Field(default=None, min_length=1, max_length=4000)
    temporal_scope: str = Field(default="", max_length=250)
    assessment_ids: tuple[Identifier, ...] = Field(default=(), max_length=50)
    relations: tuple[WorkshopRelation, ...] = Field(default=(), max_length=10)
    teachback: TeachbackFork | None = None
    context: ClaimContext | None = None

    @model_validator(mode="after")
    def target(self) -> Self:
        if any(not getattr(self, name).strip() for name in ("scope", "rationale", "consequence", "challenge")):
            raise ValueError("Review fields cannot be blank")
        if self.action in ("merge", "supersede") and (
            not self.target_record_id
            or self.expected_target_review_version is None
            or self.expected_target_statement_sha256 is None
        ):
            raise ValueError("Merge/supersession requires target identity, expected review version and statement hash")
        if self.action == "revise" and not self.statement:
            raise ValueError("Revision requires a statement")
        return self


class ReviewExportQuery(FrozenRecord):
    from_time: AwareDatetime
    to_time: AwareDatetime
    limit: int = Field(default=25, ge=1, le=50, strict=True)
    cursor: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def interval(self) -> Self:
        if self.to_time <= self.from_time:
            raise ValueError("Export requires a nonempty half-open interval")
        return self


class ExportReasoning(BaseModel):
    model_config = ConfigDict(extra="forbid")
    encounter: dict[str, Any] | None
    claim_or_tension: dict[str, Any] | None
    comparison: dict[str, Any] | list[dict[str, Any]] | None
    consequence_or_challenge: dict[str, Any] | None
    decision_or_uncertainty: dict[str, Any] | None


class ExportItem(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    export_id: str
    id: str
    timestamp: AwareDatetime | None
    kind: Literal["encounter", "assessment", "legacy_assessment", "decision", "event", "legacy_event"]
    record: dict[str, Any]
    source_accounting: dict[str, Any] | None
    reasoning: ExportReasoning
    reasoning_sources: list[dict[str, Any]] = Field(max_length=11)
    unknown_reasoning_fields: list[str] = Field(max_length=5)
    comparison_truncated: bool
    tool_authority: Literal["none"]
    content_redacted: bool
    completion_index_origin: Literal["existing_receipt", "forward_completion"] | None = None


class ExportPage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_id: AgentId
    resource: Literal["encounters", "assessments", "decisions", "events"]
    from_time: AwareDatetime = Field(alias="from")
    to_time: AwareDatetime = Field(alias="to")
    limit: int = Field(ge=1, le=50)
    items: list[ExportItem] = Field(max_length=50)
    next_cursor: str | None = Field(max_length=2048)
    snapshot: dict[str, str | int]
    interval_complete: bool
    coverage: Literal["stored_dated_rows_at_snapshot"]
    undated_rows: int = Field(ge=0)
    assessment_coverage: Literal["completed_receipts_only"]
    tool_authority: Literal["none"]
