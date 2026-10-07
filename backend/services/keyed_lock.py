"""Application-scoped keyed asyncio lock registry."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass


@dataclass
class _LockEntry:
    lock: asyncio.Lock
    users: int = 0
    holder: asyncio.Task[object] | None = None
    depth: int = 0


class KeyedLockRegistry:
    """Serialize work per key with task-reentrancy and discard idle entries."""

    def __init__(self) -> None:
        self._entries: dict[str, _LockEntry] = {}

    @property
    def active_key_count(self) -> int:
        return len(self._entries)

    @asynccontextmanager
    async def hold(self, key: str) -> AsyncIterator[None]:
        current_task = asyncio.current_task()
        entry = self._entries.get(key)
        if entry is None:
            entry = _LockEntry(lock=asyncio.Lock())
            self._entries[key] = entry
        entry.users += 1

        if current_task is not None and entry.holder is current_task:
            entry.depth += 1
            try:
                yield
            finally:
                entry.depth -= 1
                entry.users -= 1
                if entry.users == 0 and self._entries.get(key) is entry:
                    self._entries.pop(key, None)
            return

        acquired = False
        try:
            await entry.lock.acquire()
            acquired = True
            entry.holder = current_task
            entry.depth = 1
            yield
        finally:
            if acquired:
                entry.depth -= 1
                if entry.depth == 0:
                    entry.holder = None
                    entry.lock.release()
            entry.users -= 1
            if entry.users == 0 and self._entries.get(key) is entry:
                self._entries.pop(key, None)
