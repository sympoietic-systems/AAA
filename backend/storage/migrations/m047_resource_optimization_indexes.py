import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_notifications_dismissed_ts
            ON notifications(dismissed, timestamp DESC);

        CREATE INDEX IF NOT EXISTS idx_notifications_type
            ON notifications(type);

        CREATE INDEX IF NOT EXISTS idx_conversation_log_sig
            ON conversation_log(structural_signature);

        CREATE INDEX IF NOT EXISTS idx_conversation_log_agent_ts
            ON conversation_log(agent_id, timestamp DESC);
    """)
