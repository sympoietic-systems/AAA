import sqlite3


def up(conn):
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_notes (
                id                TEXT PRIMARY KEY,
                conversation_id   TEXT NOT NULL,
                message_id        INTEGER NOT NULL,
                selected_text     TEXT NOT NULL,
                comment           TEXT DEFAULT '',
                visibility        TEXT NOT NULL DEFAULT 'personal',
                created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                FOREIGN KEY (message_id) REFERENCES conversation_log(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cn_conv ON conversation_notes(conversation_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cn_msg ON conversation_notes(message_id)")
    except sqlite3.OperationalError:
        pass
