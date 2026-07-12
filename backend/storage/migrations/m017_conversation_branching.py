import contextlib
import logging
import sqlite3

logger = logging.getLogger(__name__)


def up(conn: sqlite3.Connection):
    # 1. Add parent_message_id column to conversation_log
    try:
        conn.execute(
            "ALTER TABLE conversation_log ADD COLUMN parent_message_id INTEGER REFERENCES conversation_log(id) ON DELETE SET NULL"
        )
        logger.info("Added parent_message_id to conversation_log")
    except sqlite3.OperationalError as e:
        logger.warning("parent_message_id column already exists or failed to add: %s", e)

    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conversation_log_parent ON conversation_log(parent_message_id)")

    # 2. Add message_id column to consolidation_checkpoints
    try:
        conn.execute(
            "ALTER TABLE consolidation_checkpoints ADD COLUMN message_id INTEGER REFERENCES conversation_log(id) ON DELETE SET NULL"
        )
        logger.info("Added message_id to consolidation_checkpoints")
    except sqlite3.OperationalError as e:
        logger.warning("message_id column already exists or failed to add: %s", e)

    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cc_message ON consolidation_checkpoints(message_id)")

    # 3. Create message_links table for DAG cross-links
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS message_links (
                id          TEXT PRIMARY KEY,
                source_id   INTEGER NOT NULL REFERENCES conversation_log(id) ON DELETE CASCADE,
                target_id   INTEGER NOT NULL REFERENCES conversation_log(id) ON DELETE CASCADE,
                link_type   TEXT NOT NULL DEFAULT 'resonance',
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ml_src ON message_links(source_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ml_tgt ON message_links(target_id)")
        logger.info("Created message_links table and indexes")
    except sqlite3.OperationalError as e:
        logger.warning("Failed to create message_links table: %s", e)

    # 4. Recreate memory_nodes with composite primary key: (id, checkpoint_id)
    # Check if memory_nodes already has composite key by checking table info
    cursor = conn.execute("PRAGMA table_info(memory_nodes)")
    table_info = cursor.fetchall()

    # In table_info, pk is 1 or more if it is a primary key column.
    # We check if there are multiple primary keys.
    pk_columns = [col["name"] for col in table_info if col["pk"] > 0]

    if len(pk_columns) < 2:
        logger.info("Migrating memory_nodes to composite primary key (id, checkpoint_id)")
        try:
            # Drop old temporary table if it exists
            conn.execute("DROP TABLE IF EXISTS _memory_nodes_old")
            # Rename existing memory_nodes to old
            conn.execute("ALTER TABLE memory_nodes RENAME TO _memory_nodes_old")

            # Create new table with composite primary key
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_nodes (
                    id                TEXT NOT NULL,
                    conversation_id   TEXT NOT NULL,
                    checkpoint_id     INTEGER NOT NULL,
                    node_type         TEXT NOT NULL DEFAULT 'concept',
                    intensity         REAL NOT NULL DEFAULT 0.5,
                    scar              TEXT DEFAULT '',
                    glitch_potential  REAL NOT NULL DEFAULT 0.0,
                    intra_active_text TEXT NOT NULL,
                    surface_fragment  TEXT DEFAULT '',
                    agential_symmetry TEXT DEFAULT 'negotiated',
                    diffractive_key   TEXT DEFAULT '',
                    tendril_ids       TEXT DEFAULT '[]',
                    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id, checkpoint_id),
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                    FOREIGN KEY (checkpoint_id) REFERENCES consolidation_checkpoints(id) ON DELETE CASCADE
                )
            """)

            # Copy data from old to new
            # If the old table exists and has data, copy it
            conn.execute("""
                INSERT INTO memory_nodes (
                    id, conversation_id, checkpoint_id, node_type, intensity,
                    scar, glitch_potential, intra_active_text, surface_fragment,
                    agential_symmetry, diffractive_key, tendril_ids, created_at
                )
                SELECT
                    id, conversation_id, checkpoint_id, node_type, intensity,
                    scar, glitch_potential, intra_active_text, surface_fragment,
                    agential_symmetry, diffractive_key, tendril_ids, created_at
                FROM _memory_nodes_old
            """)

            # Drop old table
            conn.execute("DROP TABLE IF EXISTS _memory_nodes_old")

            # Re-create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mn_conv ON memory_nodes(conversation_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mn_type ON memory_nodes(node_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mn_intensity ON memory_nodes(intensity)")

            logger.info("Successfully migrated memory_nodes to composite primary key")
        except sqlite3.OperationalError as e:
            logger.exception("Failed to migrate memory_nodes: %s", e)
            # Rollback if rename occurred but create/copy failed (we try to rename back if possible)
            with contextlib.suppress(sqlite3.OperationalError):
                conn.execute("ALTER TABLE _memory_nodes_old RENAME TO memory_nodes")
    else:
        logger.info("memory_nodes already has a composite primary key: %s", pk_columns)
