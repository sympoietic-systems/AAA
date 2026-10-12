"""Read-only export cursors and attributed reasoning; no adoption or evaluator ports."""

import asyncio
import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, ValidationError

from backend.core.logging_config import mask_secrets
from backend.errors import GlitchError, SecurityViolation, ValidationGlitch
from backend.services.belief_review_contracts import FrozenRecord, Sha256
from backend.services.belief_review_store import _agent, _identifier
from backend.storage.repositories.cognitive.belief_export import RESOURCES, BeliefExportRepository, utc

PAGE_SECONDS = 10.0


def _budget(deadline: float) -> None:
    if time.monotonic() >= deadline:
        raise GlitchError(
            "Export projection budget exceeded; reduce limit",
            status_code=503,
            kind="resource_exhausted",
            entity="belief_export",
        )


class ExportSnapshot(FrozenRecord):
    database_id: str = Field(min_length=36, max_length=36)
    legacy_generation: int = Field(ge=0, strict=True)
    encounter: int = Field(ge=0, strict=True)
    assessment: int = Field(ge=0, strict=True)
    decision: int = Field(ge=0, strict=True)
    event: int = Field(ge=0, strict=True)
    legacy_event: int = Field(ge=0, strict=True)


class ExportCursor(FrozenRecord):
    binding: Sha256
    snapshot: ExportSnapshot
    last_time: str = Field(min_length=32, max_length=32)
    last_id: str = Field(min_length=1, max_length=180)


def scrub(value: Any) -> Any:
    """Legacy content can predate binding-time secret rejection; mask without rewriting storage."""
    if isinstance(value, str):
        result = mask_secrets(value)
        for key, raw in os.environ.items():
            if key == "AAA_PASSWORD" or key.endswith("API_KEY"):
                for secret in raw.split(","):
                    secret = secret.strip()
                    if secret:
                        result = result.replace(secret, "[REDACTED]")
        return result
    if isinstance(value, dict):
        return {scrub(k): scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(part) for part in value]
    return value


class BeliefExport:
    def __init__(self, db_path: str | object, signing_secret: str):
        if not signing_secret:
            raise SecurityViolation("Belief export requires configured authentication", entity="belief_export")
        self.repository = BeliefExportRepository(db_path)
        self.key = hmac.digest(signing_secret.encode(), b"aaa:belief-export:v1", "sha256")

    def _encode(self, value: ExportCursor) -> str:
        body = value.model_dump_json().encode()
        return base64.urlsafe_b64encode(body + hmac.digest(self.key, body, "sha256")).decode().rstrip("=")

    def _decode(self, token: str, binding: str) -> ExportCursor:
        try:
            if not token or len(token) > 2048:
                raise ValueError("Cursor size")
            raw = base64.b64decode(token + "=" * (-len(token) % 4), altchars=b"-_", validate=True)
            body, signature = raw[:-32], raw[-32:]
            if not hmac.compare_digest(signature, hmac.digest(self.key, body, "sha256")):
                raise ValueError("Cursor signature")
            value = ExportCursor.model_validate_json(body)
            if value.binding != binding or utc(value.last_time) != value.last_time:
                raise ValueError("Cursor binding")
            return value
        except (ValueError, ValidationError) as error:
            raise ValidationGlitch("Invalid or mismatched export cursor", entity="belief_export") from error

    def _projection(self, agent: str, item: dict[str, Any], deadline: float) -> dict[str, Any]:
        _budget(deadline)
        record = item["record"]
        kind = item["kind"]
        encounter: dict[str, Any] | None = record if kind == "encounter" else None
        linked: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        if kind in ("assessment", "event") and record.get("encounter_id"):
            parent = self.repository.detail(agent, "encounters", str(record["encounter_id"]))
            encounter = parent["record"]
            linked.append({"id": parent["id"], "kind": parent["kind"], "timestamp": parent["timestamp"]})
        comparisons: dict[str, Any] | list[dict[str, Any]] | None = None
        truncated = False
        if kind == "assessment":
            comparisons = {
                "snapshots": record.get("comparison_snapshots", []),
                "relations": record.get("relations", []),
            }
        elif kind == "decision":
            ids = record.get("assessment_ids", [])
            assessments = []
            encounters: dict[str, dict[str, Any]] = {}
            for identity in ids[:10]:
                _budget(deadline)
                receipt = self.repository.detail(agent, "assessments", str(identity))
                encounter_id = receipt["record"].get("encounter_id")
                if encounter_id and encounter_id not in encounters:
                    encounters[str(encounter_id)] = self.repository.detail(agent, "encounters", str(encounter_id))[
                        "record"
                    ]
                assessments.append(
                    {
                        "id": receipt["id"],
                        "comparison_snapshots": receipt["record"].get("comparison_snapshots", []),
                        "relations": receipt["record"].get("relations", []),
                    }
                )
                linked.append({"id": receipt["id"], "kind": receipt["kind"], "timestamp": receipt["timestamp"]})
            comparisons = assessments or None
            truncated = len(ids) > 10
            if encounters:
                encounter = {"linked_encounters": list(encounters.values()), "truncated": truncated}
                for encounter_id in encounters:
                    _budget(deadline)
                    observed = self.repository.source_accounting(agent, encounter_id)
                    if observed:
                        observations.append(observed)
        if encounter and kind != "decision" and encounter.get("id"):
            _budget(deadline)
            observed = self.repository.source_accounting(agent, str(encounter["id"]))
            if observed:
                observations.append(observed)
        claim = None
        if encounter and kind != "decision":
            claim = {
                k: encounter.get(k) for k in ("statement", "statement_sha256", "scope", "temporal_scope", "trigger")
            }
        elif kind == "decision":
            claim = {"statement_sha256": record.get("statement_sha256"), "scope": record.get("scope")}
        consequence = None
        if kind in ("assessment", "decision"):
            consequence = {
                "consequence": record.get("consequence_or_tension", record.get("consequence")),
                "challenge": record.get("challenge"),
            }
        uncertainty = None
        if kind == "assessment":
            uncertainty = {
                k: record.get(k)
                for k in ("evaluator_status", "abstain_reason", "assessment_confidence", "evaluation_diagnostics")
            }
        elif kind == "decision":
            uncertainty = {
                k: record.get(k) for k in ("actor", "authority", "next_state", "rationale", "dissent", "positions")
            }
        elif kind == "event":
            uncertainty = {"independent_warrant": record.get("independent_warrant")}
        if kind == "legacy_assessment":
            encounter = record.get("source")
            claim = {k: record.get(k) for k in ("statement", "scope", "temporal_scope", "trigger")}
            comparisons = record.get("comparisons")
            consequence = {"consequence": record.get("consequence")} if record.get("consequence") else None
            uncertainty = {k: record.get(k) for k in ("recommendation", "reason", "evaluation")}
            uncertainty["legacy_advisory_decision"] = record.get("decision")
        reasoning = {
            "encounter": encounter,
            "claim_or_tension": claim,
            "comparison": comparisons,
            "consequence_or_challenge": consequence,
            "decision_or_uncertainty": uncertainty,
        }
        projected = item | {
            "source_accounting": {"observations": observations, "truncated": truncated} if observations else None,
            "reasoning": reasoning,
            "reasoning_sources": [{"id": item["id"], "kind": kind, "timestamp": item["timestamp"]}, *linked],
            "unknown_reasoning_fields": [key for key, value in reasoning.items() if value is None],
            "comparison_truncated": truncated,
            "tool_authority": "none",
        }
        safe = scrub(projected)
        _budget(deadline)
        safe["content_redacted"] = safe != projected
        return dict(safe)

    async def page(
        self, agent: str, resource: str, start: datetime, end: datetime, limit: int = 25, cursor: str | None = None
    ) -> dict[str, Any]:
        return await asyncio.to_thread(self._page, agent, resource, start, end, limit, cursor)

    def _page(
        self, agent: str, resource: str, start: datetime, end: datetime, limit: int, cursor: str | None
    ) -> dict[str, Any]:
        deadline = time.monotonic() + PAGE_SECONDS
        agent = _agent(agent)
        if resource not in RESOURCES or type(limit) is not int or not 1 <= limit <= 50:
            raise ValidationGlitch("Invalid export resource or limit", entity="belief_export")
        if start.tzinfo is None or end.tzinfo is None or end <= start:
            raise ValidationGlitch("Export requires an aware nonempty UTC interval", entity="belief_export")
        first, stop = utc(start.isoformat()), utc(end.isoformat())
        binding = hashlib.sha256(json.dumps([agent, resource, first, stop, limit]).encode()).hexdigest()
        decoded = self._decode(cursor, binding) if cursor is not None else None
        snapshot = decoded.snapshot.model_dump(exclude={"schema_version"}) if decoded else None
        last = (decoded.last_time, decoded.last_id) if decoded else ("", "")
        result = self.repository.page(agent, resource, first, stop, limit, snapshot, last)
        items = [self._projection(agent, item, deadline) for item in result["items"]]
        _budget(deadline)
        next_cursor = None
        if result["has_more"]:
            final = result["items"][-1]
            next_cursor = self._encode(
                ExportCursor(
                    binding=binding,
                    snapshot=ExportSnapshot.model_validate(result["snapshot"]),
                    last_time=final["timestamp"],
                    last_id=final["export_id"],
                )
            )
        page = {
            "agent_id": agent,
            "resource": resource,
            "from": first,
            "to": stop,
            "limit": limit,
            "items": items,
            "next_cursor": next_cursor,
            "snapshot": result["snapshot"],
            "interval_complete": not result["has_more"] and result["undated_rows"] == 0,
            "coverage": "stored_dated_rows_at_snapshot",
            "undated_rows": result["undated_rows"],
            "assessment_coverage": "completed_receipts_only",
            "tool_authority": "none",
        }
        if len(json.dumps(page, ensure_ascii=False).encode()) > 2_000_000:
            raise GlitchError(
                "Export page exceeds size budget; reduce limit",
                status_code=503,
                kind="resource_exhausted",
                entity="belief_export",
            )
        return page

    async def detail(
        self, agent: str, resource: Literal["encounters", "assessments", "decisions"], identity: str
    ) -> dict[str, Any]:
        return await asyncio.to_thread(self._detail, _agent(agent), resource, _identifier(identity))

    def _detail(self, agent: str, resource: str, identity: str) -> dict[str, Any]:
        deadline = time.monotonic() + PAGE_SECONDS
        return self._projection(agent, self.repository.detail(agent, resource, identity), deadline)
