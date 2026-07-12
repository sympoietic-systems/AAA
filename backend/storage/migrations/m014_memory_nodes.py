import contextlib
import sqlite3


def up(conn):
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_nodes (
                id                TEXT PRIMARY KEY,
                conversation_id   TEXT NOT NULL,
                checkpoint_id     INTEGER NOT NULL,
                node_type         TEXT NOT NULL DEFAULT 'concept',
                intensity         REAL NOT NULL DEFAULT 0.5,
                scar              TEXT DEFAULT '',
                glitch_potential  REAL NOT NULL DEFAULT 0.0,
                intra_active_text TEXT NOT NULL,
                surface_fragment  TEXT DEFAULT '',
                agential_symmetry TEXT DEFAULT 'negotiated',
                diffractive_key   TEXT DEFAULT '',
                tendril_ids       TEXT DEFAULT '[]',
                created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                FOREIGN KEY (checkpoint_id) REFERENCES consolidation_checkpoints(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mn_conv ON memory_nodes(conversation_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mn_type ON memory_nodes(node_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mn_intensity ON memory_nodes(intensity)")
    except sqlite3.OperationalError:
        pass

    for sql in [
        "ALTER TABLE conversations ADD COLUMN requires_consolidation INTEGER DEFAULT 0",
        "ALTER TABLE conversations ADD COLUMN last_consolidated_at DATETIME",
        "ALTER TABLE conversation_log ADD COLUMN metabolized INTEGER DEFAULT 0",
    ]:
        with contextlib.suppress(sqlite3.OperationalError):
            conn.execute(sql)
