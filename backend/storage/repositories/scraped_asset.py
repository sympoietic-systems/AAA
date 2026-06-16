"""Repository for scraped_assets table — harvested web content."""

from datetime import datetime, timezone
from typing import Optional

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


class ScrapedAssetRepository(BaseRepository):
    @with_connection
    def create(self, asset: dict) -> str:
        conn = self._conn()
        conn.execute(
            """INSERT INTO scraped_assets (
                id, branch_id, task_id, url, raw_markdown,
                relevance_score, novelty_score, diffractive_score,
                memory_node_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                asset["id"],
                asset["branch_id"],
                asset["task_id"],
                asset["url"],
                asset["raw_markdown"],
                asset.get("relevance_score", 0.0),
                asset.get("novelty_score", 0.0),
                asset.get("diffractive_score", 0.0),
                asset.get("memory_node_id"),
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        return asset["id"]

    @with_connection
    def get(self, asset_id: str) -> Optional[dict]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM scraped_assets WHERE id = ?", (asset_id,)
        ).fetchone()
        return dict(row) if row else None

    @with_connection
    def get_by_branch(self, branch_id: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM scraped_assets WHERE branch_id = ? ORDER BY created_at",
            (branch_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def get_by_task(self, task_id: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM scraped_assets WHERE task_id = ? ORDER BY created_at",
            (task_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def get_by_node(self, memory_node_id: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM scraped_assets WHERE memory_node_id = ?",
            (memory_node_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def count_by_task(self, task_id: str) -> int:
        conn = self._conn()
        row = conn.execute(
            "SELECT COUNT(*) FROM scraped_assets WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        return row[0] if row else 0
