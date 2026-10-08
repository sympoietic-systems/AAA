"""Bounded browser sessions backed by memory or the application database."""

import hashlib
import os
import secrets
import time
from collections import OrderedDict

from backend.core.auth import get_auth_password
from backend.storage.repositories.auth_session import AuthSessionRepository

SESSION_COOKIE = "aaa_session"
DEFAULT_SESSION_TTL = 7 * 24 * 60 * 60


def get_session_ttl() -> int:
    """Return configured session TTL in seconds. Default: 7 days."""
    raw = os.environ.get("AAA_SESSION_TTL", "").strip()
    if not raw:
        return DEFAULT_SESSION_TTL
    try:
        val = int(raw)
        return val if val > 0 else DEFAULT_SESSION_TTL
    except ValueError:
        return DEFAULT_SESSION_TTL


SESSION_TTL = DEFAULT_SESSION_TTL


class SessionStore:
    """Store opaque sessions; persistent instances survive restarts and password rotation."""

    def __init__(self, capacity: int = 1024, ttl: int | None = None, db_path: str | None = None) -> None:
        self.capacity = capacity
        self.ttl = ttl if ttl is not None else get_session_ttl()
        self._sessions: OrderedDict[str, tuple[float, bytes]] = OrderedDict()
        self._repository = AuthSessionRepository(db_path) if db_path is not None else None

    def initialize(self) -> None:
        """Initialize persistent backing storage; no-op for an in-memory store."""
        if self._repository is not None:
            self._repository.initialize()

    def issue(self) -> str:
        token = secrets.token_urlsafe(32)
        key = self._key(token)
        password_digest = self._password_digest()
        if self._repository is not None:
            wall_clock = int(time.time())
            self._repository.issue(key, wall_clock, wall_clock + self.ttl, password_digest, self.capacity)
            return token

        now = time.monotonic()
        self._sessions = OrderedDict((key, value) for key, value in self._sessions.items() if value[0] > now)
        while len(self._sessions) >= self.capacity:
            self._sessions.popitem(last=False)
        self._sessions[key] = (now + self.ttl, password_digest)
        return token

    def valid(self, token: str | None) -> bool:
        if not token or len(token) > 128:
            return False
        key = self._key(token)
        if self._repository is not None:
            persisted_entry = self._repository.get(key)
            if persisted_entry is None:
                return False
            expires_at, password_digest, revoked = persisted_entry
            if revoked:
                return False
            if expires_at <= int(time.time()):
                self._repository.revoke(key, "expired", int(time.time()))
                return False
            if not secrets.compare_digest(password_digest, self._password_digest()):
                self._repository.revoke(key, "password_rotation", int(time.time()))
                return False
            return True

        entry = self._sessions.get(key)
        if entry is None:
            return False
        expires, password_digest = entry
        if expires <= time.monotonic() or not secrets.compare_digest(password_digest, self._password_digest()):
            self._sessions.pop(key, None)
            return False
        return True

    def revoke(self, token: str | None) -> None:
        if token:
            key = self._key(token)
            if self._repository is not None:
                self._repository.revoke(key, "logout", int(time.time()))
            else:
                self._sessions.pop(key, None)

    @staticmethod
    def _key(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _password_digest() -> bytes:
        return hashlib.sha256(get_auth_password().encode()).digest()
