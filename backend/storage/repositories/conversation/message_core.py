"""Message repository core collaborator."""

import json
from typing import Any

from backend.storage.connection import with_connection
from backend.storage.models import Message
from backend.storage.repositories.base import BaseRepository
from backend.storage.row_mappers import _row_to_message


class MessageCoreRepository(BaseRepository):
    @with_connection
    def insert(
        self,
        speaker: str,
        content: str,
        embedding: bytes,
        embedding_model: str,
        embedding_dim: int,
        thinking: str | None = None,
        agent_id: str = "",
        conversation_id: str = "",
        content_tokens: int = 0,
        thinking_tokens: int | None = None,
        model_used: str | None = None,
        provider_used: str | None = None,
        context_sent: str | None = None,
        structural_signature: bytes = b"",
        structural_justification: str | None = None,
        parent_message_id: int | None = None,
        active_skills: list[str] | str | None = None,
        active_beliefs: list[str] | str | None = None,
    ) -> Message:
        conn = self._conn()
        skills_str = json.dumps(active_skills) if isinstance(active_skills, list) else active_skills
        beliefs_str = json.dumps(active_beliefs) if isinstance(active_beliefs, list) else active_beliefs
        conn.execute(
            """INSERT INTO conversation_log
               (agent_id, speaker, content, thinking, context_sent, embedding, embedding_model, embedding_dim, conversation_id, content_tokens, thinking_tokens, model_used, provider_used, structural_signature, structural_justification, parent_message_id, active_skills, active_beliefs)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                agent_id,
                speaker,
                content,
                thinking,
                context_sent,
                embedding,
                embedding_model,
                embedding_dim,
                conversation_id,
                content_tokens,
                thinking_tokens,
                model_used,
                provider_used,
                structural_signature,
                structural_justification,
                parent_message_id,
                skills_str,
                beliefs_str,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM conversation_log WHERE id = last_insert_rowid()").fetchone()
        return _row_to_message(row)

    @with_connection
    def get_by_id(self, message_id: int) -> Message | None:
        conn = self._conn()
        row = conn.execute("SELECT * FROM conversation_log WHERE id = ?", (message_id,)).fetchone()
        if row is None:
            return None
        return _row_to_message(row)

    @with_connection
    def update_signature(self, message_id: int, structural_signature: bytes) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE conversation_log SET structural_signature = ? WHERE id = ?",
            (structural_signature, message_id),
        )
        conn.commit()

    @with_connection
    def update_embedding(self, message_id: int, embedding: bytes, embedding_model: str, embedding_dim: int) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE conversation_log SET embedding = ?, embedding_model = ?, embedding_dim = ? WHERE id = ?",
            (embedding, embedding_model, embedding_dim, message_id),
        )
        conn.commit()

    @with_connection
    def get_max_message_id(self) -> int:
        conn = self._conn()
        row = conn.execute("SELECT MAX(id) FROM conversation_log").fetchone()
        return row[0] if row and row[0] is not None else 0

    @with_connection
    def get_messages_without_signatures(self) -> list[Message]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM conversation_log WHERE structural_signature IS NULL ORDER BY id ASC"
        ).fetchall()
        return [_row_to_message(r) for r in rows]

    @with_connection
    def get_messages_without_metrics(self) -> list[Message]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT cl.* FROM conversation_log cl
               LEFT JOIN conversation_metrics cm ON cl.id = cm.message_id
               WHERE cm.message_id IS NULL
               ORDER BY cl.conversation_id, cl.id ASC"""
        ).fetchall()
        return [_row_to_message(r) for r in rows]

    @with_connection
    def get_surprise_index(self, message_id: int) -> float:
        conn = self._conn()
        row = conn.execute(
            "SELECT surprise_index FROM conversation_metrics WHERE message_id = ?",
            (message_id,),
        ).fetchone()
        if row and row["surprise_index"] is not None:
            return float(row["surprise_index"])
        return 0.0

    @with_connection
    def count_dreams_since(self, since_date_str: str) -> int:
        conn = self._conn()
        row = conn.execute(
            """SELECT COUNT(*) as cnt FROM dream_log
               WHERE timestamp >= ?""",
            (since_date_str,),
        ).fetchone()
        return row["cnt"] if row else 0

    @with_connection
    def mark_message_metabolized(self, message_id: int) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE conversation_log SET metabolized = 1 WHERE id = ?",
            (message_id,),
        )
        conn.commit()

    @with_connection
    def get_by_ids(self, message_ids: list[int]) -> list[Message]:
        if not message_ids:
            return []
        conn = self._conn()
        placeholders = ",".join("?" * len(message_ids))
        rows = conn.execute(
            f"SELECT * FROM conversation_log WHERE id IN ({placeholders})",
            message_ids,
        ).fetchall()
        return [_row_to_message(r) for r in rows]

    @with_connection
    def get_token_totals(self, conversation_id: str | None = None) -> list[dict[str, Any]]:
        conn = self._conn()
        if conversation_id is not None:
            rows = conn.execute(
                """SELECT conversation_id,
                          SUM(CASE WHEN speaker = 'human' THEN content_tokens ELSE 0 END) as user_tokens,
                          SUM(CASE WHEN speaker = 'apparatus' THEN content_tokens ELSE 0 END) as agent_tokens,
                          COALESCE(SUM(thinking_tokens), 0) as thinking_tokens
                   FROM conversation_log
                   WHERE conversation_id = ? AND conversation_id != ''
                   GROUP BY conversation_id""",
                (conversation_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT conversation_id,
                          SUM(CASE WHEN speaker = 'human' THEN content_tokens ELSE 0 END) as user_tokens,
                          SUM(CASE WHEN speaker = 'apparatus' THEN content_tokens ELSE 0 END) as agent_tokens,
                          COALESCE(SUM(thinking_tokens), 0) as thinking_tokens
                   FROM conversation_log
                   WHERE conversation_id != ''
                   GROUP BY conversation_id
                   ORDER BY conversation_id""",
            ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def reassign_messages(self, from_conversation_id: str, to_conversation_id: str) -> int:
        conn = self._conn()
        cursor = conn.execute(
            "UPDATE conversation_log SET conversation_id = ? WHERE conversation_id = ?",
            (to_conversation_id, from_conversation_id),
        )
        conn.commit()
        return cursor.rowcount

    @with_connection
    def increment_message_note_count(self, message_id: int, amount: int = 1) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE conversation_log SET note_count = COALESCE(note_count, 0) + ? WHERE id = ?",
            (amount, message_id),
        )
        conn.commit()

    @with_connection
    def update_content(self, message_id: int, content: str) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE conversation_log SET content = ? WHERE id = ?",
            (content, message_id),
        )
        conn.commit()

    @with_connection
    def delete_message(self, message_id: int) -> None:
        """Delete a single message and its related data (cascade).
        Child messages are reparented to the deleted message's parent."""
        conn = self._conn()

        # Get the parent of the message being deleted
        row = conn.execute("SELECT parent_message_id FROM conversation_log WHERE id = ?", (message_id,)).fetchone()
        grandparent_id = row["parent_message_id"] if row else None

        # Reparent direct children to the deleted message's parent
        conn.execute(
            "UPDATE conversation_log SET parent_message_id = ? WHERE parent_message_id = ?",
            (grandparent_id, message_id),
        )

        # Clean up related records
        conn.execute("DELETE FROM conversation_metrics WHERE message_id = ?", (message_id,))
        conn.execute("DELETE FROM message_links WHERE source_id = ? OR target_id = ?", (message_id, message_id))
        conn.execute("DELETE FROM notes WHERE asset_type = 'conversation_message' AND asset_id = ?", (str(message_id),))
        conn.execute("DELETE FROM conversation_log WHERE id = ?", (message_id,))
        conn.commit()
