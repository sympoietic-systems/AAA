"""Add rerun_version column to research_steps for in-place step rerun.

When a step is re-executed, its row is updated in-place and
rerun_version increments.  All downstream steps (higher step_number)
are marked 'stale' for cascade re-execution.
"""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.execute("ALTER TABLE research_steps ADD COLUMN rerun_version INTEGER NOT NULL DEFAULT 1")
    conn.commit()


def down(conn: sqlite3.Connection) -> None:
    pass
