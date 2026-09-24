import asyncio
from types import SimpleNamespace

import pytest

from backend.services.chat import ChatService
from backend.services.keyed_lock import KeyedLockRegistry


async def test_same_key_serializes_and_idle_entry_is_removed():
    registry = KeyedLockRegistry()
    active = 0
    peak = 0

    async def worker() -> None:
        nonlocal active, peak
        async with registry.hold("conversation-1"):
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0)
            active -= 1

    await asyncio.gather(*(worker() for _ in range(12)))

    assert peak == 1
    assert registry.active_key_count == 0


async def test_distinct_keys_run_concurrently_without_retaining_entries():
    registry = KeyedLockRegistry()
    both_entered = asyncio.Event()
    entered = 0

    async def worker(key: str) -> None:
        nonlocal entered
        async with registry.hold(key):
            entered += 1
            if entered == 2:
                both_entered.set()
            await asyncio.wait_for(both_entered.wait(), timeout=1)

    await asyncio.gather(worker("conversation-1"), worker("conversation-2"))

    assert registry.active_key_count == 0


async def test_cancelled_waiter_does_not_leak_key():
    registry = KeyedLockRegistry()
    holder_entered = asyncio.Event()
    release_holder = asyncio.Event()

    async def holder() -> None:
        async with registry.hold("conversation-1"):
            holder_entered.set()
            await release_holder.wait()

    async def waiter() -> None:
        async with registry.hold("conversation-1"):
            raise AssertionError("cancelled waiter acquired the lock")

    holder_task = asyncio.create_task(holder())
    await holder_entered.wait()
    waiter_task = asyncio.create_task(waiter())
    await asyncio.sleep(0)
    waiter_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiter_task

    assert registry.active_key_count == 1
    release_holder.set()
    await holder_task
    assert registry.active_key_count == 0


async def test_many_transient_keys_leave_registry_bounded_by_active_work():
    registry = KeyedLockRegistry()

    for index in range(500):
        async with registry.hold(f"conversation-{index}"):
            assert registry.active_key_count == 1

    assert registry.active_key_count == 0


def test_chat_services_share_app_owned_registry():
    state = SimpleNamespace(conversation_locks=KeyedLockRegistry())

    first = ChatService(state)
    second = ChatService(state)

    assert first._conversation_locks is state.conversation_locks
    assert second._conversation_locks is state.conversation_locks
