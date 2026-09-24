"""Message repository graph collaborator."""

from backend.storage.connection import with_connection
from backend.storage.models import Message, MessageLink
from backend.storage.repositories.base import BaseRepository
from backend.storage.row_mappers import _row_to_message, _row_to_message_link


class MessageGraphRepository(BaseRepository):
    @with_connection
    def _normalize_legacy_links(self) -> None:
        conn = self._conn()
        try:
            # Delete duplicates where source_id > target_id and the correctly-ordered version exists
            conn.execute(
                """DELETE FROM message_links
                   WHERE source_id > target_id
                   AND (target_id || '_' || source_id || '_' || link_type) IN (SELECT id FROM message_links)"""
            )
            # Update remaining reversed links to be correctly ordered
            conn.execute(
                """UPDATE message_links
                   SET id = target_id || '_' || source_id || '_' || link_type,
                       source_id = target_id,
                       target_id = source_id
                   WHERE source_id > target_id"""
            )
            conn.commit()
        except Exception:
            # Table might not exist yet during migrations, ignore if so
            pass

    @with_connection
    def get_ancestor_path(self, message_id: int, limit: int = 100) -> list[Message]:
        conn = self._conn()
        rows = conn.execute(
            """
            WITH RECURSIVE ancestors AS (
                SELECT * FROM conversation_log WHERE id = ?
                UNION ALL
                SELECT cl.* FROM conversation_log cl
                JOIN ancestors a ON cl.id = a.parent_message_id
            )
            SELECT * FROM ancestors LIMIT ?
            """,
            (message_id, limit),
        ).fetchall()
        return [_row_to_message(r) for r in reversed(rows)]

    @with_connection
    def link_exists(self, msg_a: int, msg_b: int, link_type: str = "resonance") -> bool:
        conn = self._conn()
        link_id = f"{min(msg_a, msg_b)}_{max(msg_a, msg_b)}_{link_type}"
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM message_links WHERE id = ?",
            (link_id,),
        ).fetchone()
        return row["cnt"] > 0 if row else False

    @with_connection
    def add_message_link(
        self,
        source_id: int,
        target_id: int,
        link_type: str = "resonance",
        status: str = "active",
        justification: str = "",
    ) -> MessageLink:
        conn = self._conn()
        # Consistent undirected link_id ordering to prevent duplicates/cross-talk
        link_id = f"{min(source_id, target_id)}_{max(source_id, target_id)}_{link_type}"
        conn.execute(
            """INSERT INTO message_links (id, source_id, target_id, link_type, status, justification)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   status = CASE
                       WHEN excluded.status = 'proposed' AND message_links.status IN ('active', 'ignored') THEN message_links.status
                       ELSE excluded.status
                   END,
                   justification = CASE
                       WHEN excluded.status = 'proposed' AND message_links.status IN ('active', 'ignored') THEN message_links.justification
                       ELSE excluded.justification
                   END""",
            (link_id, source_id, target_id, link_type, status, justification),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM message_links WHERE id = ?",
            (link_id,),
        ).fetchone()
        return _row_to_message_link(row)

    @with_connection
    def confirm_message_link(self, link_id: str) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE message_links SET status = 'active' WHERE id = ?",
            (link_id,),
        )
        conn.commit()

    @with_connection
    def delete_message_link(self, link_id: str) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE message_links SET status = 'ignored' WHERE id = ?",
            (link_id,),
        )
        conn.commit()

    @with_connection
    def get_message_links(self, conversation_id: str) -> list[MessageLink]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT ml.* FROM message_links ml
               JOIN conversation_log cl_src ON ml.source_id = cl_src.id
               JOIN conversation_log cl_tgt ON ml.target_id = cl_tgt.id
               WHERE cl_src.conversation_id = ? AND cl_tgt.conversation_id = ?
                 AND ml.status != 'ignored'""",
            (conversation_id, conversation_id),
        ).fetchall()
        return [_row_to_message_link(r) for r in rows]
