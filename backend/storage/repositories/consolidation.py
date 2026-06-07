from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


class ConsolidationCheckpointRepository(BaseRepository):
    @with_connection
    def save(self, conversation_id: str, message_count: int, summary: str, model: str = "", human_summary: str = "") -> int:
        conn = self._conn()
        conn.execute(
            """INSERT INTO consolidation_checkpoints (conversation_id, message_count, summary, model, human_summary)
               VALUES (?, ?, ?, ?, ?)""",
            (conversation_id, message_count, summary, model, human_summary),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id FROM consolidation_checkpoints WHERE id = last_insert_rowid()"
        ).fetchone()
        return row["id"] if row else 0

    @with_connection
    def get_latest(self, conversation_id: str) -> dict | None:
        conn = self._conn()
        row = conn.execute(
            """SELECT * FROM consolidation_checkpoints
               WHERE conversation_id = ?
               ORDER BY id DESC LIMIT 1""",
            (conversation_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "conversation_id": row["conversation_id"],
            "message_count": row["message_count"],
            "summary": row["summary"],
            "model": row["model"],
            "human_summary": row["human_summary"] if "human_summary" in row.keys() else "",
            "created_at": row["created_at"],
        }

    @with_connection
    def delete_by_conversation(self, conversation_id: str) -> None:
        conn = self._conn()
        conn.execute(
            "DELETE FROM consolidation_checkpoints WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.commit()
