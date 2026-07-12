import sqlite3


def up(conn):
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sediment_injections (
                id                    TEXT PRIMARY KEY,
                source_conversation_id TEXT NOT NULL,
                source_file_name      TEXT NOT NULL,
                target_conversation_id TEXT NOT NULL,
                injected_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_conversation_id) REFERENCES conversations(id),
                FOREIGN KEY (target_conversation_id) REFERENCES conversations(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_si_target ON sediment_injections(target_conversation_id)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_si_source ON sediment_injections(source_conversation_id, source_file_name)"
        )
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_tags (
                conversation_id TEXT NOT NULL,
                tag             TEXT NOT NULL,
                tag_type        TEXT NOT NULL,
                PRIMARY KEY (conversation_id, tag),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ct_conv ON conversation_tags(conversation_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ct_tag ON conversation_tags(tag)")
    except sqlite3.OperationalError:
        pass
