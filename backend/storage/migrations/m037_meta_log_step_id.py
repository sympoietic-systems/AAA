"""Add step_id column to research_meta_log for step-level tracking.

branch_id references research_branches(id) — step UUIDs don't exist there,
causing FK violations.  step_id is a plain TEXT column with no FK, used
for linking meta-log entries to orchestrator steps.
"""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("ALTER TABLE research_meta_log ADD COLUMN step_id TEXT")
        conn.commit()
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e).lower():
            raise



def down(conn: sqlite3.Connection) -> None:
    pass
