"""Add orchestrator_state to research_tasks and query_group/query_text to research_steps.

orchestrator_state: Full serialised orchestrator state (JSON blob). Persisted after
  every step so resume/restart never loses data. Contains: phase, query_index,
  current_depth, all_findings, plan, step_number, caches.

query_group: Which search query group (1-based) this step belongs to.
query_text: The actual query text used for search/digest steps (for display).
"""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.execute("ALTER TABLE research_tasks ADD COLUMN orchestrator_state TEXT")
    conn.execute("ALTER TABLE research_steps ADD COLUMN query_group INTEGER")
    conn.execute("ALTER TABLE research_steps ADD COLUMN query_text TEXT")
    conn.commit()


def down(conn: sqlite3.Connection) -> None:
    pass
