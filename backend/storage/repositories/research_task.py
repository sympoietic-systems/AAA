"""Repository for research_tasks table — autonomous research task lifecycle."""

from datetime import datetime, timezone
from typing import Optional

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


class ResearchTaskRepository(BaseRepository):
    @with_connection
    def create(self, task: dict) -> str:
        conn = self._conn()
        conn.execute(
            """INSERT INTO research_tasks (
                id, title, objective, trigger_source, status, priority,
                conversation_id, max_depth, max_breadth, is_agonistic,
                budget_limit_usd, proposal_rationale, proposal_message_id,
                proposed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task["id"],
                task["title"],
                task["objective"],
                task["trigger_source"],
                task.get("status", "proposed"),
                task.get("priority", 2),
                task.get("conversation_id"),
                task.get("max_depth", 3),
                task.get("max_breadth", 4),
                1 if task.get("is_agonistic") else 0,
                task.get("budget_limit_usd", 0.50),
                task.get("proposal_rationale"),
                task.get("proposal_message_id"),
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        return task["id"]

    @with_connection
    def get(self, task_id: str) -> Optional[dict]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM research_tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return dict(row) if row else None

    @with_connection
    def list_all(
        self,
        status: Optional[str] = None,
        trigger_source: Optional[str] = None,
        conversation_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        conn = self._conn()
        query = "SELECT * FROM research_tasks WHERE 1=1"
        params: list = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if trigger_source:
            query += " AND trigger_source = ?"
            params.append(trigger_source)
        if conversation_id:
            query += " AND conversation_id = ?"
            params.append(conversation_id)

        query += " ORDER BY proposed_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def update(self, task_id: str, **fields) -> None:
        if not fields:
            return
        conn = self._conn()
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [task_id]
        conn.execute(
            f"UPDATE research_tasks SET {set_clause} WHERE id = ?", values
        )
        conn.commit()

    @with_connection
    def transition_status(self, task_id: str, new_status: str) -> None:
        conn = self._conn()
        timestamp_col = {
            "approved": "approved_at",
            "active": "started_at",
            "completed": "completed_at",
        }.get(new_status)

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        if timestamp_col:
            conn.execute(
                f"UPDATE research_tasks SET status = ?, {timestamp_col} = ? WHERE id = ?",
                (new_status, now, task_id),
            )
        else:
            conn.execute(
                "UPDATE research_tasks SET status = ? WHERE id = ?",
                (new_status, task_id),
            )
        conn.commit()

    @with_connection
    def count_by_status(self, status: str) -> int:
        conn = self._conn()
        row = conn.execute(
            "SELECT COUNT(*) FROM research_tasks WHERE status = ?", (status,)
        ).fetchone()
        return row[0] if row else 0

    @with_connection
    def get_next_queued(self) -> Optional[dict]:
        conn = self._conn()
        row = conn.execute(
            """SELECT * FROM research_tasks
               WHERE status = 'queued'
               ORDER BY priority ASC, proposed_at ASC
               LIMIT 1""",
        ).fetchone()
        return dict(row) if row else None

    @with_connection
    def has_active_for_conversation(self, conversation_id: str) -> bool:
        conn = self._conn()
        row = conn.execute(
            """SELECT COUNT(*) FROM research_tasks
               WHERE conversation_id = ?
               AND status IN ('queued', 'active')""",
            (conversation_id,),
        ).fetchone()
        return row[0] > 0 if row else False

    @with_connection
    def expire_stale_proposals(
        self, conversation_timeout_mins: int = 60, daemon_timeout_mins: int = 600
    ) -> int:
        conn = self._conn()
        cursor = conn.execute(
            """UPDATE research_tasks SET status = 'expired'
               WHERE status = 'proposed'
               AND (
                   (trigger_source LIKE 'user_%' AND proposed_at < datetime('now', ?))
                   OR
                   (trigger_source LIKE 'symbia_%' AND proposed_at < datetime('now', ?))
               )""",
            (
                f"-{conversation_timeout_mins} minutes",
                f"-{daemon_timeout_mins} minutes",
            ),
        )
        conn.commit()
        return cursor.rowcount

    @with_connection
    def delete(self, task_id: str) -> None:
        """Delete a task. CASCADE handles branches, assets, plans, steps, meta log."""
        conn = self._conn()
        conn.execute("DELETE FROM research_tasks WHERE id = ?", (task_id,))
        conn.commit()
