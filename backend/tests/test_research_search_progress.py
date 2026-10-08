import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from backend.api.routes.research.steps import execute_step
from backend.services.research.steps import search
from backend.services.research.task_manager import ResearchTaskManager
from backend.services.research.task_state import SearchPayload, StepEnvelope


@pytest.mark.asyncio
async def test_optional_selector_times_out_and_preserves_candidates(monkeypatch):
    cancelled = asyncio.Event()

    async def stalled(*args, **kwargs):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    monkeypatch.setattr(search, "generate_unified", stalled)
    candidates = [{"url": f"https://example.org/{i}"} for i in range(3)]
    result = await asyncio.wait_for(
        search._select_high_fidelity_results(object(), "objective", "query", candidates, 2, timeout_seconds=0.01),
        timeout=1,
    )
    assert result == candidates[:2]
    await asyncio.wait_for(cancelled.wait(), 1)


@pytest.mark.asyncio
async def test_selector_parent_cancellation_does_not_return_fallback(monkeypatch):
    started = asyncio.Event()

    async def stalled(*args, **kwargs):
        started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(search, "generate_unified", stalled)
    pending = asyncio.create_task(search._select_high_fidelity_results(object(), "o", "q", [{}, {}], 1))
    await started.wait()
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending


@pytest.mark.asyncio
async def test_query_results_persist_before_next_selector_finishes(monkeypatch):
    orch = MagicMock()
    orch._state.config = {}
    orch._state.llm_provider = object()
    orch.default_top_n = 1
    orch.acquisition_enabled.return_value = True
    orch._load_cache.return_value = {}
    orch._create_or_update_step.side_effect = ["first", "second"]
    orch.acquire = AsyncMock(return_value=SimpleNamespace(content='[{"url":"https://example.org/a"}]'))
    second_started = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    async def select(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            second_started.set()
            await release.wait()
        return [{"url": "https://example.org/a"}]

    monkeypatch.setattr(search, "_select_high_fidelity_results", select)
    envelope = StepEnvelope(
        task_id="task",
        objective="o",
        current_depth=0,
        max_depth=1,
        budget=1,
        payload=SearchPayload(queries=["one", "two"]),
    )
    pending = asyncio.create_task(search.SearchStep().execute(orch, envelope))
    try:
        await asyncio.wait_for(second_started.wait(), 1)
        assert orch.step_result_repo.create.call_count == 1
        orch.step_repo.update.assert_called_once_with("first", status="completed", result_summary="1 results")
    finally:
        release.set()
        output = await pending
    assert len(output.payload.search_results) == 2


@pytest.mark.asyncio
async def test_manual_step_rejects_busy_phase_without_mutating_state():
    lock = asyncio.Lock()
    await lock.acquire()
    manager = MagicMock()
    manager.get_task.return_value = {"status": "active"}
    manager.orchestrator._state_mgr.locks = {"task": lock}
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(research_task_manager=manager)))
    try:
        with pytest.raises(HTTPException) as exc:
            await execute_step("task", request, rerun_step_type="search")
        assert exc.value.status_code == 409
        manager.orchestrator.set_phase.assert_not_called()
        manager.task_repo.update.assert_not_called()
    finally:
        lock.release()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["partial", "failed", "cancelled", "completed"])
async def test_auto_worker_preserves_terminal_status_without_second_transition(status):
    manager = SimpleNamespace()
    manager._get_semaphore = lambda: asyncio.Semaphore(1)
    manager.task_repo = MagicMock()
    manager.task_repo.get.side_effect = [{"title": "fixture", "status": "active"}, {"status": status}]
    manager.orchestrator = SimpleNamespace(execute=AsyncMock(return_value={"result_summary": "retained"}))
    manager.complete = MagicMock()
    manager.fail = MagicMock()
    manager.config = {"manual_mode": True}
    manager._active_tasks = {"task": object()}
    await ResearchTaskManager._execute_task(manager, "task")
    manager.complete.assert_not_called()
    manager.fail.assert_not_called()
    assert not manager._active_tasks
