import sqlite3
import logging

logger = logging.getLogger(__name__)


def up(conn: sqlite3.Connection):
    """Add description column to expertise_nodes."""
    try:
        conn.execute("ALTER TABLE expertise_nodes ADD COLUMN description TEXT")
        logger.info("Added description column to expertise_nodes")
    except sqlite3.OperationalError:
        logger.info("description column already exists in expertise_nodes")
        pass
