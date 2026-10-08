"""Add source-bound admission receipts without rewriting historical beliefs."""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS belief_admission (
            id TEXT PRIMARY KEY,
            event_key TEXT UNIQUE NOT NULL,
            proposal_id TEXT,
            statement_key TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('assessing', 'complete')),
            receipt TEXT NOT NULL,
            created_at TEXT NOT NULL,
            assessed_at TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_belief_admission_proposal ON belief_admission(proposal_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_belief_admission_statement ON belief_admission(statement_key)")
