"""Human-reviewable cuts; a proposal cannot authorize child spending."""

from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator

from backend.storage.research_receipts import ReceiptModel


class BranchScope(ReceiptModel):
    scope_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=1000)
    retrieval_vocabulary: tuple[Annotated[str, Field(min_length=1, max_length=200)], ...] = Field(
        min_length=1, max_length=20
    )
    validation_norm: str = Field(min_length=1, max_length=1000)
    attempt_allocation: int = Field(ge=1, le=16)
    budget_allocation_usd: float = Field(ge=0, le=50)

    @model_validator(mode="after")
    def validate_text(self) -> "BranchScope":
        if (
            not self.question.strip()
            or not self.validation_norm.strip()
            or any(not word.strip() for word in self.retrieval_vocabulary)
        ):
            raise ValueError("Scope questions, vocabularies and validation norms cannot be blank")
        return self


class BranchProposalDraft(ReceiptModel):
    question: str = Field(min_length=1, max_length=1000)
    rationale: str = Field(min_length=1, max_length=2000)
    cut_kind: Literal["retrieval_vocabulary", "validation_norm"]
    witness_segment_ids: tuple[Annotated[str, Field(min_length=1, max_length=200)], ...] = Field(
        min_length=2, max_length=20
    )
    scopes: tuple[BranchScope, ...] = Field(min_length=2, max_length=2)
    overlap: str = Field(min_length=1, max_length=1000)
    risk: str = Field(min_length=1, max_length=1000)
    coupled_relational: bool = False
    parent_attempt_reserve: int = Field(default=8, ge=8, le=64)
    parent_budget_reserve_usd: float = Field(ge=0, le=50)

    @model_validator(mode="after")
    def validate_cut(self) -> "BranchProposalDraft":
        first, second = self.scopes
        if self.coupled_relational:
            raise ValueError("Coupled relational questions must remain in the parent line")
        if first.scope_id == second.scope_id or len(set(self.witness_segment_ids)) < 2:
            raise ValueError("A branch cut requires distinct scopes and evidence anchors")
        if self.cut_kind == "retrieval_vocabulary" and set(first.retrieval_vocabulary) == set(
            second.retrieval_vocabulary
        ):
            raise ValueError("Retrieval vocabularies do not differ")
        if (
            self.cut_kind == "validation_norm"
            and first.validation_norm.strip().casefold() == second.validation_norm.strip().casefold()
        ):
            raise ValueError("Validation norms do not differ")
        return self


class BranchProposal(ReceiptModel):
    proposal_id: str
    task_id: str
    action_id: str
    parent_objective: str
    draft: BranchProposalDraft
    created_at: AwareDatetime
    expires_at: AwareDatetime
    resume_phase: str
    status: Literal["pending", "approved", "declined", "expired"] = "pending"
    resolved_at: AwareDatetime | None = None
    reviewed_by: str | None = None
    approved_scopes: tuple[BranchScope, ...] | None = None
    resolution_reason: str | None = Field(default=None, max_length=200)
