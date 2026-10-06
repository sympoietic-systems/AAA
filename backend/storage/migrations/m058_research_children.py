"""Durable bounded child ownership and immutable evidence delivery."""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.execute("""CREATE TABLE IF NOT EXISTS research_child_runs (
        child_task_id TEXT PRIMARY KEY REFERENCES research_tasks(id) ON DELETE CASCADE,
        parent_task_id TEXT NOT NULL REFERENCES research_tasks(id) ON DELETE CASCADE,
        proposal_id TEXT NOT NULL REFERENCES research_branch_proposals(proposal_id),
        scope_id TEXT NOT NULL, allocation_json TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'allocated', packet_json TEXT,
        parent_action_id TEXT REFERENCES research_action_receipts(action_id),
        UNIQUE(parent_task_id,scope_id)
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_child_parent ON research_child_runs(parent_task_id)")
