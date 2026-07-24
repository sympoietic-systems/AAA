from datetime import datetime
from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


class DailySummaryRepository(BaseRepository):
    @with_connection
    def get_by_date(self, date_str: str) -> dict | None:
        conn = self._conn()
        row = conn.execute(
            """SELECT date, summary, metrics_json, created_at, updated_at
               FROM daily_summaries
               WHERE date = ?""",
            (date_str,),
        ).fetchone()
        if row:
            return dict(row)
        return None

    @with_connection
    def upsert_summary(self, date_str: str, summary: str, metrics_json: str = "{}") -> None:
        conn = self._conn()
        conn.execute(
            """INSERT INTO daily_summaries (date, summary, metrics_json, updated_at)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(date) DO UPDATE SET
                   summary = excluded.summary,
                   metrics_json = excluded.metrics_json,
                   updated_at = CURRENT_TIMESTAMP""",
            (date_str, summary, metrics_json),
        )
        conn.commit()

    @with_connection
    def list_summarized_dates(self) -> set[str]:
        conn = self._conn()
        rows = conn.execute("SELECT date FROM daily_summaries").fetchall()
        return {r["date"] for r in rows}
