"""Structural selection and inert framing. Recall grants no warrant or action capability."""

import hashlib
import json
import os
from datetime import UTC, datetime
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.core.logging_config import mask_secrets
from backend.modules.belief_math import parse_vector_16d
from backend.storage.repositories.cognitive.belief_selection import SelectionRecord, SelectionSnapshot
from backend.utils.vector import cosine_similarity


class ParticipationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    enabled: bool = False
    slots: int = Field(default=0, ge=0, le=2)

    @model_validator(mode="after")
    def disabled_budget(self) -> "ParticipationPolicy":
        if not self.enabled and self.slots:
            raise ValueError("Disabled participation requires zero exploratory slots")
        return self


def selection_item(
    record: SelectionRecord,
    slot: int,
    reason: str,
    snapshot: SelectionSnapshot,
    *,
    timestamp: str,
    dormant: bool = False,
) -> dict[str, Any]:
    return {
        "slot": slot,
        "id": record.id,
        "label": record.label,
        "statement": record.statement,
        "confidence": record.confidence,
        "mass": record.ontological_mass,
        "fallback": False,
        "selection_receipt": {
            "record_id": record.id,
            "statement_hash": hashlib.sha256(record.statement.encode()).hexdigest(),
            "review_state": record.review_state,
            "scope": record.scope,
            "temporal_scope": record.temporal_scope,
            "standing": record.standing,
            "challenges": list(record.challenges) or ["unknown / not recorded"],
            "dissent": list(record.dissent),
            "decision_id": record.decision_id,
            "intended_use": "dormant_inquiry"
            if dormant
            else (
                "scoped_provisional_premise" if record.standing == "situated_commitment" else "question_or_comparison"
            ),
            "selection_reason": reason,
            "selection_policy": "belief-participation-v1",
            "timestamp": timestamp,
            "scan_truncated": snapshot.truncated,
            "history_truncated": record.history_truncated,
            "counter_trace": record.counter_trace,
            "tool_authority": "none",
            "independent_warrant_delta": 0,
        },
    }


def exploratory(
    snapshot: SelectionSnapshot, signature: np.ndarray[Any, Any] | None, policy: ParticipationPolicy, *, timestamp: str
) -> list[dict[str, Any]]:
    if not policy.enabled or not policy.slots:
        return []
    pool = [r for r in snapshot.records if r.stratum != "active" and not r.label.startswith("skill:")]

    def similarity(record: SelectionRecord) -> float:
        vector = parse_vector_16d(record.vector_16d)
        if signature is None or len(signature) != 16 or vector is None:
            return 0.0
        value = float(cosine_similarity(signature, vector))
        return value if np.isfinite(value) else 0.0

    # Friction is structural uncertainty/dissent; it makes no semantic conflict verdict.
    pool.sort(key=lambda r: (not bool(r.dissent or r.review_state == "declined"), abs(r.confidence - 0.5), r.id))
    chosen = pool[:1]
    if policy.slots == 2:
        remaining = [r for r in pool if r not in chosen]
        if remaining:
            chosen.append(max(remaining, key=lambda r: (similarity(r), r.id)))
    return [
        selection_item(
            r,
            7 + i,
            "exploratory_friction" if i == 0 else "exploratory_resonance",
            snapshot,
            timestamp=timestamp,
            dormant=r.stratum == "history",
        )
        for i, r in enumerate(chosen)
    ]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def safe_selection_text(value: str) -> str:
    result = mask_secrets(value)
    for key, raw in os.environ.items():
        if key == "AAA_PASSWORD" or key.endswith("API_KEY"):
            for secret in raw.split(","):
                if secret.strip():
                    result = result.replace(secret.strip(), "[REDACTED]")
    return result


def frame_selection(item: dict[str, Any], max_statement: int = 120) -> str:
    receipt = item["selection_receipt"]
    data = {"label": item.get("label", ""), "statement": item["statement"][:max_statement], **receipt}
    # JSON quotes and escaped markup preserve source XML as data, including boundary-looking strings.
    return (
        json.dumps(safe_selection_data(data), ensure_ascii=True)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def safe_selection_data(value: Any) -> Any:
    if isinstance(value, str):
        return safe_selection_text(value)
    if isinstance(value, list):
        return [safe_selection_data(part) for part in value]
    if isinstance(value, dict):
        return {key: safe_selection_data(part) for key, part in value.items()}
    return value
