import sqlite3
import logging

logger = logging.getLogger(__name__)


def up(conn: sqlite3.Connection):
    # 1. Create skill_versions table
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS skill_versions (
                id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                content TEXT NOT NULL,
                description TEXT NOT NULL,
                trigger_keywords TEXT,
                changelog TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(skill_id) REFERENCES skill_nodes(id) ON DELETE CASCADE,
                UNIQUE(skill_id, version)
            )
        """)
        logger.info("Created skill_versions table")
    except sqlite3.OperationalError as e:
        logger.warning("Failed to create skill_versions table: %s", e)

    # 2. Backfill existing skills into skill_versions
    try:
        conn.execute("""
            INSERT OR IGNORE INTO skill_versions (id, skill_id, version, content, description, trigger_keywords, changelog, created_at)
            SELECT id || '_' || version, id, version, content, description, trigger_keywords, changelog, updated_at
            FROM skill_nodes
        """)
        logger.info("Backfilled existing skills into skill_versions")
    except sqlite3.OperationalError as e:
        logger.warning("Failed to backfill skill_versions: %s", e)
