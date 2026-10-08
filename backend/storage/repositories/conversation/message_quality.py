"""Atomic quality receipts and review traces; originals remain inspectable."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, cast

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository
from backend.utils.message_quality import content_hash


class MessageQualityRepository(BaseRepository):
    @with_connection
    def save_quality(self, message_id: int, receipt: dict[str, Any]) -> dict[str, Any]:
        conn = self._conn()
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM conversation_log WHERE id = ?", (message_id,)).fetchone()
            if row is None:
                raise LookupError("Message not found")
            if row["speaker"] != "apparatus":
                raise ValueError("Only assistant messages can be assessed")
            if receipt.get("content_hash") != content_hash(row["content"]):
                raise ValueError("Message content changed; reassessment required")
            previous = json.loads(row["quality_receipt"]) if row["quality_receipt"] else None
            if previous and previous.get("source") == "manual" and receipt.get("source") != "manual":
                return cast(dict[str, Any], previous)
            if receipt.get("status") not in {"sound", "degraded", "uncertain", "unassessed"}:
                raise ValueError("Invalid quality status")
            saved = {**receipt, "assessed_at": datetime.now(UTC).isoformat()}
            saved["excluded_from_context"] = saved["status"] == "degraded"
            encoded = json.dumps(saved, allow_nan=False)
            conn.execute(
                "UPDATE conversation_log SET quality_status = ?, quality_receipt = ? WHERE id = ?",
                (saved["status"], encoded, message_id),
            )
            conn.execute(
                "INSERT INTO message_quality_events(message_id, assessed_at, receipt) VALUES (?, ?, ?)",
                (message_id, saved["assessed_at"], encoded),
            )
            # One durable trace per message; reassessments update rather than duplicate it.
            trace_id = f"quality-{message_id}"
            if saved["status"] in {"degraded", "uncertain"}:
                detail = (
                    "Excluded from generation context"
                    if saved["status"] == "degraded"
                    else "Needs review; remains in context"
                )
                confidence = saved.get("confidence")
                suffix = f"; Jev confidence {confidence:.2f}" if isinstance(confidence, (int, float)) else ""
                snippet = f"Response quality: {saved['status']}. {detail}. Reason: {saved['reason']}{suffix}."
                conn.execute(
                    """INSERT INTO notifications(id, type, timestamp, snippet, conversation_id,
                       message_id, parent_message_id, speaker, source, source_type, source_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 'apparatus', 'response-quality', 'conversation', ?)
                       ON CONFLICT(id) DO UPDATE SET type=excluded.type, snippet=excluded.snippet, timestamp=excluded.timestamp,
                       read=0, dismissed=0""",
                    (
                        trace_id,
                        "glitch" if saved["status"] == "degraded" else "trace",
                        saved["assessed_at"],
                        snippet,
                        row["conversation_id"],
                        message_id,
                        row["parent_message_id"],
                        row["conversation_id"],
                    ),
                )
            else:
                conn.execute("UPDATE notifications SET dismissed=1 WHERE id=?", (trace_id,))
        return saved

    @with_connection
    def degraded_ids(self, conversation_id: str) -> set[int]:
        rows = (
            self._conn()
            .execute(
                "SELECT id FROM conversation_log WHERE conversation_id=? AND quality_status='degraded'",
                (conversation_id,),
            )
            .fetchall()
        )
        return {row["id"] for row in rows}

    @with_connection
    def list_quality(self, status: str, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        rows = (
            self._conn()
            .execute(
                """SELECT id, conversation_id, timestamp, content, quality_receipt FROM conversation_log
               WHERE quality_status=? ORDER BY id DESC LIMIT ? OFFSET ?""",
                (status, limit, offset),
            )
            .fetchall()
        )
        return [
            {
                "message_id": row["id"],
                "conversation_id": row["conversation_id"],
                "timestamp": row["timestamp"],
                "preview": row["content"][:300],
                "quality": json.loads(row["quality_receipt"]),
            }
            for row in rows
        ]
