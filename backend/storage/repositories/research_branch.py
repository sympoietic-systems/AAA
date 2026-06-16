"""Repository for research_branches table — recursive tree traversal nodes."""

from datetime import datetime, timezone
from typing import Optional

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


class ResearchBranchRepository(BaseRepository):
    @with_connection
    def create(self, branch: dict) -> str:
        conn = self._conn()
        conn.execute(
            """INSERT INTO research_branches (
                id, task_id, conversation_id, parent_branch_id,
                query, goal, depth, breadth, status,
                vector_16d, homeostatic_tension, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                branch["id"],
                branch["task_id"],
                branch["conversation_id"],
                branch.get("parent_branch_id"),
                branch["query"],
                branch["goal"],
                branch["depth"],
                branch["breadth"],
                branch.get("status", "probing"),
                branch.get("vector_16d"),
                branch.get("homeostatic_tension", 0.0),
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        return branch["id"]

    @with_connection
    def get(self, branch_id: str) -> Optional[dict]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM research_branches WHERE id = ?", (branch_id,)
        ).fetchone()
        return dict(row) if row else None

    @with_connection
    def get_by_task(self, task_id: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM research_branches WHERE task_id = ? ORDER BY depth, created_at",
            (task_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def get_by_parent(self, parent_branch_id: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM research_branches WHERE parent_branch_id = ?",
            (parent_branch_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def update(self, branch_id: str, **fields) -> None:
        if not fields:
            return
        conn = self._conn()
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [branch_id]
        conn.execute(
            f"UPDATE research_branches SET {set_clause} WHERE id = ?", values
        )
        conn.commit()

    @with_connection
    def count_by_task_and_status(self, task_id: str, status: str) -> int:
        conn = self._conn()
        row = conn.execute(
            "SELECT COUNT(*) FROM research_branches WHERE task_id = ? AND status = ?",
            (task_id, status),
        ).fetchone()
        return row[0] if row else 0

    @with_connection
    def get_active_by_task(self, task_id: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT * FROM research_branches
               WHERE task_id = ? AND status = 'probing'
               ORDER BY depth ASC, created_at ASC""",
            (task_id,),
        ).fetchall()
        return [dict(r) for r in rows]
