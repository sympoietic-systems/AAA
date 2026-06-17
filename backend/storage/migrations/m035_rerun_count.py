"""Add rerun_count column to research_tasks for in-place rerun support.

See: docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 17 research_task_manager
"""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.execute("ALTER TABLE research_tasks ADD COLUMN rerun_count INTEGER NOT NULL DEFAULT 0")
    conn.commit()


def down(conn: sqlite3.Connection) -> None:
    # SQLite doesn't support DROP COLUMN easily; leaving column in place is harmless.
    pass
