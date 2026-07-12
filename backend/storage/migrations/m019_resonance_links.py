import logging
import sqlite3

logger = logging.getLogger(__name__)


def up(conn: sqlite3.Connection):
    # 1. Add status column to message_links table
    try:
        conn.execute("ALTER TABLE message_links ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
        logger.info("Added status column to message_links")
    except sqlite3.OperationalError as e:
        logger.warning("status column already exists or failed to add: %s", e)

    # 2. Add justification column to message_links table
    try:
        conn.execute("ALTER TABLE message_links ADD COLUMN justification TEXT DEFAULT ''")
        logger.info("Added justification column to message_links")
    except sqlite3.OperationalError as e:
        logger.warning("justification column already exists or failed to add: %s", e)
