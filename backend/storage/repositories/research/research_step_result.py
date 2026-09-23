"""Repository for research_step_results table."""

from datetime import UTC, datetime

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


class ResearchStepResultRepository(BaseRepository):
    @with_connection
    def create(self, result: dict) -> str:
        conn = self._conn()
        conn.execute(
            """INSERT INTO research_step_results (
                id, step_id, task_id, source_url, source_title,
                raw_content, analyzed_json, relevance_score, novelty_score,
                raw_file_path, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result["id"],
                result["step_id"],
                result["task_id"],
                result.get("source_url"),
                result.get("source_title"),
                result.get("raw_content"),
                result.get("analyzed_json"),
                result.get("relevance_score", 0.0),
                result.get("novelty_score", 0.0),
                result.get("raw_file_path"),
                result.get("created_at") or datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        return result["id"]

    @with_connection
    def get_by_step(self, step_id: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM research_step_results WHERE step_id = ? ORDER BY relevance_score DESC",
            (step_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def get_by_task(self, task_id: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM research_step_results WHERE task_id = ? ORDER BY created_at ASC",
            (task_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def update_analysis(self, result_id: str, analyzed_json: str) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE research_step_results SET analyzed_json = ? WHERE id = ?",
            (analyzed_json, result_id),
        )
        conn.commit()
