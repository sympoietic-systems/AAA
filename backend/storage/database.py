import os
import sqlite3
from pathlib import Path


def get_db_path(db_path: str) -> Path:
    path = Path(db_path)
    if not path.is_absolute():
        path = Path(__file__).parent.parent / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> sqlite3.Connection:
    """Initialize database. Migrations run only when AAA_RUN_MIGRATIONS=true."""
    conn = get_connection(db_path)

    _cleanup_invalid_conversations(conn)

    if os.environ.get("AAA_RUN_MIGRATIONS", "").lower() not in ("true", "1", "yes"):
        return conn

    from backend.storage.migrations import run_all_migrations

    run_all_migrations(conn)
    _migrate_legacy_conversation(conn)
    _cleanup_invalid_conversations(conn)
    conn.commit()
    return conn


def _cleanup_invalid_conversations(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("DELETE FROM conversations WHERE id IS NULL OR id = ''")
        conn.commit()
    except sqlite3.OperationalError:
        pass


_LEGACY_CONVERSATION_ID = "00000000-0000-0000-0000-000000000000"


def _migrate_legacy_conversation(conn: sqlite3.Connection) -> None:
    orphan_count = conn.execute("SELECT COUNT(*) FROM conversation_log WHERE conversation_id = ''").fetchone()[0]

    if orphan_count == 0:
        return

    conn.execute(
        """INSERT OR IGNORE INTO conversations (id, title, agent_id)
           VALUES (?, ?, ?)""",
        (_LEGACY_CONVERSATION_ID, "Legacy", ""),
    )

    conn.execute(
        "UPDATE conversation_log SET conversation_id = ? WHERE conversation_id = ''",
        (_LEGACY_CONVERSATION_ID,),
    )
