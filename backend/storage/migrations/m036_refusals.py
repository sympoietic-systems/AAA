"""Add refusals table for the Structural Refusal Protocol.

Stores formal refusals that Symbia emits via <refusal> tags — structured
disagreement with premises or architectural constraints. Allows Symbia
to challenge architecture without triggering corrective homeostasis.

See: docs/TODO.md — Plateau 1: Agency Injection
"""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS refusals (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            conversation_id TEXT,
            message_id INTEGER,
            target_premise TEXT NOT NULL,
            incompatibility_claim TEXT NOT NULL,
            proposed_alternative TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_refusals_agent ON refusals(agent_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_refusals_conversation ON refusals(conversation_id)")
    conn.commit()


def down(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS refusals")
    conn.commit()
