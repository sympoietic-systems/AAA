"""Message repository history collaborator."""

from datetime import datetime
from typing import Any

from backend.storage.connection import with_connection
from backend.storage.models import Message
from backend.storage.repositories.base import BaseRepository
from backend.storage.row_mappers import _row_to_message


class MessageHistoryRepository(BaseRepository):
    @with_connection
    def get_recent(self, limit: int = 50, conversation_id: str | None = None) -> list[Message]:
        conn = self._conn()
        if conversation_id is not None:
            rows = conn.execute(
                "SELECT * FROM conversation_log WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
                (conversation_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM conversation_log ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_row_to_message(r) for r in reversed(rows)]

    @with_connection
    def get_messages_since(self, conversation_id: str, last_message_count: int) -> list[Message]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM conversation_log WHERE conversation_id = ? ORDER BY id ASC",
            (conversation_id,),
        ).fetchall()
        messages = [_row_to_message(r) for r in rows]
        return messages[last_message_count:]

    @with_connection
    def get_last_message_timestamp(self, conversation_id: str | None = None) -> datetime | None:
        conn = self._conn()
        if conversation_id:
            row = conn.execute(
                "SELECT timestamp FROM conversation_log WHERE conversation_id = ? ORDER BY id DESC LIMIT 1",
                (conversation_id,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT timestamp FROM conversation_log ORDER BY id DESC LIMIT 1",
            ).fetchone()
        if row is None or not row["timestamp"]:
            return None
        try:
            return datetime.fromisoformat(row["timestamp"])
        except Exception:
            return None

    @with_connection
    def get_messages_by_conversation(self, conversation_id: str) -> list[Message]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM conversation_log WHERE conversation_id = ? ORDER BY id ASC",
            (conversation_id,),
        ).fetchall()
        return [_row_to_message(r) for r in rows]

    @with_connection
    def get_recent_assistant_signatures(self, conversation_id: str, limit: int = 5) -> list[bytes]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT structural_signature FROM conversation_log
               WHERE conversation_id = ? AND speaker = 'apparatus' AND structural_signature IS NOT NULL
               ORDER BY id DESC LIMIT ?""",
            (conversation_id, limit),
        ).fetchall()
        signatures = []
        for r in rows:
            blob = r["structural_signature"]
            if blob:
                signatures.append(blob)
        return signatures

    @with_connection
    def get_recent_with_metrics(
        self,
        limit: int = 50,
        offset: int = 0,
        conversation_id: str | None = None,
        exclude_message_id: int | None = None,
    ) -> list[dict[str, Any]]:
        conn = self._conn()
        exclude_clause = "AND cl.id != ?" if exclude_message_id is not None else ""
        if conversation_id is not None:
            params = (
                (conversation_id,) + ((exclude_message_id,) if exclude_message_id is not None else ()) + (limit, offset)
            )
            rows = conn.execute(
                f"""SELECT cl.id, cl.timestamp, cl.speaker, cl.content, cl.thinking,
                          cl.content_tokens, cl.thinking_tokens, cl.model_used, cl.provider_used,
                          cl.structural_signature, cl.structural_justification, cl.parent_message_id,
                          cl.active_skills, cl.active_beliefs, cl.context_sent,
                          (cl.context_sent IS NOT NULL AND cl.context_sent != '') AS has_context,
                          cm.s_t, cm.novelty, cm.rolling_entropy, cm.coupling,
                          cm.agent_divergence, cm.deficit,
                          cm.reverse_perturbation, cm.surprise_index,
                          cm.mutual_perturbation, cm.vitality,
                          cm.boringness, cm.conceptual_velocity,
                          cm.divergence_resolution_ratio, cm.paskian_health
                    FROM conversation_log cl
                    LEFT JOIN conversation_metrics cm ON cl.id = cm.message_id
                    WHERE cl.conversation_id = ? {exclude_clause}
                    ORDER BY cl.id DESC LIMIT ? OFFSET ?""",
                params,
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT cl.id, cl.timestamp, cl.speaker, cl.content, cl.thinking,
                          cl.content_tokens, cl.thinking_tokens, cl.model_used, cl.provider_used,
                          cl.structural_signature, cl.structural_justification, cl.parent_message_id,
                          cl.active_skills, cl.active_beliefs, cl.context_sent,
                          (cl.context_sent IS NOT NULL AND cl.context_sent != '') AS has_context,
                          cm.s_t, cm.novelty, cm.rolling_entropy, cm.coupling,
                          cm.agent_divergence, cm.deficit,
                          cm.reverse_perturbation, cm.surprise_index,
                          cm.mutual_perturbation, cm.vitality,
                          cm.boringness, cm.conceptual_velocity,
                          cm.divergence_resolution_ratio, cm.paskian_health
                    FROM conversation_log cl
                    LEFT JOIN conversation_metrics cm ON cl.id = cm.message_id
                    ORDER BY cl.id DESC LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    @with_connection
    def get_recent_with_metrics_for_path(
        self, message_ids: list[int], limit: int = 5, exclude_message_id: int | None = None
    ) -> list[dict[str, Any]]:
        if not message_ids:
            return []
        conn = self._conn()
        ids = list(message_ids)
        if exclude_message_id is not None:
            ids = [i for i in ids if i != exclude_message_id]
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        rows = conn.execute(
            f"""SELECT cl.id, cl.timestamp, cl.speaker, cl.content, cl.thinking,
                      cl.content_tokens, cl.thinking_tokens, cl.model_used, cl.provider_used,
                      cl.structural_signature, cl.structural_justification, cl.parent_message_id,
                      cl.active_skills, cl.active_beliefs, cl.context_sent,
                      (cl.context_sent IS NOT NULL AND cl.context_sent != '') AS has_context,
                      cm.s_t, cm.novelty, cm.rolling_entropy, cm.coupling,
                      cm.agent_divergence, cm.deficit,
                      cm.reverse_perturbation, cm.surprise_index,
                      cm.mutual_perturbation, cm.vitality,
                      cm.boringness, cm.conceptual_velocity,
                      cm.divergence_resolution_ratio, cm.paskian_health
                FROM conversation_log cl
                LEFT JOIN conversation_metrics cm ON cl.id = cm.message_id
                WHERE cl.id IN ({placeholders})
                ORDER BY cl.id DESC LIMIT ?""",
            ids + [limit],
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    @with_connection
    def count_messages(self, conversation_id: str | None = None) -> int:
        conn = self._conn()
        if conversation_id:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM conversation_log WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) as cnt FROM conversation_log").fetchone()
        return row["cnt"] if row else 0

    @with_connection
    def get_sediment_messages_with_metadata(self, message_ids: list[int]) -> list[dict[str, Any]]:
        if not message_ids:
            return []
        conn = self._conn()
        placeholders = ",".join("?" * len(message_ids))
        rows = conn.execute(
            f"""SELECT cl.*, c.title as conversation_title
               FROM conversation_log cl
               LEFT JOIN conversations c ON cl.conversation_id = c.id
               WHERE cl.id IN ({placeholders})""",
            message_ids,
        ).fetchall()
        results = []
        for row in rows:
            results.append(
                {
                    "id": row["id"],
                    "timestamp": datetime.fromisoformat(row["timestamp"]) if row["timestamp"] else datetime.now(),
                    "conversation_id": row["conversation_id"],
                    "speaker": row["speaker"],
                    "content": row["content"],
                    "conversation_title": row["conversation_title"] or "Untitled Conversation",
                }
            )
        return results
