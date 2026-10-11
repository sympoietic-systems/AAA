"""Bounded, read-transaction export of existing agent-owned ledger records."""

import json
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from backend.errors import ConstraintViolation, GlitchError, ResourceNotFound
from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository

# Static SQL only: resource selection never interpolates caller input.
SOURCES = {
    "encounter": ("belief_encounters e", "e.agent_id", "e.id", "e.received_at", "e.encounter_json", "e.rowid"),
    "assessment": (
        "belief_assessment_completions x JOIN belief_admission e ON e.id=x.ledger_id",
        "e.agent_id",
        "e.assessment_id",
        "e.assessed_at",
        "e.receipt",
        "x.sequence",
    ),
    "legacy_assessment": (
        "belief_assessment_completions x JOIN belief_admission e ON e.id=x.ledger_id "
        "LEFT JOIN belief_proposals p ON p.id=e.proposal_id LEFT JOIN belief_nodes n ON n.id=e.proposal_id",
        "COALESCE(p.agent_id,n.agent_id)",
        "e.id",
        "e.assessed_at",
        "e.receipt",
        "x.sequence",
    ),
    "decision": ("belief_review_decisions e", "e.agent_id", "e.id", "e.timestamp", "e.decision_json", "e.rowid"),
    "event": ("belief_review_events e", "e.agent_id", "e.id", "e.timestamp", "e.receipt_json", "e.rowid"),
    "legacy_event": (
        "belief_events e JOIN belief_nodes n ON n.id=e.belief_id",
        "n.agent_id",
        "e.id",
        "e.timestamp",
        "NULL",
        "e.rowid",
    ),
}
RESOURCES = {
    "encounters": ("encounter",),
    "assessments": ("assessment", "legacy_assessment"),
    "decisions": ("decision",),
    "events": ("event", "legacy_event"),
}
TABLES = {
    "encounter": "belief_encounters",
    "assessment": "belief_assessment_completions",
    "decision": "belief_review_decisions",
    "event": "belief_review_events",
    "legacy_event": "belief_events",
}
MAX_RECEIPT_BYTES = 256_000
READ_SECONDS = 3.0


def utc(value: str | None) -> str:
    """Legacy SQLite CURRENT_TIMESTAMP is UTC; absent/unparseable dates remain unknown."""
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.replace(tzinfo=parsed.tzinfo or UTC).astimezone(UTC).isoformat(timespec="microseconds")
    except (ValueError, OverflowError):
        return ""


class BeliefExportRepository(BaseRepository):
    @with_connection
    def source_accounting(self, agent: str, encounter: str) -> dict[str, Any] | None:
        with self._read() as conn:
            row = conn.execute(
                "SELECT CASE WHEN length(CAST(o.receipt_json AS BLOB))<=? THEN o.receipt_json END "
                "FROM belief_source_observations o JOIN belief_encounters e ON e.agent_id=o.agent_id "
                "AND e.id=o.encounter_id WHERE o.agent_id=? AND o.encounter_id=?",
                (MAX_RECEIPT_BYTES, agent, encounter),
            ).fetchone()
            if row is None:
                return None
            if row[0] is None:
                raise GlitchError(
                    "Source observation exceeds export size budget",
                    status_code=503,
                    kind="resource_exhausted",
                    entity="belief_export",
                )
            return dict(json.loads(row[0]))

    @contextmanager
    def _read(self) -> Iterator[sqlite3.Connection]:
        conn = self._conn()
        if conn.in_transaction:
            raise ConstraintViolation("Export requires an independent read transaction", entity="belief_export")
        deadline = time.monotonic() + READ_SECONDS
        conn.create_function("export_utc", 1, utc, deterministic=True)
        conn.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        conn.execute("BEGIN")
        try:
            yield conn
        except sqlite3.OperationalError as error:
            if error.sqlite_errorcode == sqlite3.SQLITE_INTERRUPT:
                raise GlitchError(
                    "Export read budget exceeded; narrow the interval",
                    status_code=503,
                    kind="resource_exhausted",
                    entity="belief_export",
                ) from error
            raise
        finally:
            conn.rollback()
            conn.set_progress_handler(None, 0)

    def _snapshot(self, conn: sqlite3.Connection) -> dict[str, Any]:
        row = conn.execute("SELECT database_id,legacy_generation FROM belief_export_meta WHERE id=1").fetchone()
        result: dict[str, Any] = {"database_id": row[0], "legacy_generation": row[1]}
        for key, table in TABLES.items():
            result[key] = conn.execute(f"SELECT COALESCE(MAX(rowid),0) FROM {table}").fetchone()[0]
        return result

    def _check(self, current: dict[str, Any], saved: dict[str, Any], resource: str) -> None:
        if current["database_id"] != saved["database_id"] or any(current[k] < saved[k] for k in TABLES):
            raise ConstraintViolation("Export snapshot no longer available; restart export", entity="belief_export")
        if resource in ("events", "assessments") and current["legacy_generation"] != saved["legacy_generation"]:
            raise ConstraintViolation("Legacy history changed; restart export", entity="belief_export")

    def _rows(
        self,
        conn: sqlite3.Connection,
        kind: str,
        agent: str,
        watermark: int,
        start: str,
        end: str,
        last: tuple[str, str],
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        source, owner, identity, timestamp, payload, order = SOURCES[kind]
        native = " AND e.assessment_id IS NOT NULL" if kind == "assessment" else ""
        if kind == "legacy_assessment":
            native = " AND e.assessment_id IS NULL"
        prefix = kind + ":"
        key = f"(? || {identity})"
        base = f"{owner}=? AND {order}<=?{native}"
        extra = "x.index_origin AS export_index_origin," if kind in ("assessment", "legacy_assessment") else ""
        if kind == "legacy_event":
            fields = (
                "id",
                "timestamp",
                "belief_id",
                "source_type",
                "source_id",
                "alignment_coefficient",
                "perturbation_magnitude",
                "event_type",
                "impact_score",
                "rationale",
                "impact_quantity",
                "impact_unit",
                "delta_mass",
                "confidence_delta",
            )
            size = "+".join(f"COALESCE(length(CAST(e.{field} AS BLOB)),0)" for field in fields)
            payload = "json_object(" + ",".join(f"'{field}',e.{field}" for field in fields) + ")"
        else:
            size = f"length(CAST({payload} AS BLOB))"
        unknown = conn.execute(
            f"SELECT COUNT(*) FROM {source} WHERE {base} AND export_utc({timestamp})=''", (agent, watermark)
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT {identity} AS export_identity,export_utc({timestamp}) AS export_time,"
            f"{key} AS export_key,{extra}{size} AS payload_bytes,"
            f"CASE WHEN ({size})<=? THEN {payload} END AS export_payload "
            f"FROM {source} WHERE {base} AND export_utc({timestamp})>=? AND export_utc({timestamp})<? "
            f"AND (export_utc({timestamp}),{key})>(?,?) ORDER BY export_time,export_key LIMIT ?",
            (prefix, MAX_RECEIPT_BYTES, agent, watermark, start, end, prefix, *last, limit),
        ).fetchall()
        result = []
        for row in rows:
            if row["payload_bytes"] and row["payload_bytes"] > MAX_RECEIPT_BYTES:
                raise GlitchError(
                    "Stored receipt exceeds export size budget",
                    status_code=503,
                    kind="resource_exhausted",
                    entity="belief_export",
                )
            if kind == "legacy_event":
                value = json.loads(row["export_payload"])
                value.update(
                    impact_value=value["impact_score"],
                    delta_confidence=value["impact_score"],
                    receipt_id=None,
                    encounter_id=None,
                    origin="legacy",
                )
            else:
                value = json.loads(row["export_payload"])
            result.append(
                {
                    "export_id": row["export_key"],
                    "id": row["export_identity"],
                    "timestamp": row["export_time"],
                    "kind": kind,
                    "record": value,
                }
            )
            if extra:
                result[-1]["completion_index_origin"] = row["export_index_origin"]
        return result, unknown

    @with_connection
    def page(
        self,
        agent: str,
        resource: str,
        start: str,
        end: str,
        limit: int,
        snapshot: dict[str, Any] | None,
        last: tuple[str, str],
    ) -> dict[str, Any]:
        with self._read() as conn:
            current = self._snapshot(conn)
            saved = snapshot or current
            self._check(current, saved, resource)
            items: list[dict[str, Any]] = []
            unknown = 0
            for kind in RESOURCES[resource]:
                watermark = int(saved["assessment" if kind == "legacy_assessment" else kind])
                found, undated = self._rows(conn, kind, agent, watermark, start, end, last, limit + 1)
                items.extend(found)
                unknown += undated
            items.sort(key=lambda item: (item["timestamp"], item["export_id"]))
            return {"items": items[:limit], "has_more": len(items) > limit, "snapshot": saved, "undated_rows": unknown}

    @with_connection
    def detail(self, agent: str, resource: str, identity: str) -> dict[str, Any]:
        with self._read() as conn:
            kind = {"encounters": "encounter", "assessments": "assessment", "decisions": "decision"}[resource]
            source, owner, id_column, timestamp, payload, _ = SOURCES[kind]
            # Pending assessments are available individually, but cannot enter immutable exports.
            if kind == "assessment":
                source = "belief_admission e"
            row = conn.execute(
                f"SELECT CASE WHEN length(CAST({payload} AS BLOB))<=? THEN {payload} END,"
                f"export_utc({timestamp}) FROM {source} WHERE {owner}=? AND {id_column}=?",
                (MAX_RECEIPT_BYTES, agent, identity),
            ).fetchone()
            if row is None:
                raise ResourceNotFound("Belief review record not found", entity="belief_export")
            if row[0] is None:
                raise GlitchError(
                    "Stored receipt exceeds export size budget",
                    status_code=503,
                    kind="resource_exhausted",
                    entity="belief_export",
                )
            return {
                "export_id": kind + ":" + identity,
                "id": identity,
                "timestamp": row[1] or None,
                "kind": kind,
                "record": json.loads(row[0]),
            }
