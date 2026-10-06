"""Acquisition intent and cache access provenance, without content duplication."""

from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from backend.storage.research_receipts import ReceiptModel


class AcquisitionReceipt(ReceiptModel):
    acquisition_id: str
    task_id: str
    action_id: str
    canonical_url: str = Field(max_length=8192)
    config_hash: str
    started_at: AwareDatetime
    completed_at: AwareDatetime | None = None
    outcome: Literal["pending", "fetched", "cache_hit", "unavailable", "failed", "cancelled"] = "pending"
    origin_acquisition_id: str | None = None
    observed_at: AwareDatetime | None = None
    valid_until: AwareDatetime | None = None
    providers: tuple[str, ...] = ()
    origin_providers: tuple[str, ...] = ()
    source_id: str | None = None
    source_version: str | None = None
    error_category: str | None = None

    @model_validator(mode="after")
    def validate_observation(self) -> "AcquisitionReceipt":
        if self.outcome != "pending" and (self.completed_at is None or self.completed_at < self.started_at):
            raise ValueError("Acquisition terminal time must follow intent")
        if (self.source_id is None) != (self.source_version is None):
            raise ValueError("Acquisition source identity requires a version")
        if self.outcome in {"fetched", "cache_hit"} and (
            self.observed_at is None or self.valid_until is None or self.valid_until < self.observed_at
        ):
            raise ValueError("Available acquisition requires observation and reuse expiry")
        if self.outcome == "cache_hit" and (not self.origin_acquisition_id or self.providers):
            raise ValueError("Cache access requires origin and no new provider invocation")
        return self
