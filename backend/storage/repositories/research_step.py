"""Repository for research_steps table."""

from datetime import datetime, timezone
from typing import Optional

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


class ResearchStepRepository(BaseRepository):
    @with_connection
    def create(self, step: dict) -> str:
        conn = self._conn()
        conn.execute(
            """INSERT INTO research_steps (
                id, task_id, plan_id, step_number, step_type,
                step_data, status, result_summary, started_at, completed_at, created_at,
                query_group, query_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                step["id"],
                step["task_id"],
                step["plan_id"],
                step["step_number"],
                step["step_type"],
                step.get("step_data", "{}"),
                step.get("status", "pending"),
                step.get("result_summary"),
                step.get("started_at"),
                step.get("completed_at"),
                step.get("created_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                step.get("query_group"),
                step.get("query_text"),
            ),
        )
        conn.commit()
        return step["id"]

    @with_connection
    def get(self, step_id: str) -> Optional[dict]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM research_steps WHERE id = ?", (step_id,)
        ).fetchone()
        return dict(row) if row else None

    @with_connection
    def get_by_task(self, task_id: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM research_steps WHERE task_id = ? ORDER BY step_number ASC",
            (task_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def get_by_plan(self, plan_id: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM research_steps WHERE plan_id = ? ORDER BY step_number ASC",
            (plan_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def update(self, step_id: str, **kwargs) -> None:
        allowed = {"status", "result_summary", "started_at", "completed_at", "step_data", "rerun_version", "query_group", "query_text"}
        updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not updates:
            return
        conn = self._conn()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [step_id]
        conn.execute(f"UPDATE research_steps SET {set_clause} WHERE id = ?", values)
        conn.commit()

    @with_connection
    def mark_downstream_stale(self, task_id: str, after_step_number: int) -> int:
        """Set all steps with step_number > after_step_number to 'stale'.
        Returns count of affected rows."""
        conn = self._conn()
        cur = conn.execute(
            """UPDATE research_steps SET status = 'stale'
               WHERE task_id = ? AND step_number > ? AND status = 'completed'""",
            (task_id, after_step_number),
        )
        conn.commit()
        return cur.rowcount

    @with_connection
    def delete_downstream(self, task_id: str, after_step_number: int, exclude_types: tuple[str, ...] = ()) -> int:
        """Delete all steps with step_number > after_step_number.
        Used when rerunning a step — downstream must be re-created.
        Optionally exclude certain step_types from deletion.
        Returns count of deleted rows."""
        conn = self._conn()
        if exclude_types:
            placeholders = ", ".join("?" * len(exclude_types))
            cur = conn.execute(
                f"DELETE FROM research_steps WHERE task_id = ? AND step_number > ? AND step_type NOT IN ({placeholders})",
                (task_id, after_step_number, *exclude_types),
            )
        else:
            cur = conn.execute(
                "DELETE FROM research_steps WHERE task_id = ? AND step_number > ?",
                (task_id, after_step_number),
            )
        conn.commit()
        return cur.rowcount
