from typing import Optional

from backend.storage.connection import with_connection
from backend.storage.models import Conversation
from backend.storage.repositories.base import BaseRepository
from backend.storage.row_mappers import _row_to_conversation


class ConversationRepository(BaseRepository):
    @with_connection
    def create(self, conversation_id: str, agent_id: str = "", title: str = "") -> Conversation:
        conn = self._conn()
        conn.execute(
            """INSERT INTO conversations (id, title, agent_id)
               VALUES (?, ?, ?)""",
            (conversation_id, title, agent_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        return _row_to_conversation(row)

    @with_connection
    def get(self, conversation_id: str) -> Optional[Conversation]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        if row is None:
            return None
        return _row_to_conversation(row)

    @with_connection
    def list_all(self, tag: Optional[str] = None) -> list[Conversation]:
        conn = self._conn()
        if tag:
            rows = conn.execute(
                """SELECT c.*, COUNT(cl.id) as message_count
                   FROM conversations c
                   LEFT JOIN conversation_log cl ON c.id = cl.conversation_id
                   JOIN conversation_tags ct ON c.id = ct.conversation_id
                   WHERE ct.tag = ?
                   GROUP BY c.id
                   ORDER BY MAX(cl.timestamp) DESC""",
                (tag,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT c.*, COUNT(cl.id) as message_count
                   FROM conversations c
                   LEFT JOIN conversation_log cl ON c.id = cl.conversation_id
                   GROUP BY c.id
                   ORDER BY MAX(cl.timestamp) DESC"""
            ).fetchall()
        return [_row_to_conversation(r) for r in rows]

    @with_connection
    def update_title(self, conversation_id: str, title: str) -> None:
        conn = self._conn()
        conn.execute(
            """UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
            (title, conversation_id),
        )
        conn.commit()

    @with_connection
    def touch(self, conversation_id: str) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )
        conn.commit()

    @with_connection
    def delete(self, conversation_id: str) -> None:
        conn = self._conn()
        conn.execute(
            """DELETE FROM conversation_metrics
               WHERE message_id IN (
                    SELECT id FROM conversation_log WHERE conversation_id = ?
               )""",
            (conversation_id,),
        )
        conn.execute(
            "DELETE FROM conversation_log WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.execute(
            "DELETE FROM perception_sediment WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.execute(
            "DELETE FROM perception_files WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.execute(
            "DELETE FROM consolidation_checkpoints WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.execute(
            "DELETE FROM memory_nodes WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.execute(
            "DELETE FROM conversation_tags WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.execute(
            "DELETE FROM conversations WHERE id = ?",
            (conversation_id,),
        )
        conn.commit()

    @with_connection
    def get_tags(self, conversation_id: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT tag, tag_type FROM conversation_tags WHERE conversation_id = ? ORDER BY tag ASC",
            (conversation_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def add_tag(self, conversation_id: str, tag: str, tag_type: str) -> None:
        conn = self._conn()
        conn.execute(
            """INSERT OR IGNORE INTO conversation_tags (conversation_id, tag, tag_type)
               VALUES (?, ?, ?)""",
            (conversation_id, tag.strip(), tag_type),
        )
        conn.commit()

    @with_connection
    def remove_tag(self, conversation_id: str, tag: str) -> None:
        conn = self._conn()
        conn.execute(
            "DELETE FROM conversation_tags WHERE conversation_id = ? AND tag = ?",
            (conversation_id, tag.strip()),
        )
        conn.commit()

    @with_connection
    def get_all_unique_tags(self) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT DISTINCT tag, tag_type FROM conversation_tags ORDER BY tag ASC"
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def mark_requires_consolidation(self, conversation_id: str, requires: bool) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE conversations SET requires_consolidation = ? WHERE id = ?",
            (1 if requires else 0, conversation_id),
        )
        conn.commit()

    @with_connection
    def update_last_consolidated_at(self, conversation_id: str) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE conversations SET last_consolidated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )
        conn.commit()
