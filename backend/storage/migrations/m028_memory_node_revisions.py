"""R4: Add revision_count and last_merged_at columns to memory_nodes table.

These enable merge observability: tracking how many times a node has been
updated during incremental consolidation, and when the last merge occurred.
"""

import logging

logger = logging.getLogger(__name__)


def up(conn):
    """Add revision_count and last_merged_at columns."""
    table_info = conn.execute("PRAGMA table_info(memory_nodes)").fetchall()
    col_names = [col["name"] for col in table_info]

    if "revision_count" not in col_names:
        logger.info("Adding revision_count column to memory_nodes")
        conn.execute("ALTER TABLE memory_nodes ADD COLUMN revision_count INTEGER NOT NULL DEFAULT 0")

    if "last_merged_at" not in col_names:
        logger.info("Adding last_merged_at column to memory_nodes")
        conn.execute("ALTER TABLE memory_nodes ADD COLUMN last_merged_at DATETIME")
