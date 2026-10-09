"""Forward-only lineage observations and typed events; no historical data inference."""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS belief_source_observations (agent_id TEXT NOT NULL, encounter_id TEXT NOT NULL, "
        "record_id TEXT NOT NULL, claim_id TEXT NOT NULL, internal_activity INTEGER NOT NULL CHECK(internal_activity IN (0,1)), "
        "recurrence INTEGER NOT NULL CHECK(recurrence IN (0,1)), observed_at TEXT NOT NULL, receipt_json TEXT NOT NULL, "
        "PRIMARY KEY(agent_id,encounter_id), FOREIGN KEY(agent_id,encounter_id) REFERENCES belief_encounters(agent_id,id))"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_belief_source_record ON belief_source_observations(agent_id,record_id,observed_at,encounter_id)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_belief_source_claim ON belief_source_observations(agent_id,claim_id)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS belief_review_events (agent_id TEXT NOT NULL, id TEXT NOT NULL, record_id TEXT NOT NULL, "
        "encounter_id TEXT NOT NULL, event_type TEXT NOT NULL, impact_quantity TEXT NOT NULL, impact_unit TEXT NOT NULL, "
        "impact_value REAL NOT NULL, delta_mass REAL NOT NULL, confidence_delta REAL NOT NULL, timestamp TEXT NOT NULL, "
        "receipt_json TEXT NOT NULL, PRIMARY KEY(agent_id,id), "
        "FOREIGN KEY(agent_id,encounter_id) REFERENCES belief_source_observations(agent_id,encounter_id))"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_belief_review_events_record ON belief_review_events(agent_id,record_id,timestamp,id)"
    )
    for table in ("belief_source_observations", "belief_review_events"):
        for operation in ("UPDATE", "DELETE"):
            conn.execute(
                f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation.lower()} BEFORE {operation} ON {table} "
                "BEGIN SELECT RAISE(ABORT,'source accounting provenance retained'); END"
            )
