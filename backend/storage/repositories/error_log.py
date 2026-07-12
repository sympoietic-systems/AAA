import json
import traceback

from backend.storage.connection import with_connection
from backend.storage.models import ErrorLogEntry
from backend.storage.repositories.base import BaseRepository


class ErrorLogRepository(BaseRepository):
    @with_connection
    def log_error(
        self,
        module: str,
        error: Exception,
        context: dict | None = None,
    ) -> ErrorLogEntry:
        conn = self._conn()
        conn.execute(
            """INSERT INTO error_log (module, error_type, error_message, traceback, context)
               VALUES (?, ?, ?, ?, ?)""",
            (
                module,
                type(error).__name__,
                str(error),
                traceback.format_exc(),
                json.dumps(context) if context else None,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM error_log WHERE id = last_insert_rowid()").fetchone()
        from datetime import datetime as _dt

        return ErrorLogEntry(
            id=row["id"],
            timestamp=_dt.fromisoformat(row["timestamp"]),
            module=row["module"],
            error_type=row["error_type"],
            error_message=row["error_message"],
            traceback=row["traceback"],
            context=row["context"],
        )

    @with_connection
    def get_recent(self, limit: int = 20) -> list[ErrorLogEntry]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM error_log ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        from datetime import datetime

        return [
            ErrorLogEntry(
                id=r["id"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
                module=r["module"],
                error_type=r["error_type"],
                error_message=r["error_message"],
                traceback=r["traceback"],
                context=r["context"],
            )
            for r in rows
        ]
