"""Build a bounded, read-only view of runtime release evidence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from backend.storage import migrations
from backend.storage.activation import ActivationTrace

_REQUIRED_MIGRATIONS = {
    "051_activation_provenance",
    "059_message_quality",
    "061_message_generation_receipt",
    "064_belief_review_persistence",
    "065_belief_explicit_intake",
    "066_belief_source_accounting",
    "067_belief_workshop",
    "068_belief_export_order",
    "069_belief_revision_links",
}
_MAX_RECENT_ROWS = 5000
_FLAG_PATHS = {
    "belief_assessment_enabled": ("belief_review", "assessment", "enabled"),
    "belief_participation_enabled": ("belief_review", "participation", "enabled"),
    "belief_participation_slots": ("belief_review", "participation", "slots"),
    "belief_intake_document": ("belief_review", "origin_intake", "document"),
    "belief_intake_shared_note": ("belief_review", "origin_intake", "shared_note"),
    "belief_intake_web": ("belief_review", "origin_intake", "web"),
    "belief_intake_explicit_chat": ("belief_review", "origin_intake", "explicit_chat"),
    "belief_intake_explicit_dream": ("belief_review", "origin_intake", "explicit_dream"),
    "belief_intake_passive_chat": ("belief_review", "origin_intake", "passive_chat"),
    "belief_intake_conversation_pattern": ("belief_review", "origin_intake", "conversation_pattern"),
    "belief_intake_scar_fold": ("belief_review", "origin_intake", "scar_fold"),
    "research_triage_enabled": ("research_triage", "enabled"),
}


def _nested_value(config: dict[str, Any], path: tuple[str, ...]) -> bool | int | None:
    value: Any = config
    for part in path:
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    return None


def _build_revision() -> str | None:
    revision = os.environ.get("AAA_BUILD_REVISION", "").strip().lower()
    return revision if re.fullmatch(r"[0-9a-f]{7,40}", revision) else None


def _expected_migrations() -> list[str]:
    migration_dir = Path(migrations.__file__).parent
    return sorted(
        f"{path.stem[1:4]}_{path.stem[5:]}"
        for path in migration_dir.glob("m[0-9][0-9][0-9]_*.py")
        if int(path.stem[1:4]) > 50
    )


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def build_release_readiness(
    config: dict[str, Any], database_path: str, days: int, *, now: datetime | None = None
) -> dict[str, Any]:
    """Report effective in-process flags and bounded DB coverage without mutations."""
    current = now.astimezone(UTC) if now else datetime.now(UTC)
    start = current - timedelta(days=days)
    flags = {name: _nested_value(config, path) for name, path in _FLAG_PATHS.items()}
    flags_hash = hashlib.sha256(json.dumps(flags, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    path = Path(database_path).resolve()
    uri = f"{path.as_uri()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        conn.execute("BEGIN")
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "conversation_log" not in tables:
            raise ValueError("Database has no conversation_log table")
        columns = {row[1] for row in conn.execute("PRAGMA table_info(conversation_log)")}
        migration_available = "_migrations" in tables
        applied = (
            sorted(row[0] for row in conn.execute("SELECT name FROM _migrations")) if migration_available else None
        )
        expected = _expected_migrations()
        missing = sorted(_REQUIRED_MIGRATIONS - set(applied or [])) if migration_available else None
        selected = {
            "timestamp": "timestamp" if "timestamp" in columns else "NULL",
            "activation_provenance": "activation_provenance" if "activation_provenance" in columns else "NULL",
            "generation_receipt": "generation_receipt" if "generation_receipt" in columns else "NULL",
            "quality_status": "quality_status" if "quality_status" in columns else "NULL",
            "quality_receipt": "quality_receipt" if "quality_receipt" in columns else "NULL",
        }
        query = (
            "SELECT "
            + ", ".join(f"{column} AS {alias}" for alias, column in selected.items())
            + " FROM conversation_log WHERE speaker='apparatus' ORDER BY id DESC LIMIT ?"
        )
        fetched = conn.execute(query, (_MAX_RECENT_ROWS + 1,)).fetchall()
    scan_truncated = len(fetched) > _MAX_RECENT_ROWS
    recent = []
    invalid_timestamps = 0
    for row in fetched[:_MAX_RECENT_ROWS]:
        timestamp = _parse_timestamp(row["timestamp"])
        if timestamp is None:
            invalid_timestamps += 1
        elif start <= timestamp <= current:
            recent.append(row)

    activation_counts: Counter[str] = Counter()
    generation_present = 0
    quality_status_counts: Counter[str] = Counter()
    quality_present = 0
    quality_invalid = 0
    for row in recent:
        raw_activation = row["activation_provenance"]
        if raw_activation is None:
            activation_counts["unknown"] += 1
        else:
            try:
                trace = ActivationTrace.model_validate_json(raw_activation)
            except (ValidationError, TypeError):
                activation_counts["invalid"] += 1
            else:
                activation_counts[trace.coverage] += 1
        if row["generation_receipt"]:
            generation_present += 1
        status = row["quality_status"]
        quality_status_counts[status if isinstance(status, str) else "unknown"] += 1
        raw_quality = row["quality_receipt"]
        if raw_quality:
            quality_present += 1
            try:
                json.loads(raw_quality)
            except (json.JSONDecodeError, TypeError):
                quality_invalid += 1

    generated_at = current
    return {
        "generated_at": generated_at,
        "read_only": True,
        "build_revision": _build_revision(),
        "config_flags_sha256": flags_hash,
        "effective_flags": flags,
        "window_days": days,
        "recent_assistant_rows": len(recent),
        "rows_examined": min(len(fetched), _MAX_RECENT_ROWS),
        "scan_truncated": scan_truncated,
        "invalid_timestamp_rows": invalid_timestamps,
        "migration_table_available": migration_available,
        "applied_migrations": applied,
        "expected_migrations": expected,
        "missing_migrations": missing,
        "activation_provenance": {
            "available": "activation_provenance" in columns,
            "counts": dict(activation_counts) if "activation_provenance" in columns else None,
            "interpretation": "Assembly provenance does not establish response influence.",
        },
        "generation_receipts": {
            "available": "generation_receipt" in columns,
            "present": generation_present if "generation_receipt" in columns else None,
            "missing": len(recent) - generation_present if "generation_receipt" in columns else None,
        },
        "response_quality": {
            "available": {
                "quality_status": "quality_status" in columns,
                "quality_receipt": "quality_receipt" in columns,
            },
            "status_counts": dict(quality_status_counts) if "quality_status" in columns else None,
            "receipt_present": quality_present if "quality_receipt" in columns else None,
            "receipt_missing": len(recent) - quality_present if "quality_receipt" in columns else None,
            "receipt_invalid": quality_invalid if "quality_receipt" in columns else None,
        },
    }
