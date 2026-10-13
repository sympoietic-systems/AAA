"""Immutable explicit links for operator-authored belief revisions and supersession."""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS belief_revision_links ("
        "agent_id TEXT NOT NULL, source_record_id TEXT NOT NULL, successor_record_id TEXT NOT NULL, "
        "action TEXT NOT NULL CHECK(action IN ('revise','supersede')), source_statement_sha256 TEXT NOT NULL, "
        "successor_statement_sha256 TEXT NOT NULL, command_id TEXT NOT NULL, decision_id TEXT NOT NULL, timestamp TEXT NOT NULL, "
        "PRIMARY KEY(agent_id,source_record_id,successor_record_id,action), "
        "FOREIGN KEY(agent_id,decision_id) REFERENCES belief_review_decisions(agent_id,id), "
        "FOREIGN KEY(agent_id,command_id) REFERENCES belief_workshop_commands(agent_id,id))"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_belief_revision_source ON belief_revision_links(agent_id,source_record_id,timestamp)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_belief_revision_successor ON belief_revision_links(agent_id,successor_record_id,timestamp)"
    )
    for operation in ("UPDATE", "DELETE"):
        conn.execute(
            f"CREATE TRIGGER IF NOT EXISTS immutable_belief_revision_links_{operation.lower()} "
            f"BEFORE {operation} ON belief_revision_links BEGIN SELECT RAISE(ABORT,'belief revision links retained'); END"
        )
