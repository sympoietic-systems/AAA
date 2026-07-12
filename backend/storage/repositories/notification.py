import uuid
from datetime import datetime
from typing import Any

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


class NotificationRepository(BaseRepository):
    @with_connection
    def create(
        self,
        type: str,
        snippet: str,
        id: str | None = None,
        timestamp: str | None = None,
        conversation_id: str | None = None,
        message_id: int | None = None,
        parent_message_id: int | None = None,
        speaker: str | None = None,
        source: str | None = None,
        read: int = 0,
        dismissed: int = 0,
        source_type: str | None = None,
        source_id: str | None = None,
    ) -> dict[str, Any]:
        conn = self._conn()
        notif_id = id or str(uuid.uuid4())
        ts = timestamp or datetime.utcnow().isoformat()

        conn.execute(
            """INSERT INTO notifications (
                id, type, timestamp, snippet, conversation_id, message_id,
                parent_message_id, speaker, source, read, dismissed,
                source_type, source_id
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                notif_id,
                type,
                ts,
                snippet,
                conversation_id,
                message_id,
                parent_message_id,
                speaker,
                source,
                read,
                dismissed,
                source_type,
                source_id,
            ),
        )
        conn.commit()
        return self.get(notif_id)

    @with_connection
    def get(self, id: str) -> dict[str, Any] | None:
        conn = self._conn()
        row = conn.execute("SELECT * FROM notifications WHERE id = ?", (id,)).fetchone()
        if not row:
            return None
        return dict(row)

    @with_connection
    def list_active(self, limit: int = 100) -> list[dict[str, Any]]:
        """List un-dismissed notifications."""
        conn = self._conn()
        rows = conn.execute(
            """SELECT * FROM notifications
               WHERE dismissed = 0
               ORDER BY timestamp DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        dismissed: bool | None = None,
        type_filter: str | None = None,
        search_query: str | None = None,
    ) -> list[dict[str, Any]]:
        """List all notifications with filters and paging."""
        conn = self._conn()
        query = "SELECT * FROM notifications WHERE 1=1"
        params = []

        if dismissed is not None:
            query += " AND dismissed = ?"
            params.append(1 if dismissed else 0)

        if type_filter:
            query += " AND type = ?"
            params.append(type_filter)

        if search_query:
            query += " AND (snippet LIKE ? OR source LIKE ?)"
            params.append(f"%{search_query}%")
            params.append(f"%{search_query}%")

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def mark_as_read(self, id: str) -> dict[str, Any] | None:
        conn = self._conn()
        conn.execute("UPDATE notifications SET read = 1 WHERE id = ?", (id,))
        conn.commit()
        return self.get(id)

    @with_connection
    def mark_as_unread(self, id: str) -> dict[str, Any] | None:
        conn = self._conn()
        conn.execute("UPDATE notifications SET read = 0 WHERE id = ?", (id,))
        conn.commit()
        return self.get(id)

    @with_connection
    def mark_all_as_read(self, type_filter: str | None = None) -> None:
        conn = self._conn()
        if type_filter:
            conn.execute(
                "UPDATE notifications SET read = 1 WHERE type = ?",
                (type_filter,),
            )
        else:
            conn.execute("UPDATE notifications SET read = 1")
        conn.commit()

    @with_connection
    def dismiss(self, id: str) -> dict[str, Any] | None:
        conn = self._conn()
        conn.execute("UPDATE notifications SET dismissed = 1 WHERE id = ?", (id,))
        conn.commit()
        return self.get(id)

    @with_connection
    def dismiss_by_match(self, conversation_id: str, message_id: int) -> None:
        conn = self._conn()
        conn.execute(
            """UPDATE notifications SET dismissed = 1
               WHERE conversation_id = ? AND message_id = ?""",
            (conversation_id, message_id),
        )
        conn.commit()

    @with_connection
    def clear_by_type(self, type_filter: str) -> None:
        """Dismiss all notifications of a specific type."""
        conn = self._conn()
        conn.execute(
            "UPDATE notifications SET dismissed = 1 WHERE type = ?",
            (type_filter,),
        )
        conn.commit()

    @with_connection
    def clear_all(self) -> None:
        """Dismiss all notifications."""
        conn = self._conn()
        conn.execute("UPDATE notifications SET dismissed = 1")
        conn.commit()
