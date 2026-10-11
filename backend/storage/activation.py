"""Pure persistence schema for assembly provenance; no cognitive operator imports."""

import json
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class BeliefSelectionReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    record_id: str = Field(min_length=1, max_length=200)
    statement_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    review_state: str = Field(max_length=64)
    scope: str = Field(max_length=500)
    temporal_scope: str = Field(max_length=250)
    standing: str = Field(max_length=64)
    challenges: list[str] = Field(max_length=3)
    dissent: list[str] = Field(max_length=4)
    decision_id: str | None = Field(default=None, max_length=128)
    intended_use: Literal["dormant_inquiry", "scoped_provisional_premise", "question_or_comparison"]
    selection_reason: str = Field(max_length=64)
    selection_policy: Literal["belief-participation-v1"]
    timestamp: AwareDatetime
    scan_truncated: bool
    history_truncated: bool
    counter_trace: dict[str, Any] | None = None
    tool_authority: Literal["none"] = "none"
    independent_warrant_delta: Literal[0] = 0


class ActivationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    kind: Literal["belief", "skill", "external"]
    id: str | None = Field(default=None, max_length=200)
    label: str = Field(default="", max_length=200)
    origin: Literal["attractor", "spectral", "always_active", "on_demand", "file", "web", "resonance", "diffractive"]
    selected: bool = True
    injected: bool


class ActivationTrace(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[1] = 1
    stage: Literal["assembled"] = "assembled"
    coverage: Literal["complete", "partial"]
    prompt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    entries: list[ActivationEntry] = Field(max_length=128)
    selection_receipts: list[BeliefSelectionReceipt] = Field(default_factory=list, max_length=10)


def serialize_activation_trace(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    return ActivationTrace.model_validate_json(json.dumps(value)).model_dump_json()
