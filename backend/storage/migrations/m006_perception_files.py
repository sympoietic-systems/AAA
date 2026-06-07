import sqlite3


def up(conn):
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS perception_files (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id   TEXT NOT NULL,
                file_name         TEXT NOT NULL,
                file_type         TEXT NOT NULL,
                status            TEXT NOT NULL DEFAULT 'uploading' CHECK (status IN ('uploading', 'processing', 'ready', 'error')),
                summary           TEXT,
                summary_model     TEXT,
                token_count       INTEGER DEFAULT 0,
                chunk_count       INTEGER DEFAULT 0,
                created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                UNIQUE(conversation_id, file_name)
            )
        """)
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pf_conv ON perception_files(conversation_id)")
    except sqlite3.OperationalError:
        pass

    for col, col_type in [
        ("interference_score", "REAL DEFAULT 0.0"),
        ("belief_nodes_implicated", "TEXT"),
        ("state_vector_impact", "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE perception_files ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass
