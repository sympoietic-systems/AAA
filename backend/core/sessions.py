"""Bounded, process-local browser sessions; no persistent credentials."""

import hashlib
import secrets
import time
from collections import OrderedDict

from backend.core.auth import get_auth_password

SESSION_COOKIE = "aaa_session"
SESSION_TTL = 8 * 60 * 60


class SessionStore:
    """Each app owns one store. Restart and password rotation invalidate sessions."""

    def __init__(self, capacity: int = 1024, ttl: int = SESSION_TTL) -> None:
        self.capacity = capacity
        self.ttl = ttl
        self._sessions: OrderedDict[str, tuple[float, bytes]] = OrderedDict()

    def issue(self) -> str:
        now = time.monotonic()
        self._sessions = OrderedDict((key, value) for key, value in self._sessions.items() if value[0] > now)
        while len(self._sessions) >= self.capacity:
            self._sessions.popitem(last=False)
        token = secrets.token_urlsafe(32)
        self._sessions[self._key(token)] = (now + self.ttl, self._password_digest())
        return token

    def valid(self, token: str | None) -> bool:
        if not token or len(token) > 128:
            return False
        key = self._key(token)
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
            self._sessions.pop(self._key(token), None)

    @staticmethod
    def _key(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _password_digest() -> bytes:
        return hashlib.sha256(get_auth_password().encode()).digest()
