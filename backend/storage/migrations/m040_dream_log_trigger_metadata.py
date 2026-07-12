import logging
import sqlite3

logger = logging.getLogger(__name__)


def up(conn: sqlite3.Connection):
    """Add trigger_reason and source_conversation_id columns to dream_log."""
    conn.execute("""
        ALTER TABLE dream_log
        ADD COLUMN trigger_reason TEXT DEFAULT ''
    """)
    conn.execute("""
        ALTER TABLE dream_log
        ADD COLUMN source_conversation_id TEXT DEFAULT ''
    """)
    logger.info("Migration m040_dream_log_trigger_metadata applied")


def down(conn: sqlite3.Connection):
    """Remove columns (SQLite doesn't support DROP COLUMN directly, skip)."""
    logger.info("Migration m040_dream_log_trigger_metadata down (no-op, SQLite limitation)")
