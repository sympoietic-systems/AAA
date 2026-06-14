import sqlite3
import logging

logger = logging.getLogger(__name__)


def up(conn: sqlite3.Connection):
    """Create tables for the dynamic personality cascade.
    
    - commitment_nodes: theoretical commitment lifecycle
    - commitment_events: audit trail for commitment changes
    - expertise_nodes: domain expertise accretion state
    - personality_state: aspirational trait attractors (single row)
    """

    # 1. commitment_nodes
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS commitment_nodes (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL DEFAULT 'symbia',
                label TEXT NOT NULL,
                statement TEXT NOT NULL,
                lifecycle_stage TEXT NOT NULL DEFAULT 'active'
                    CHECK(lifecycle_stage IN ('proto', 'active', 'spectral')),
                confidence REAL NOT NULL DEFAULT 0.0,
                ontological_mass REAL NOT NULL DEFAULT 1.0,
                vector_16d TEXT NOT NULL DEFAULT '[]',
                nucleation_rationale TEXT,
                collapse_rationale TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(agent_id, label)
            )
        """)
        logger.info("Created commitment_nodes table")
    except sqlite3.OperationalError as e:
        logger.error("Failed to create commitment_nodes table: %s", e)
        raise

    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_commitment_agent ON commitment_nodes(agent_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_commitment_stage ON commitment_nodes(agent_id, lifecycle_stage)"
        )
    except sqlite3.OperationalError as e:
        logger.error("Failed to create commitment_node indexes: %s", e)
        raise

    # 2. commitment_events
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS commitment_events (
                id TEXT PRIMARY KEY,
                commitment_id TEXT NOT NULL,
                event_type TEXT NOT NULL
                    CHECK(event_type IN (
                        'nucleation', 'crystallization', 'mass_update',
                        'statement_refinement', 'collapse'
                    )),
                rationale TEXT,
                mass_before REAL,
                mass_after REAL,
                confidence_before REAL,
                confidence_after REAL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(commitment_id) REFERENCES commitment_nodes(id) ON DELETE CASCADE
            )
        """)
        logger.info("Created commitment_events table")
    except sqlite3.OperationalError as e:
        logger.error("Failed to create commitment_events table: %s", e)
        raise

    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_commitment_events_cid ON commitment_events(commitment_id)"
        )
    except sqlite3.OperationalError as e:
        logger.error("Failed to create commitment_events index: %s", e)
        raise

    # 3. expertise_nodes
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expertise_nodes (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL DEFAULT 'symbia',
                domain TEXT NOT NULL,
                lifecycle_stage TEXT NOT NULL DEFAULT 'proto'
                    CHECK(lifecycle_stage IN ('proto', 'active', 'dormant')),
                ontological_mass REAL NOT NULL DEFAULT 0.05,
                level_label TEXT NOT NULL DEFAULT 'nascent'
                    CHECK(level_label IN ('nascent', 'developing', 'advanced', 'dormant')),
                vector_16d TEXT NOT NULL DEFAULT '[]',
                signal_count INTEGER NOT NULL DEFAULT 0,
                last_signal_at DATETIME,
                crystallization_rationale TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(agent_id, domain)
            )
        """)
        logger.info("Created expertise_nodes table")
    except sqlite3.OperationalError as e:
        logger.error("Failed to create expertise_nodes table: %s", e)
        raise

    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_expertise_agent ON expertise_nodes(agent_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_expertise_stage ON expertise_nodes(agent_id, lifecycle_stage)"
        )
    except sqlite3.OperationalError as e:
        logger.error("Failed to create expertise_nodes indexes: %s", e)
        raise

    # 4. personality_state (single-row table)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS personality_state (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                agent_id TEXT NOT NULL DEFAULT 'symbia',
                aspirational_traits_json TEXT NOT NULL DEFAULT '{}',
                active_commitment_ids_json TEXT NOT NULL DEFAULT '[]',
                trait_computation_version INTEGER NOT NULL DEFAULT 1,
                last_recomputed_at DATETIME,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("Created personality_state table")
    except sqlite3.OperationalError as e:
        logger.error("Failed to create personality_state table: %s", e)
        raise
