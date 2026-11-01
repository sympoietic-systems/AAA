"""Versioned research records. Provenance does not establish semantic support."""

from datetime import datetime
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class ReceiptModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class ProviderAttemptReceipt(ReceiptModel):
    attempt_id: str | None = None
    task_id: str
    action_id: str
    request_id: str
    provider_request_id: str | None = None
    provider: str
    model: str
    attempt_number: int = Field(ge=1)
    started_at: AwareDatetime
    completed_at: AwareDatetime | None = None
    outcome: Literal["pending", "complete", "partial", "failed", "cancelled"] = "pending"
    finish_reason: str | None = None
    truncated: bool | None = None
    cancelled: bool | None = None
    error_category: str | None = None
    usage: dict[str, int] | None = None
    known_cost_usd: float | None = Field(default=None, ge=0)
    budget_reserved_usd: float | None = Field(default=None, ge=0)
    elapsed_seconds: float | None = Field(default=None, ge=0)


class EvidencePacket(ReceiptModel):
    source_id: str
    source_version: str
    raw_span_locator: str | None = None
    representation: str | None = None
    representation_span_locators: tuple[str, ...] = Field(default=(), max_length=1000)
    acquisition_id: str | None = None
    observed_at: AwareDatetime | None = None
    accessed_at: AwareDatetime | None = None
    valid_until: AwareDatetime | None = None
    cache_hit: bool | None = None
    claim_ids: tuple[str, ...] = ()
    covered_rubric_ids: tuple[str, ...] = ()
    supporting_segment_ids: tuple[str, ...] = ()
    contrary_segment_ids: tuple[str, ...] = ()
    extraction_method: str | None = None
    extraction_quality: float | None = Field(default=None, ge=0, le=1)
    excluded_evidence: dict[str, str] = Field(default_factory=dict)
    unavailable_evidence: dict[str, str] = Field(default_factory=dict)
    unresolved_gaps: tuple[str, ...] = ()
    interpretation: str | None = None


ActionStatus = Literal["pending", "running", "complete", "partial", "failed", "cancelled"]


class ActionObservation(ReceiptModel):
    """Executor-observed delivery; absent telemetry remains unknown."""

    output_refs: tuple[str, ...] = ()
    provider_attempts: tuple[ProviderAttemptReceipt, ...] = ()
    evidence_packets: tuple[EvidencePacket, ...] = ()
    acquisition_ids: tuple[str, ...] = Field(default=(), max_length=256)
    phase_elapsed_seconds: float | None = Field(default=None, ge=0)
    scheduler_decision: dict[str, Any] | None = None
    branch_proposal_id: str | None = Field(default=None, max_length=100)
    child_task_ids: tuple[str, ...] = Field(default=(), max_length=2)
    child_packet_hashes: dict[str, str] = Field(default_factory=dict, max_length=2)


class ResearchActionReceipt(ReceiptModel):
    schema_version: Literal[1] = 1
    action_id: str
    task_id: str
    kind: str
    intent: str
    input_version: str
    dependency_ids: tuple[str, ...] = ()
    rationale: str
    budget_reserved: float = Field(ge=0)
    deadline: AwareDatetime | None = None
    contract_hash: str
    policy_hash: str
    status: ActionStatus = "pending"
    started_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None
    observation: ActionObservation | None = None

    def request_json(self) -> str:
        return self.model_dump_json(exclude={"status", "started_at", "completed_at", "observation"})

    def transition(
        self, status: ActionStatus, at: datetime, observation: ActionObservation | None = None
    ) -> "ResearchActionReceipt":
        return ResearchActionReceipt.model_validate(
            {
                **self.model_dump(),
                "status": status,
                "started_at": at if status == "running" else self.started_at,
                "completed_at": None if status == "running" else at,
                "observation": observation,
            }
        )
