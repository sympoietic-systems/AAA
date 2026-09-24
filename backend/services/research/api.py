"""Typed async boundary for synchronous research API operations."""

import asyncio
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


async def run_research_sync(operation: Callable[P, R], /, *args: P.args, **kwargs: P.kwargs) -> R:
    """Run one synchronous research use case outside the event loop."""
    return await asyncio.to_thread(operation, *args, **kwargs)


async def queue_task(manager: Any, task_id: str) -> None:
    """Persist a queue transition off-loop, then start queue processing on-loop."""
    await run_research_sync(manager.transition, task_id, "queued")
    await manager._try_process_queue()


async def approve_and_queue_task(manager: Any, task_id: str) -> None:
    await run_research_sync(manager.approve, task_id)
    await queue_task(manager, task_id)


async def cancel_task(manager: Any, task_id: str) -> None:
    await run_research_sync(manager.transition, task_id, "cancelled")
    active = manager._active_tasks.get(task_id)
    if active is not None:
        active.cancel()


async def delete_task(manager: Any, task_id: str) -> None:
    active = manager._active_tasks.pop(task_id, None)
    if active is not None:
        active.cancel()

    def delete_persistence() -> None:
        manager.task_repo.delete_with_notes(task_id)

    await run_research_sync(delete_persistence)


async def run_task(manager: Any, task_id: str) -> None:
    await run_research_sync(manager.transition, task_id, "active")
    orch_config = manager._app_state.config.get("research_orchestrator", {})
    if orch_config.get("enabled", False) and manager.config.get("manual_mode", False):
        coroutine = manager._orchestrator_step_async(task_id, first_step=True)
    else:
        coroutine = manager._execute_task(task_id)
    manager._active_tasks[task_id] = asyncio.create_task(coroutine)


async def rerun_task(manager: Any, task_id: str) -> None:
    await run_research_sync(manager.rerun_task, task_id, schedule=False)
    await manager._try_process_queue()


async def continue_task(manager: Any, task_id: str, **kwargs: Any) -> None:
    await run_research_sync(manager.continue_task, task_id, schedule=False, **kwargs)
    coroutine = manager._execute_continued_task(task_id)
    manager._active_tasks[task_id] = asyncio.create_task(coroutine)
