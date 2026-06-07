import sqlite3


def up(conn):
    try:
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
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cc_conv ON consolidation_checkpoints(conversation_id)")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE consolidation_checkpoints ADD COLUMN human_summary TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
