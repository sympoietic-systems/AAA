"""Concurrency utilities — shared semaphore and lock patterns."""

import asyncio


def ensure_semaphore(owner: object, attr_name: str, max_concurrent: int) -> asyncio.Semaphore:
    """Lazily create or return an asyncio.Semaphore on the owner object.

    Usage in a class:
        self._semaphore = None

        @property
        def max_concurrent(self) -> int:
            return self.config.get("max_concurrent", 3)

        async def do_work(self):
            sem = ensure_semaphore(self, '_semaphore', self.max_concurrent)
            async with sem:
                ...

    Args:
        owner: The object that owns the semaphore (usually 'self').
        attr_name: The instance attribute name to store the semaphore under.
        max_concurrent: The concurrency limit for the semaphore.
    """
    existing: asyncio.Semaphore | None = getattr(owner, attr_name, None)
    if existing is None:
        existing = asyncio.Semaphore(max_concurrent)
        setattr(owner, attr_name, existing)
    return existing
