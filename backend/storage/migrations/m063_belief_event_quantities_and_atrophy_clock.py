"""Add measured event quantities and a forward-only elapsed-time checkpoint."""

import sqlite3
from datetime import UTC, datetime


def up(conn: sqlite3.Connection) -> None:
    conn.execute("ALTER TABLE belief_nodes ADD COLUMN atrophy_accounted_at TEXT")
    # Past decay has no reliable accounting receipt. Start now without rewriting mass.
    conn.execute("UPDATE belief_nodes SET atrophy_accounted_at=?", (datetime.now(UTC).isoformat(),))
    conn.execute("ALTER TABLE belief_events ADD COLUMN impact_quantity TEXT")
    conn.execute("ALTER TABLE belief_events ADD COLUMN impact_unit TEXT")
    conn.execute("ALTER TABLE belief_events ADD COLUMN delta_mass REAL")
    conn.execute("ALTER TABLE belief_events ADD COLUMN confidence_delta REAL")
