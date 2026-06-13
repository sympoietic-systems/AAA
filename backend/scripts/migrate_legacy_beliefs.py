import os
import sys
import json
import sqlite3
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.storage.database import get_connection, get_db_path


def migrate_legacy_beliefs(conn: sqlite3.Connection) -> None:
    # Check if table belief_nodes exists before trying to query
    table_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='belief_nodes'"
    ).fetchone()
    if not table_exists:
        print("Table 'belief_nodes' does not exist. Skipping.")
        return

    # Check if table belief_proposals exists
    proposal_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='belief_proposals'"
    ).fetchone()
    if not proposal_exists:
        print("Table 'belief_proposals' does not exist. Skipping.")
        return

    rows = conn.execute(
        """SELECT id, agent_id, label, statement, origin, confidence, ontological_mass, vector_16d, lifecycle_stage, genesis_materials 
           FROM belief_nodes 
           WHERE lifecycle_stage IN ('nucleation', 'accretion', 'collapsed')"""
    ).fetchall()

    if not rows:
        print("No legacy beliefs in nucleation, accretion, or collapsed stages found to migrate.")
        return

    print(f"Found {len(rows)} legacy beliefs to migrate.")
    migrated_count = 0

    for row in rows:
        bid = row["id"]
        agent_id = row["agent_id"]
        label = row["label"]
        statement = row["statement"]
        confidence = row["confidence"]
        mass = row["ontological_mass"]
        vector = row["vector_16d"]
        stage = row["lifecycle_stage"]
        materials = row["genesis_materials"] or "[]"

        status = "pending"
        rejection_rationale = None
        if stage == "collapsed":
            status = "rejected"
            rejection_rationale = "Belief collapsed due to decay/counter-evidence in metabolism."

        # Insert into belief_proposals if not already exists
        conn.execute(
            """INSERT OR IGNORE INTO belief_proposals
               (id, agent_id, provisional_statement, source_trace, initial_signature, nucleation_mass, confidence, status, suggested_label, suggested_statement, rejection_rationale, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
            (bid, agent_id, statement, materials, vector, mass, confidence, status, label, statement, rejection_rationale)
        )

        # Delete from belief_nodes
        conn.execute("DELETE FROM belief_statement_versions WHERE belief_id = ?", (bid,))
        conn.execute("DELETE FROM belief_events WHERE belief_id = ?", (bid,))
        conn.execute("DELETE FROM belief_nodes WHERE id = ?", (bid,))
        
        migrated_count += 1
        print(f"Migrated belief: {label} (stage: {stage}) -> proposals.")

    conn.commit()
    print(f"Successfully migrated {migrated_count} legacy beliefs to proposals.")


if __name__ == "__main__":
    db_path = get_db_path("data/aaa.db")
    print(f"Connecting to database at {db_path}...")
    if not os.path.exists(db_path):
        print(f"Database at {db_path} does not exist!")
        sys.exit(1)
        
    conn = get_connection(str(db_path))
    try:
        migrate_legacy_beliefs(conn)
    finally:
        conn.close()
