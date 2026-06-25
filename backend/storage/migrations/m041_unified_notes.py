"""Unified notes table — replaces conversation_notes with a polymorphic asset_type + asset_id pattern.

Supports notes on any text-bearing asset: conversation messages, research tasks, etc.
Migrates existing conversation_notes data into the new table, then drops the old one.
"""

import sqlite3


def up(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id              TEXT PRIMARY KEY,
            asset_type      TEXT NOT NULL,
            asset_id        TEXT NOT NULL,
            conversation_id TEXT,
            selected_text   TEXT NOT NULL,
            comment         TEXT DEFAULT '',
            visibility      TEXT NOT NULL DEFAULT 'personal',
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_conv ON notes(conversation_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_asset ON notes(asset_type, asset_id)")

    cursor = conn.execute("SELECT COUNT(*) FROM conversation_notes")
    count = cursor.fetchone()[0]

    if count > 0:
        conn.execute("""
            INSERT INTO notes (id, asset_type, asset_id, conversation_id, selected_text, comment, visibility, created_at, updated_at)
            SELECT
                id,
                'conversation_message',
                CAST(message_id AS TEXT),
                conversation_id,
                selected_text,
                comment,
                visibility,
                created_at,
                updated_at
            FROM conversation_notes
        """)

    conn.execute("DROP TABLE IF EXISTS conversation_notes")
    conn.execute("DROP INDEX IF EXISTS idx_cn_conv")
    conn.execute("DROP INDEX IF EXISTS idx_cn_msg")
