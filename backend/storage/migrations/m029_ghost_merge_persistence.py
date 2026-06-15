"""13C: Add merged_from and merged_into columns to belief_nodes table.

These enable tracking which ghost beliefs have been absorbed by others
during dream daemon ghost ecology merging, preventing ghost accumulation
from distorting nucleation calculations.
"""
import logging

logger = logging.getLogger(__name__)


def up(conn):
    """Add merged_from and merged_into columns."""
    table_info = conn.execute("PRAGMA table_info(belief_nodes)").fetchall()
    col_names = [col["name"] for col in table_info]

    if "merged_from" not in col_names:
        logger.info("Adding merged_from column to belief_nodes")
        conn.execute(
            "ALTER TABLE belief_nodes ADD COLUMN merged_from TEXT"
        )

    if "merged_into" not in col_names:
        logger.info("Adding merged_into column to belief_nodes")
        conn.execute(
            "ALTER TABLE belief_nodes ADD COLUMN merged_into TEXT"
        )
