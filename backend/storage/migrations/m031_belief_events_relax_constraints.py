"""Remove overly restrictive CHECK constraints on belief_events.source_type and event_type.

The original m010 constraint only allowed 10 source_type values and 5 event_type values.
In practice, the codebase uses additional types:
  - source_type: atrophy, ghost_ecology
  - event_type: atrophy, revision, accretion
"""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    # Recreate belief_events table without the restrictive CHECK constraints
    conn.execute("ALTER TABLE belief_events RENAME TO belief_events_old")

    conn.execute("""
        CREATE TABLE belief_events (
            id TEXT PRIMARY KEY,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            belief_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_id TEXT,
            alignment_coefficient REAL,
            perturbation_magnitude REAL,
            event_type TEXT NOT NULL,
            impact_score REAL,
            rationale TEXT,
            FOREIGN KEY(belief_id) REFERENCES belief_nodes(id) ON DELETE CASCADE
        )
    """)

    conn.execute("INSERT INTO belief_events SELECT * FROM belief_events_old")
    conn.execute("DROP TABLE belief_events_old")
    conn.commit()
