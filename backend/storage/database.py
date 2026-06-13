import sqlite3
from pathlib import Path
from typing import Optional


def get_db_path(db_path: str) -> Path:
    path = Path(db_path)
    if not path.is_absolute():
        path = Path(__file__).parent.parent / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> sqlite3.Connection:
    """Initialize database with all migrations and legacy data migration."""
    conn = get_connection(db_path)
    from backend.storage.migrations import run_all_migrations
    run_all_migrations(conn)
    _migrate_legacy_conversation(conn)
    _migrate_legacy_beliefs(conn)
    conn.commit()
    return conn


def _migrate_legacy_beliefs(conn: sqlite3.Connection) -> None:
    # Check if table belief_nodes exists before trying to query
    table_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='belief_nodes'"
    ).fetchone()
    if not table_exists:
        return

    # Check if table belief_proposals exists
    proposal_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='belief_proposals'"
    ).fetchone()
    if not proposal_exists:
        return

    rows = conn.execute(
        """SELECT id, agent_id, label, statement, origin, confidence, ontological_mass, vector_16d, lifecycle_stage, genesis_materials 
           FROM belief_nodes 
           WHERE lifecycle_stage IN ('nucleation', 'accretion', 'collapsed')"""
    ).fetchall()

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


_LEGACY_CONVERSATION_ID = "00000000-0000-0000-0000-000000000000"


def _migrate_legacy_conversation(conn: sqlite3.Connection) -> None:
    orphan_count = conn.execute(
        "SELECT COUNT(*) FROM conversation_log WHERE conversation_id = ''"
    ).fetchone()[0]

    if orphan_count == 0:
        return

    conn.execute(
        """INSERT OR IGNORE INTO conversations (id, title, agent_id)
           VALUES (?, ?, ?)""",
        (_LEGACY_CONVERSATION_ID, "Legacy", ""),
    )

    conn.execute(
        "UPDATE conversation_log SET conversation_id = ? WHERE conversation_id = ''",
        (_LEGACY_CONVERSATION_ID,),
    )
