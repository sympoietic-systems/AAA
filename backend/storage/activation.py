"""Pure persistence schema for assembly provenance; no cognitive operator imports."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


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


def serialize_activation_trace(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    return ActivationTrace.model_validate(value).model_dump_json()
