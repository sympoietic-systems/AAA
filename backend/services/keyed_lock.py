"""Application-scoped keyed asyncio lock registry."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass


@dataclass
class _LockEntry:
    lock: asyncio.Lock
    users: int = 0


class KeyedLockRegistry:
    """Serialize work per key and discard entries when no holder or waiter remains."""

    def __init__(self) -> None:
        self._entries: dict[str, _LockEntry] = {}

    @property
    def active_key_count(self) -> int:
        return len(self._entries)

    @asynccontextmanager
    async def hold(self, key: str) -> AsyncIterator[None]:
        entry = self._entries.get(key)
        if entry is None:
            entry = _LockEntry(lock=asyncio.Lock())
            self._entries[key] = entry
        entry.users += 1

        acquired = False
        try:
            await entry.lock.acquire()
            acquired = True
            yield
        finally:
            if acquired:
                entry.lock.release()
            entry.users -= 1
            if entry.users == 0 and self._entries.get(key) is entry:
                self._entries.pop(key, None)
