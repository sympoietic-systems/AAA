"""Add display_name column to perception_files.

Allows storing a human-readable name (e.g. research task objective)
alongside the technical file_name. Displayed in sediment injection lists.
"""

import sqlite3


def up(conn):
    try:
        conn.execute("ALTER TABLE perception_files ADD COLUMN display_name TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass
