"""Immutable operator command/teachback annotations linked to the existing decision ledger."""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS belief_workshop_commands (agent_id TEXT NOT NULL, id TEXT NOT NULL, "
        "record_id TEXT NOT NULL, input_hash TEXT NOT NULL, decision_id TEXT NOT NULL, action TEXT NOT NULL, timestamp TEXT NOT NULL, "
        "receipt_json TEXT NOT NULL, PRIMARY KEY(agent_id,id), "
        "FOREIGN KEY(agent_id,decision_id) REFERENCES belief_review_decisions(agent_id,id))"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_workshop_record ON belief_workshop_commands(agent_id,record_id,timestamp,id)"
    )
    for operation in ("UPDATE", "DELETE"):
        conn.execute(
            f"CREATE TRIGGER IF NOT EXISTS immutable_belief_workshop_{operation.lower()} BEFORE {operation} ON belief_workshop_commands "
            "BEGIN SELECT RAISE(ABORT,'workshop history retained'); END"
        )
