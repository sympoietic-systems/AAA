from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


class DreamLogRepository(BaseRepository):
    @with_connection
    def log_dream(
        self,
        conversation_id: str,
        action: str,
        prompt_msg_id: int,
        response_msg_id: int,
        turns: int = 1,
        trigger_reason: str = "",
        source_conversation_id: str = "",
    ) -> int:
        conn = self._conn()
        cursor = conn.execute(
            """INSERT INTO dream_log
               (conversation_id, action, prompt_msg_id, response_msg_id, turns,
                trigger_reason, source_conversation_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (conversation_id, action, prompt_msg_id, response_msg_id, turns, trigger_reason, source_conversation_id),
        )
        conn.commit()
        return cursor.lastrowid

    @with_connection
    def get_recent(self, limit: int = 24) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT dl.id, dl.conversation_id, dl.action, dl.response_msg_id, dl.turns, dl.timestamp,
                      dl.trigger_reason, dl.source_conversation_id,
                      c.title,
                      (SELECT COUNT(*) FROM conversation_log WHERE conversation_id = dl.conversation_id) as msg_count,
                      (SELECT content FROM conversation_log WHERE id = dl.response_msg_id) as last_snippet
               FROM dream_log dl
               JOIN conversations c ON dl.conversation_id = c.id
               ORDER BY dl.timestamp DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
