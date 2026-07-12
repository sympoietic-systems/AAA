import contextlib
import sqlite3


def up(conn):
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS perception_sediment (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id   TEXT NOT NULL,
                file_name         TEXT NOT NULL,
                file_type         TEXT NOT NULL,
                chunk_index       INTEGER NOT NULL,
                chunk_text        TEXT NOT NULL,
                embedding         BLOB NOT NULL,
                embedding_model   TEXT NOT NULL,
                token_count       INTEGER NOT NULL,
                created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                opacity           INTEGER DEFAULT 0,
                opacity_meta      TEXT,
                structural_signature BLOB,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ps_conv ON perception_sediment(conversation_id)")
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ps_file ON perception_sediment(conversation_id, file_name)")

    for col, col_type in [
        ("opacity", "INTEGER DEFAULT 0"),
        ("opacity_meta", "TEXT"),
    ]:
        with contextlib.suppress(sqlite3.OperationalError):
            conn.execute(f"ALTER TABLE perception_sediment ADD COLUMN {col} {col_type}")
