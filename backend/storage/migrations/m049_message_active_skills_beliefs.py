"""Migration 049: Add active_skills and active_beliefs columns to conversation_log.

Persists active skills and active beliefs per-turn so message reply footers
can render active skills (+skill) and active beliefs (~belief) on history reload
and conversation tree navigation.
"""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(conversation_log)")
    cols = [r[1] for r in cursor.fetchall()]

    if "active_skills" not in cols:
        cursor.execute("ALTER TABLE conversation_log ADD COLUMN active_skills TEXT")
    if "active_beliefs" not in cols:
        cursor.execute("ALTER TABLE conversation_log ADD COLUMN active_beliefs TEXT")
