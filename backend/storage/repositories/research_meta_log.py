"""Repository for research_meta_log table — traceability/debug log."""

from datetime import datetime, timezone
from typing import Optional

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


class ResearchMetaLogRepository(BaseRepository):
    @with_connection
    def create(self, entry: dict) -> str:
        conn = self._conn()
        conn.execute(
            """INSERT INTO research_meta_log (
                id, task_id, branch_id, step_id, event_type, event_data, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                entry["id"],
                entry["task_id"],
                entry.get("branch_id"),
                entry.get("step_id"),
                entry["event_type"],
                entry["event_data"],
                entry.get("created_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        return entry["id"]

    @with_connection
    def get_by_task(self, task_id: str, limit: int = 200) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT id, task_id, branch_id, event_type, event_data, created_at
               FROM research_meta_log
               WHERE task_id = ?
               ORDER BY created_at ASC
               LIMIT ?""",
            (task_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def get_by_branch(self, branch_id: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT id, task_id, branch_id, step_id, event_type, event_data, created_at
               FROM research_meta_log
               WHERE branch_id = ?
               ORDER BY created_at ASC""",
            (branch_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def get_by_step(self, step_id: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT id, task_id, branch_id, step_id, event_type, event_data, created_at
               FROM research_meta_log
               WHERE step_id = ?
               ORDER BY created_at ASC""",
            (step_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def count_by_task(self, task_id: str) -> int:
        conn = self._conn()
        row = conn.execute(
            "SELECT COUNT(*) FROM research_meta_log WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        return row[0] if row else 0
