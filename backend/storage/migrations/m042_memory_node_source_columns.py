"""Add source_type and source_id columns to memory_nodes for universal source attachment.

Enables querying memory nodes by origin pipeline: conversation, research, dream, skill, etc.
Backward-compatible — default 'conversation' preserves existing semantics.
See: docs/decisions/ADR-060-research-memory-integration.md
"""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    for sql in [
        "ALTER TABLE memory_nodes ADD COLUMN source_type TEXT DEFAULT 'conversation'",
        "ALTER TABLE memory_nodes ADD COLUMN source_id TEXT DEFAULT ''",
    ]:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mn_source ON memory_nodes(source_type, source_id)"
    )
    conn.commit()
