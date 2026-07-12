"""Add cached_inputs column to research_tasks for phase input caching.

Stores serialized JSON keyed by phase name.  Avoids expensive recomputation
of persona/prompts on tab switches and step re-execution.
"""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("ALTER TABLE research_tasks ADD COLUMN cached_inputs TEXT")
        conn.commit()
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e).lower():
            raise


def down(conn: sqlite3.Connection) -> None:
    # SQLite doesn't support DROP COLUMN easily; leaving column in place is harmless.
    pass
