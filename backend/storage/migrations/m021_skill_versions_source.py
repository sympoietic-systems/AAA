import logging
import sqlite3

logger = logging.getLogger(__name__)


def up(conn: sqlite3.Connection):
    try:
        conn.execute("ALTER TABLE skill_versions ADD COLUMN source TEXT DEFAULT 'user'")
        logger.info("Added source column to skill_versions table")
    except sqlite3.OperationalError as e:
        logger.warning("Failed to add source column to skill_versions: %s", e)
