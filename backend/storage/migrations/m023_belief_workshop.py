import sqlite3
import logging

logger = logging.getLogger(__name__)


def up(conn: sqlite3.Connection):
    # 1. Alter belief_nodes table to add new columns
    for col, col_type in [
        ("evolved_from_proposal", "TEXT"),
        ("genesis_materials", "TEXT"),  # JSON array of source traces
        ("version", "INTEGER DEFAULT 1"),
    ]:
        try:
            conn.execute(f"ALTER TABLE belief_nodes ADD COLUMN {col} {col_type}")
            logger.info("Added column %s to belief_nodes", col)
        except sqlite3.OperationalError:
            # Column already exists, safe to ignore
            pass

    # 2. Create belief_proposals table
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS belief_proposals (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL DEFAULT 'symbia',
                provisional_statement TEXT NOT NULL,
                source_trace TEXT NOT NULL, -- JSON formatted list of source trace objects
                initial_signature TEXT NOT NULL, -- JSON formatted 16D vector
                nucleation_mass REAL DEFAULT 0.1,
                confidence REAL DEFAULT 0.15,
                status TEXT CHECK(status IN ('pending', 'refined', 'rejected', 'adopted')) DEFAULT 'pending',
                suggested_label TEXT,
                suggested_statement TEXT,
                potential_merge_target TEXT,
                symbia_reflection TEXT,
                symbia_friction_rationale TEXT,
                rejection_rationale TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("Created belief_proposals table")
    except sqlite3.OperationalError as e:
        logger.error("Failed to create belief_proposals table: %s", e)
        raise

    try:
        conn.execute("ALTER TABLE belief_proposals ADD COLUMN potential_merge_target TEXT")
        logger.info("Added column potential_merge_target to belief_proposals")
    except sqlite3.OperationalError:
        pass

    # 3. Create belief_statement_versions table
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS belief_statement_versions (
                id TEXT PRIMARY KEY,
                belief_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                statement TEXT NOT NULL,
                vector_16d TEXT NOT NULL, -- JSON formatted 16D vector
                change_reason TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(belief_id) REFERENCES belief_nodes(id) ON DELETE CASCADE
            )
        """)
        logger.info("Created belief_statement_versions table")
    except sqlite3.OperationalError as e:
        logger.error("Failed to create belief_statement_versions table: %s", e)
        raise
