import sqlite3


def up(conn):
    for sql in [
        "ALTER TABLE belief_nodes ADD COLUMN lifecycle_stage TEXT DEFAULT 'crystallized'",
        "ALTER TABLE belief_nodes ADD COLUMN last_reinforced_at DATETIME",
        "ALTER TABLE belief_nodes ADD COLUMN last_dreamed_at DATETIME",
    ]:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass

    conn.execute(
        "UPDATE belief_nodes SET lifecycle_stage = 'collapsed' WHERE origin = 'collapsed' AND lifecycle_stage = 'crystallized'"
    )
    conn.execute(
        "UPDATE belief_nodes SET last_reinforced_at = updated_at WHERE last_reinforced_at IS NULL"
    )

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS belief_tensions (
                belief_a_id TEXT NOT NULL,
                belief_b_id TEXT NOT NULL,
                cosine_similarity REAL NOT NULL,
                tension_magnitude REAL NOT NULL,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (belief_a_id, belief_b_id),
                FOREIGN KEY (belief_a_id) REFERENCES belief_nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (belief_b_id) REFERENCES belief_nodes(id) ON DELETE CASCADE
            )
        """)
    except sqlite3.OperationalError:
        pass
