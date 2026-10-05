"""Add research receipts without rewriting legacy task provenance."""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS research_action_receipts (
            action_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL REFERENCES research_tasks(id) ON DELETE CASCADE,
            request_json TEXT NOT NULL,
            receipt_json TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN
                ('pending', 'running', 'complete', 'partial', 'failed', 'cancelled'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_research_receipts_task_action
        ON research_action_receipts(task_id, action_id)
    """)
