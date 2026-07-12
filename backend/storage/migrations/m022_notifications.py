import logging
import sqlite3

logger = logging.getLogger(__name__)


def up(conn: sqlite3.Connection):
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                snippet TEXT NOT NULL,
                conversation_id TEXT,
                message_id INTEGER,
                parent_message_id INTEGER,
                speaker TEXT,
                source TEXT,
                read INTEGER DEFAULT 0,
                dismissed INTEGER DEFAULT 0
            )
        """)
        logger.info("Created notifications table")
    except sqlite3.OperationalError as e:
        logger.error("Failed to create notifications table: %s", e)
        raise
