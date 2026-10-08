"""Persistent browser session records."""

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


class AuthSessionRepository(BaseRepository):
    @with_connection
    def initialize(self) -> None:
        conn = self._conn()
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
        conn.commit()

    @with_connection
    def issue(self, session_hash: str, created_at: int, expires_at: int, password_digest: bytes, capacity: int) -> None:
        conn = self._conn()
        with self.atomic():
            conn.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (created_at,))
            count = int(conn.execute("SELECT COUNT(*) FROM auth_sessions").fetchone()[0])
            overflow = max(0, count - capacity + 1)
            if overflow:
                conn.execute(
                    """DELETE FROM auth_sessions WHERE session_hash IN (
                           SELECT session_hash FROM auth_sessions ORDER BY created_at ASC LIMIT ?
                       )""",
                    (overflow,),
                )
            conn.execute(
                """INSERT INTO auth_sessions
                   (session_hash, created_at, expires_at, password_digest)
                   VALUES (?, ?, ?, ?)""",
                (session_hash, created_at, expires_at, password_digest),
            )

    @with_connection
    def get(self, session_hash: str) -> tuple[int, bytes, bool] | None:
        row = (
            self._conn()
            .execute(
                "SELECT expires_at, password_digest, revoked_at FROM auth_sessions WHERE session_hash = ?",
                (session_hash,),
            )
            .fetchone()
        )
        if row is None:
            return None
        return int(row["expires_at"]), bytes(row["password_digest"]), row["revoked_at"] is not None

    @with_connection
    def revoke(self, session_hash: str, reason: str, revoked_at: int) -> None:
        self._conn().execute(
            """UPDATE auth_sessions SET revoked_at = ?, revocation_reason = ?
               WHERE session_hash = ? AND revoked_at IS NULL""",
            (revoked_at, reason, session_hash),
        )
