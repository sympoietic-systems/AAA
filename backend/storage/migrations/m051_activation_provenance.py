"""Preserve historical unknown coverage; add assembly provenance for future turns."""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(conversation_log)")}
    if "activation_provenance" not in columns:
        conn.execute("ALTER TABLE conversation_log ADD COLUMN activation_provenance TEXT")
