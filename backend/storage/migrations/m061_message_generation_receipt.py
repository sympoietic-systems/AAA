"""Store compact provider provenance on generated assistant messages."""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.execute("ALTER TABLE conversation_log ADD COLUMN generation_receipt TEXT")
