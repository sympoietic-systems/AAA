"""Durable origin promotion and non-authoritative explicit-emission annotations."""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS belief_origin_promotions (agent_id TEXT NOT NULL, origin TEXT NOT NULL, "
        "promoted_at TEXT NOT NULL, PRIMARY KEY(agent_id,origin))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS belief_explicit_annotations (agent_id TEXT NOT NULL, encounter_id TEXT NOT NULL, "
        "assessment_id TEXT NOT NULL, annotations_json TEXT NOT NULL, PRIMARY KEY(agent_id,encounter_id), "
        "FOREIGN KEY(agent_id,encounter_id) REFERENCES belief_encounters(agent_id,id))"
    )
    for table in ("belief_origin_promotions", "belief_explicit_annotations"):
        for operation in ("UPDATE", "DELETE"):
            conn.execute(
                f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation.lower()} BEFORE {operation} ON {table} "
                "BEGIN SELECT RAISE(ABORT,'explicit intake provenance retained'); END"
            )
