"""Index bounded belief histories without scanning the full event ledger."""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_belief_events_belief_timestamp ON belief_events(belief_id, timestamp DESC)"
    )
