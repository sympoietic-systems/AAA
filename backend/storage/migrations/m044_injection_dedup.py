"""Deduplicate sediment_injections + add unique constraint.

Before: id PRIMARY KEY — no protection against injecting the same
file into the same conversation multiple times.

After: UNIQUE (source_conversation_id, source_file_name, target_conversation_id).
       Duplicate rows removed, keeping the earliest injected_at per combo.
"""

import sqlite3


def up(conn):
    try:
        # 1. Remove duplicates: keep the row with the earliest injected_at
        #    for each (source_conversation_id, source_file_name, target_conversation_id)
        conn.execute("""
            DELETE FROM sediment_injections
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM sediment_injections
                GROUP BY source_conversation_id, source_file_name, target_conversation_id
            )
        """)
        conn.commit()

        # 2. Add unique index to prevent future duplicates
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_si_unique_injection
            ON sediment_injections(source_conversation_id, source_file_name, target_conversation_id)
        """)
        conn.commit()
    except sqlite3.OperationalError:
        pass
