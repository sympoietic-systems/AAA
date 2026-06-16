"""Repository for research_plans table."""

from datetime import datetime, timezone
from typing import Optional

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


class ResearchPlanRepository(BaseRepository):
    @with_connection
    def create(self, plan: dict) -> str:
        conn = self._conn()
        conn.execute(
            """INSERT INTO research_plans (
                id, task_id, plan_json, status, created_at
            ) VALUES (?, ?, ?, ?, ?)""",
            (
                plan["id"],
                plan["task_id"],
                plan["plan_json"],
                plan.get("status", "draft"),
                plan.get("created_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        return plan["id"]

    @with_connection
    def get(self, plan_id: str) -> Optional[dict]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM research_plans WHERE id = ?", (plan_id,)
        ).fetchone()
        return dict(row) if row else None

    @with_connection
    def get_by_task(self, task_id: str) -> Optional[dict]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM research_plans WHERE task_id = ? ORDER BY created_at DESC LIMIT 1",
            (task_id,),
        ).fetchone()
        return dict(row) if row else None

    @with_connection
    def update_status(self, plan_id: str, status: str) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE research_plans SET status = ? WHERE id = ?",
            (status, plan_id),
        )
        conn.commit()
