import json
import sqlite3
import traceback
from datetime import datetime
from typing import Optional

from .database import get_connection
from .models import ErrorLogEntry, Message


class MessageRepository:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return get_connection(self._db_path)

    def insert(
        self,
        speaker: str,
        content: str,
        embedding: bytes,
        embedding_model: str,
        embedding_dim: int,
        thinking: Optional[str] = None,
        agent_id: str = "",
    ) -> Message:
        conn = self._conn()
        conn.execute(
            """INSERT INTO conversation_log
               (agent_id, speaker, content, thinking, embedding, embedding_model, embedding_dim)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (agent_id, speaker, content, thinking, embedding, embedding_model, embedding_dim),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM conversation_log WHERE id = last_insert_rowid()"
        ).fetchone()
        return _row_to_message(row)

    def get_recent(self, limit: int = 50) -> list[Message]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM conversation_log ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_message(r) for r in reversed(rows)]

    def get_by_id(self, message_id: int) -> Optional[Message]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM conversation_log WHERE id = ?", (message_id,)
        ).fetchone()
        if row is None:
            return None
        return _row_to_message(row)


def _row_to_message(row: sqlite3.Row) -> Message:
    return Message(
        id=row["id"],
        timestamp=datetime.fromisoformat(row["timestamp"]),
        agent_id=row["agent_id"] if "agent_id" in row.keys() else "",
        speaker=row["speaker"],
        content=row["content"],
        thinking=row["thinking"] if "thinking" in row.keys() else None,
        embedding=row["embedding"],
        embedding_model=row["embedding_model"],
        embedding_dim=row["embedding_dim"],
    )


class ErrorLogRepository:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return get_connection(self._db_path)

    def log_error(
        self,
        module: str,
        error: Exception,
        context: Optional[dict] = None,
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
        row = conn.execute(
            "SELECT * FROM error_log WHERE id = last_insert_rowid()"
        ).fetchone()
        return ErrorLogEntry(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            module=row["module"],
            error_type=row["error_type"],
            error_message=row["error_message"],
            traceback=row["traceback"],
            context=row["context"],
        )

    def get_recent(self, limit: int = 20) -> list[ErrorLogEntry]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM error_log ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
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
