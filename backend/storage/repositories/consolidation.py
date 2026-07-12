from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


class ConsolidationCheckpointRepository(BaseRepository):
    @with_connection
    def save(
        self,
        conversation_id: str,
        message_count: int,
        summary: str,
        model: str = "",
        human_summary: str = "",
        message_id: int | None = None,
    ) -> int:
        conn = self._conn()
        conn.execute(
            """INSERT INTO consolidation_checkpoints (conversation_id, message_count, summary, model, human_summary, message_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (conversation_id, message_count, summary, model, human_summary, message_id),
        )
        conn.commit()
        row = conn.execute("SELECT id FROM consolidation_checkpoints WHERE id = last_insert_rowid()").fetchone()
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
        return _row_to_checkpoint(row)

    @with_connection
    def update_human_summary(self, checkpoint_id: int, human_summary: str) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE consolidation_checkpoints SET human_summary = ? WHERE id = ?",
            (human_summary, checkpoint_id),
        )
        conn.commit()

    @with_connection
    def delete_by_conversation(self, conversation_id: str) -> None:
        conn = self._conn()
        conn.execute(
            "DELETE FROM consolidation_checkpoints WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.commit()

    @with_connection
    def get_latest_checkpoint_for_path(self, conversation_id: str, message_ids: list[int]) -> dict | None:
        conn = self._conn()
        if not message_ids:
            return self.get_latest(conversation_id)
        placeholders = ",".join("?" * len(message_ids))
        row = conn.execute(
            f"""SELECT * FROM consolidation_checkpoints
               WHERE conversation_id = ? AND (message_id IN ({placeholders}) OR message_id IS NULL)
               ORDER BY id DESC LIMIT 1""",
            [conversation_id] + message_ids,
        ).fetchone()
        if row is None:
            return None
        return _row_to_checkpoint(row)

    @with_connection
    def get_sibling_checkpoints(self, conversation_id: str, exclude_message_ids: list[int]) -> list[dict]:
        """R3: Get checkpoints from sibling branches (same conversation, different paths).

        Returns checkpoints whose message_id is NOT in the current ancestor path,
        enabling cross-branch memory node retrieval.
        """
        conn = self._conn()
        if not exclude_message_ids:
            rows = conn.execute(
                """SELECT * FROM consolidation_checkpoints
                   WHERE conversation_id = ? AND message_id IS NOT NULL
                   ORDER BY id DESC""",
                (conversation_id,),
            ).fetchall()
        else:
            placeholders = ",".join("?" * len(exclude_message_ids))
            rows = conn.execute(
                f"""SELECT * FROM consolidation_checkpoints
                   WHERE conversation_id = ?
                     AND message_id IS NOT NULL
                     AND message_id NOT IN ({placeholders})
                   ORDER BY id DESC""",
                [conversation_id] + exclude_message_ids,
            ).fetchall()

        return [_row_to_checkpoint(row) for row in rows]


def _row_to_checkpoint(row) -> dict:
    return {
        "id": row["id"],
        "conversation_id": row["conversation_id"],
        "message_count": row["message_count"],
        "summary": row["summary"],
        "model": row["model"],
        "human_summary": row["human_summary"] if "human_summary" in row.keys() else "",
        "message_id": row["message_id"] if "message_id" in row.keys() else None,
        "created_at": row["created_at"],
    }
