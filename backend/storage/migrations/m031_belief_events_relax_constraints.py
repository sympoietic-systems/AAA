"""Remove overly restrictive CHECK constraints on belief_events.source_type and event_type.

The original m010 constraint only allowed 10 source_type values and 5 event_type values.
In practice, the codebase uses additional types:
  - source_type: atrophy, ghost_ecology
  - event_type: atrophy, revision, accretion
"""

import sqlite3

_CREATE = """
    CREATE TABLE belief_events (
        id TEXT PRIMARY KEY,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        belief_id TEXT NOT NULL,
        source_type TEXT,
        source_id TEXT,
        alignment_coefficient REAL,
        perturbation_magnitude REAL,
        event_type TEXT,
        impact_score REAL,
        rationale TEXT,
        FOREIGN KEY(belief_id) REFERENCES belief_nodes(id) ON DELETE CASCADE
    )
"""


def up(conn: sqlite3.Connection) -> None:
    # Handle partial re-run from a previously failed attempt.
    # In that case belief_events_old exists (renamed), and belief_events
    # may be empty with the wrong schema (NOT NULL from the first attempt).
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='belief_events_old'"
    )
    if cursor.fetchone():
        conn.execute("DROP TABLE belief_events")
        conn.execute(_CREATE)
        conn.execute("INSERT INTO belief_events SELECT * FROM belief_events_old")
        conn.execute("DROP TABLE belief_events_old")
        conn.commit()
        return

    # Fresh migration: rename old table, create new without CHECK constraints
    conn.execute("ALTER TABLE belief_events RENAME TO belief_events_old")
    conn.execute(_CREATE)
    conn.execute("INSERT INTO belief_events SELECT * FROM belief_events_old")
    conn.execute("DROP TABLE belief_events_old")
    conn.commit()
