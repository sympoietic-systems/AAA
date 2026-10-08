"""Persist reversible response quality without altering message content."""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.execute("ALTER TABLE conversation_log ADD COLUMN quality_status TEXT NOT NULL DEFAULT 'unassessed'")
    conn.execute("ALTER TABLE conversation_log ADD COLUMN quality_receipt TEXT")
    conn.execute("CREATE INDEX idx_message_quality ON conversation_log(quality_status, id)")
    conn.execute("""CREATE TABLE message_quality_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER NOT NULL REFERENCES conversation_log(id) ON DELETE CASCADE,
        assessed_at TEXT NOT NULL,
        receipt TEXT NOT NULL
    )""")
