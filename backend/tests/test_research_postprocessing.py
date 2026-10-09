import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.modules import provider_attempts
from backend.services.research.step_executor import ResearchStepExecutor


def executor():
    orch = SimpleNamespace(_metabolize_step=AsyncMock(), _log_meta=MagicMock())
    runner = ResearchStepExecutor(orch, {}, {}, {})
    runner.METABOLISM_TIMEOUT_SECONDS = 0.01
    return runner, orch


@pytest.mark.asyncio
async def test_v133_optional_belief_processing_is_bounded_and_incomplete_is_recorded():
    runner, orch = executor()
    cancelled = asyncio.Event()

    async def stalled(*args):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    orch._metabolize_step.side_effect = stalled
    assert not await asyncio.wait_for(runner._metabolize_bounded("task", "digesting", ["retained finding"], {}), 1)
    await asyncio.sleep(0)
    assert cancelled.is_set()
    event = orch._log_meta.call_args.args
    assert event[1] == "research_metabolism_incomplete"
    assert event[2]["reason"] == "timeout"


@pytest.mark.asyncio
async def test_v133_cancellation_resistant_optional_work_cannot_hold_research():
    runner, orch = executor()
    release = asyncio.Event()
    finished = asyncio.Event()

    async def resistant(*args):
        try:
            await release.wait()
        except asyncio.CancelledError:
            await release.wait()
        finally:
            finished.set()

    orch._metabolize_step.side_effect = resistant
    try:
        assert not await asyncio.wait_for(runner._metabolize_bounded("task", "digesting", ["finding"], {}), 1)
        assert not finished.is_set()
    finally:
        release.set()
        await asyncio.wait_for(finished.wait(), 1)


@pytest.mark.asyncio
async def test_expired_deadline_skips_optional_work_without_spending():
    runner, orch = executor()
    state = {
        "action_journal_policy": {
            "provider_policy": {"deadline": (datetime.now(UTC) - timedelta(seconds=1)).isoformat()}
        }
    }
    assert not await runner._metabolize_bounded("task", "consolidating", ["finding"], state)
    orch._metabolize_step.assert_not_awaited()
    assert orch._log_meta.call_args.args[2]["reason"] == "deadline_exhausted"


@pytest.mark.asyncio
async def test_optional_processing_parent_cancellation_propagates():
    runner, orch = executor()
    orch._metabolize_step.side_effect = asyncio.CancelledError
    with pytest.raises(asyncio.CancelledError):
        await runner._metabolize_bounded("task", "digesting", ["finding"], {})
    orch._log_meta.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("state,findings", [({"research_child": {"parent_task_id": "parent"}}, ["finding"]), ({}, [])])
async def test_children_and_empty_findings_skip_optional_work(state, findings):
    runner, orch = executor()
    assert await runner._metabolize_bounded("task", "digesting", findings, state)
    orch._metabolize_step.assert_not_awaited()


@pytest.mark.asyncio
async def test_deadline_and_execution_capacity_errors_are_distinct(monkeypatch):
    call = AsyncMock()
    with pytest.raises(provider_attempts.AttemptBudgetExceeded, match="deadline exceeded"):
        await provider_attempts.bounded_call(call, 0)
    monkeypatch.setattr(provider_attempts, "_slots", asyncio.Semaphore(0))
    with pytest.raises(provider_attempts.AttemptBudgetExceeded, match="capacity exhausted"):
        await provider_attempts.bounded_call(call, 10)
    call.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["reflection", "searching"])
async def test_expired_phase_before_model_call_creates_rerunnable_failure_row(tmp_path, phase):
    from backend.services.research.orchestrator import SomaticResearchOrchestrator
    from backend.storage.database import init_db
    from backend.storage.repositories.research.research_plan import ResearchPlanRepository
    from backend.storage.repositories.research.research_step import ResearchStepRepository
    from backend.storage.repositories.research.research_task import ResearchTaskRepository

    db = str(tmp_path / "phase.db")
    init_db(db).close()
    tasks, steps = ResearchTaskRepository(db), ResearchStepRepository(db)
    tasks.create(
        {
            "id": "task",
            "title": "Fixture",
            "objective": "o",
            "trigger_source": "test",
            "status": "active",
            "max_depth": 1,
            "budget_limit_usd": 1,
        }
    )
    plans = ResearchPlanRepository(db)
    plans.create({"id": "plan", "task_id": "task", "plan_json": "{}"})
    app = SimpleNamespace(
        config={
            "research_orchestrator": {
                "action_receipts_enabled": True,
                "provider_limits": {"task_timeout_seconds": 0.001},
            }
        },
        research_task_repo=tasks,
        research_step_repo=steps,
        research_plan_repo=plans,
        research_step_result_repo=None,
        research_meta_log_repo=None,
    )
    orch = SomaticResearchOrchestrator(app)
    state = orch.init_task("task")
    state["phase"] = phase
    state["plan_id"] = "plan"
    if phase == "searching":
        for group, status in [(1, "completed"), (2, "running")]:
            steps.create(
                {
                    "id": f"search{group}",
                    "task_id": "task",
                    "plan_id": "plan",
                    "step_type": "search",
                    "step_number": 1,
                    "phase_group": 1,
                    "query_group": group,
                    "sub_sequence": 0,
                    "status": status,
                }
            )
    await asyncio.sleep(0.01)
    result = await orch.execute_step("task")
    assert result["status"] == "error"
    assert "deadline exceeded" in result["message"]
    rows = steps.get_by_task("task")
    if phase == "reflection":
        assert len(rows) == 1 and rows[0]["step_type"] == "reflection" and rows[0]["status"] == "failed"
    else:
        assert steps.get("search1")["status"] == "completed"
        assert steps.get("search2")["status"] == "failed"
    assert tasks.get("task")["status"] == "failed"
    await orch.aclose()
