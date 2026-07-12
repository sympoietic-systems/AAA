import logging
import sqlite3

logger = logging.getLogger(__name__)


def up(conn: sqlite3.Connection):
    """Create dream_log table for tracking individual dream cycles."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dream_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            action TEXT NOT NULL DEFAULT '',
            prompt_msg_id INTEGER,
            response_msg_id INTEGER,
            turns INTEGER NOT NULL DEFAULT 1,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_dream_log_conv
        ON dream_log(conversation_id, timestamp DESC)
    """)
    logger.info("Migration m027_dream_log applied")
