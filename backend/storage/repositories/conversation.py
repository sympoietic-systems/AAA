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
    def list_all(
        self,
        tag: Optional[str] = None,
        search: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[Conversation]:
        conn = self._conn()
        where_clauses = []
        params = []

        if tag:
            where_clauses.append("c.id IN (SELECT conversation_id FROM conversation_tags WHERE tag = ?)")
            params.append(tag)

        if search:
            where_clauses.append("c.title LIKE ?")
            params.append(f"%{search}%")

        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        query = f"""
            SELECT c.*, COUNT(cl.id) as message_count
            FROM conversations c
            LEFT JOIN conversation_log cl ON c.id = cl.conversation_id
            {where_str}
            GROUP BY c.id
            ORDER BY MAX(cl.timestamp) DESC
        """

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
            if offset is not None:
                query += " OFFSET ?"
                params.append(offset)

        rows = conn.execute(query, params).fetchall()
        return [_row_to_conversation(r) for r in rows]

    @with_connection
    def count_all(self, tag: Optional[str] = None, search: Optional[str] = None) -> int:
        conn = self._conn()
        where_clauses = []
        params = []

        if tag:
            where_clauses.append("c.id IN (SELECT conversation_id FROM conversation_tags WHERE tag = ?)")
            params.append(tag)

        if search:
            where_clauses.append("c.title LIKE ?")
            params.append(f"%{search}%")

        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        query = f"SELECT COUNT(*) FROM conversations c {where_str}"
        row = conn.execute(query, params).fetchone()
        return row[0] if row else 0

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

    @with_connection
    def get_recent_dreams(self, hours: int = 48) -> list[dict]:
        """Return recent dream conversations with their last message snippet and ID."""
        conn = self._conn()
        rows = conn.execute(
            """SELECT c.id, c.title, c.created_at, c.updated_at,
                      (SELECT COUNT(*) FROM conversation_log WHERE conversation_id = c.id) as msg_count,
                      (SELECT id FROM conversation_log WHERE conversation_id = c.id ORDER BY id DESC LIMIT 1) as last_msg_id,
                      (SELECT content FROM conversation_log WHERE conversation_id = c.id ORDER BY id DESC LIMIT 1) as last_snippet
               FROM conversations c
               LEFT JOIN conversation_tags t ON c.id = t.conversation_id AND t.tag_type = 'structural' AND t.tag = 'dreams'
               WHERE (t.tag IS NOT NULL OR c.title LIKE 'Dream Log:%' OR c.title LIKE 'Internal Diary:%')
                 AND (c.created_at > datetime('now', '-' || ? || ' hours')
                      OR c.updated_at > datetime('now', '-' || ? || ' hours'))
               ORDER BY c.updated_at DESC
               LIMIT 50""",
            (hours, hours),
        ).fetchall()
        return [dict(r) for r in rows]
