"""Persist pending provider intent before any outbound invocation."""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS research_provider_attempts (
            attempt_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL REFERENCES research_tasks(id) ON DELETE CASCADE,
            action_id TEXT NOT NULL REFERENCES research_action_receipts(action_id) ON DELETE CASCADE,
            request_id TEXT NOT NULL,
            attempt_number INTEGER NOT NULL,
            receipt_json TEXT NOT NULL,
            outcome TEXT NOT NULL CHECK(outcome IN ('pending','complete','partial','failed','cancelled')),
            UNIQUE(action_id, request_id, attempt_number)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_provider_attempts_task ON research_provider_attempts(task_id, action_id)"
    )
