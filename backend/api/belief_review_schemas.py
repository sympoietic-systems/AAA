"""Reserved v2 request contracts. No routes installed by this module."""

from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from backend.services.belief_review_contracts import (
    FrozenRecord,
    Identifier,
    ParticipantPosition,
    Reason,
    ReviewState,
    Sha256,
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
