import sqlite3


def up(conn):
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS semantic_knots (
                id                TEXT PRIMARY KEY,
                conversation_id   TEXT NOT NULL,
                created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                weight            REAL NOT NULL DEFAULT 1.0,
                concept_payload   TEXT NOT NULL,
                embedding         BLOB NOT NULL,
                embedding_model   TEXT NOT NULL,
                token_count       INTEGER NOT NULL,
                structural_signature BLOB,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sk_conv ON semantic_knots(conversation_id)")
    except sqlite3.OperationalError:
        pass
