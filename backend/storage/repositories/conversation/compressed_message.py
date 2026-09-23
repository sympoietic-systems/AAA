"""R5: Repository for LLM-compressed message blocks."""

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


class CompressedMessageRepository(BaseRepository):
    """CRUD for compressed_messages table (R5 LLM batch compression)."""

    @with_connection
    def save(
        self,
        conversation_id: str,
        first_message_id: int,
        last_message_id: int,
        compressed_block: str,
    ) -> int:
        conn = self._conn()
        conn.execute(
            """INSERT INTO compressed_messages
               (conversation_id, first_message_id, last_message_id, compressed_block)
               VALUES (?, ?, ?, ?)""",
            (conversation_id, first_message_id, last_message_id, compressed_block),
        )
        conn.commit()
        row = conn.execute("SELECT id FROM compressed_messages WHERE id = last_insert_rowid()").fetchone()
        return row["id"] if row else 0

    @with_connection
    def get_for_messages(self, conversation_id: str, message_ids: list[int]) -> list[dict]:
        """Get compressed blocks that span the given message IDs."""
        conn = self._conn()
        if not message_ids:
            return []
        min_id, max_id = min(message_ids), max(message_ids)
        rows = conn.execute(
            """SELECT * FROM compressed_messages
               WHERE conversation_id = ?
                 AND first_message_id >= ?
                 AND last_message_id <= ?
               ORDER BY first_message_id ASC""",
            (conversation_id, min_id, max_id),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "conversation_id": row["conversation_id"],
                "first_message_id": row["first_message_id"],
                "last_message_id": row["last_message_id"],
                "compressed_block": row["compressed_block"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    @with_connection
    def delete_for_conversation(self, conversation_id: str) -> None:
        conn = self._conn()
        conn.execute(
            "DELETE FROM compressed_messages WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.commit()
