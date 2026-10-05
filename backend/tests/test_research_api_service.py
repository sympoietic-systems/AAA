import asyncio
import threading

from backend.services.research.api import continue_task, queue_task, rerun_task, run_research_sync


async def test_partial_task_can_retry_as_a_new_task(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from backend.api.routes.research import tasks

    source = {
        "id": "partial",
        "status": "partial",
        "objective": "Recover evidence",
        "title": "Partial",
        "trigger_source": "user_console",
        "priority": 1,
        "max_depth": 1,
        "max_breadth": 1,
        "is_agonistic": 0,
        "budget_limit_usd": 1,
    }
    created = []

    def create_task(**fields):
        created.append(fields)
        return "new-task"

    manager = SimpleNamespace(get_task=lambda task_id: source, create_task=create_task)
    queued = AsyncMock()
    monkeypatch.setattr(tasks, "queue_task", queued)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(research_task_manager=manager)))
    result = await tasks.retry_task("partial", request)
    assert result == {"task_id": "new-task", "status": "queued", "retried_from": "partial"}
    assert created[0]["objective"] == source["objective"]
    queued.assert_awaited_once_with(manager, "new-task")


async def test_run_research_sync_uses_worker_thread():
    event_loop_thread = threading.get_ident()

    worker_thread = await run_research_sync(threading.get_ident)

    assert worker_thread != event_loop_thread


async def test_queue_task_offloads_transition_and_awaits_queue_handoff():
    event_loop_thread = threading.get_ident()
    transition_threads: list[int] = []
    processed = asyncio.Event()

    class Manager:
        def transition(self, task_id: str, status: str) -> None:
            assert (task_id, status) == ("task-1", "queued")
            transition_threads.append(threading.get_ident())

        async def _try_process_queue(self) -> None:
            processed.set()

    await queue_task(Manager(), "task-1")

    assert processed.is_set()
    assert len(transition_threads) == 1
    assert transition_threads[0] != event_loop_thread


async def test_rerun_and_continue_schedule_loop_owned_tasks():
    rerun_started = asyncio.Event()
    continue_started = asyncio.Event()

    class Manager:
        def __init__(self) -> None:
            self._active_tasks: dict[str, asyncio.Task] = {}
            self.rerun_schedule: bool | None = None
            self.continue_schedule: bool | None = None

        def rerun_task(self, task_id: str, *, schedule: bool = True) -> None:
            self.rerun_schedule = schedule

        async def _try_process_queue(self) -> None:
            rerun_started.set()

        def continue_task(self, task_id: str, *, schedule: bool = True, **kwargs) -> None:
            self.continue_schedule = schedule

        async def _execute_continued_task(self, task_id: str) -> None:
            continue_started.set()

    manager = Manager()
    await rerun_task(manager, "task-1")
    await continue_task(manager, "task-1", additional_cycles=2)
    await asyncio.wait_for(continue_started.wait(), timeout=1)

    assert rerun_started.is_set()
    assert manager.rerun_schedule is False
    assert manager.continue_schedule is False
    assert "task-1" in manager._active_tasks
    await manager._active_tasks["task-1"]
