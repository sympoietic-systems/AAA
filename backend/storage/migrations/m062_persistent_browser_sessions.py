"""Persist bounded opaque browser sessions across backend restarts."""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS auth_sessions (
               session_hash TEXT PRIMARY KEY,
               created_at INTEGER NOT NULL,
               expires_at INTEGER NOT NULL,
               password_digest BLOB NOT NULL,
               revoked_at INTEGER,
               revocation_reason TEXT
           )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_auth_sessions_created ON auth_sessions(created_at)")
