import contextlib
import sqlite3


def up(conn):
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS consolidation_checkpoints (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id   TEXT NOT NULL,
                message_count     INTEGER NOT NULL,
                summary           TEXT NOT NULL,
                model             TEXT NOT NULL DEFAULT '',
                created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cc_conv ON consolidation_checkpoints(conversation_id)")
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("ALTER TABLE consolidation_checkpoints ADD COLUMN human_summary TEXT DEFAULT ''")
