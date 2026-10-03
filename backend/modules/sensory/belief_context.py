"""Explicit statement context and fail-closed referent checks; no automatic resolution."""

import hashlib
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

REFERENCE = re.compile(
    r"\b(it|its|they|them|their|this|that|these|those|he|she|his|her|former|latter|here|there|then)\b", re.I
)


class ReferenceBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    start: int = Field(ge=0, le=4000)
    end: int = Field(ge=1, le=4000)
    candidates: tuple[str, ...] = Field(max_length=8)
    role: Literal["referential", "nonreferential"] = "referential"
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)


class ClaimContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    statement_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    scope: str = Field(min_length=1, max_length=500)
    temporal_scope: str = Field(min_length=1, max_length=250)
    provenance: str = Field(min_length=1, max_length=200)
    resolution: Literal["resolved", "unresolved", "ambiguous"]
    bindings: tuple[ReferenceBinding, ...] = Field(default=(), max_length=64)


def context_error(statement: str, context: ClaimContext | None) -> str | None:
    if context is None:
        return "missing_context"
    if context.statement_sha256 != hashlib.sha256(statement.encode()).hexdigest():
        return "stale_context"
    if not all(x.strip() for x in (context.scope, context.temporal_scope, context.provenance)):
        return "missing_context"
    if context.resolution != "resolved":
        return "unresolved_referent"
    detected = {(m.start(), m.end()) for m in REFERENCE.finditer(statement)}
    indexed = {(b.start, b.end): b for b in context.bindings}
    if len(indexed) != len(context.bindings) or set(indexed) != detected:
        return "unresolved_referent"
    for binding in context.bindings:
        if binding.confidence < 0.9:
            return "unresolved_referent"
        if binding.role == "referential":
            if len(binding.candidates) != 1 or not binding.candidates[0].strip() or len(binding.candidates[0]) > 200:
                return "unresolved_referent"
        elif binding.candidates:
            return "unresolved_referent"
    return None
