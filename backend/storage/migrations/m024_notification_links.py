import sqlite3
import logging

logger = logging.getLogger(__name__)


def up(conn: sqlite3.Connection):
    # Alter notifications table to add new columns for polymorphic linking
    for col, col_type in [
        ("source_type", "TEXT"),
        ("source_id", "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE notifications ADD COLUMN {col} {col_type}")
            logger.info("Added column %s to notifications", col)
        except sqlite3.OperationalError:
            # Column already exists, safe to ignore
            pass
