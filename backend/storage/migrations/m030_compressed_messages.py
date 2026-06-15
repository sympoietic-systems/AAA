"""R5: Create compressed_messages table for LLM-based batch message compression.

Each row represents a batch of messages that exited the floating window together.
The compressed_block contains an LLM-produced dense summary preserving key
decisions, novel concepts, tonal shifts, unresolved tensions, and factual claims.
"""
import logging

logger = logging.getLogger(__name__)


def up(conn):
    """Create compressed_messages table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS compressed_messages (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id   TEXT NOT NULL,
            first_message_id  INTEGER NOT NULL,
            last_message_id   INTEGER NOT NULL,
            compressed_block  TEXT NOT NULL,
            created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    logger.info("Created compressed_messages table")
