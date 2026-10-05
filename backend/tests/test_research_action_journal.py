import asyncio
import json
import sqlite3
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.services.research.action_journal import InterruptedResearchActionError
from backend.services.research.orchestrator import SomaticResearchOrchestrator
from backend.services.research.provider_observation import generate_unified
from backend.services.research.steps.base import ResearchStepRegistry
from backend.services.research.task_state import PlanPayload, StepOutput
from backend.storage.database import init_db
from backend.storage.repositories.research.action_receipt import ReceiptConflictError
from backend.storage.repositories.research.research_task import ResearchTaskRepository


@pytest.fixture
def setup(tmp_path):
    path = str(tmp_path / "journal.db")
    init_db(path).close()
    repo = ResearchTaskRepository(path)
    repo.create(
        {
            "id": "task",
            "title": "Journal",
            "objective": "Check receipt delivery",
            "trigger_source": "test",
            "status": "active",
            "priority": 1,
            "max_depth": 1,
            "max_breadth": 1,
            "budget_limit_usd": 0.5,
        }
    )
    app = SimpleNamespace(
        config={"research_orchestrator": {"action_receipts_enabled": True}},
        research_task_repo=repo,
        research_plan_repo=None,
        research_step_repo=None,
        research_meta_log_repo=None,
    )
    orch = SomaticResearchOrchestrator(app)
    orch.init_task("task")
    orch._metabolize_step = AsyncMock()
    return orch, repo, app


def install_step(monkeypatch, execute):
    processor = SimpleNamespace(execute=execute)
    monkeypatch.setattr(ResearchStepRegistry, "get_step", lambda phase: processor)


@pytest.mark.asyncio
async def test_request_precedes_execution_and_terminal_checkpoint_survives_restart(setup, monkeypatch):
    orch, repo, app = setup
    owner_thread = threading.get_ident()
    journal = orch._action_journal
    original_begin = journal.begin
    observed_threads = []

    def begin(*args):
        observed_threads.append(threading.get_ident())
        return original_begin(*args)

    monkeypatch.setattr(journal, "begin", begin)
    calls = []

    async def execute(_, envelope):
        task = await asyncio.to_thread(repo.get, "task")
        state = json.loads(task["orchestrator_state"])
        receipt = await asyncio.to_thread(journal.repo.get, "task", state["active_action_id"])
        assert receipt.status == "running"
        calls.append(receipt.action_id)
        return StepOutput(payload=PlanPayload(), step_ids=["step:1"])

    install_step(monkeypatch, execute)
    result = await orch.execute_step("task")
    persisted = json.loads(repo.get("task")["orchestrator_state"])
    receipt = journal.repo.get("task", result["action_id"])
    assert receipt.status == "complete"
    assert receipt.observation.output_refs == ("step:1",)
    assert receipt.observation.phase_elapsed_seconds >= 0
    assert persisted["active_action_id"] is None
    assert persisted["last_action_id"] == receipt.action_id
    assert persisted["phase"] == "searching"
    assert observed_threads[0] != owner_thread
    app.config["research_orchestrator"]["action_receipts_enabled"] = False
    restarted = SomaticResearchOrchestrator(app)
    restored = restarted.resume_task("task")
    assert restored["action_journal_policy"] == persisted["action_journal_policy"]
    await restarted.execute_step("task")
    next_id = json.loads(repo.get("task")["orchestrator_state"])["last_action_id"]
    assert restarted._action_journal.repo.get("task", next_id).dependency_ids == (receipt.action_id,)
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_interrupted_action_blocks_reexecution(setup, monkeypatch):
    orch, repo, app = setup
    state = orch._get_state("task")
    receipt = await asyncio.to_thread(orch._action_journal.begin, "task", state, "planning", {})
    restarted = SomaticResearchOrchestrator(app)
    restarted.resume_task("task")
    execute = AsyncMock()
    install_step(monkeypatch, execute)
    with pytest.raises(InterruptedResearchActionError):
        await restarted.execute_step("task")
    execute.assert_not_awaited()
    assert orch._action_journal.repo.get("task", receipt.action_id).status == "running"


@pytest.mark.asyncio
async def test_provider_latency_calls_and_first_evidence_are_observed(setup, monkeypatch):
    orch, repo, _ = setup
    orch._get_state("task")["phase"] = "parsing"
    provider = SimpleNamespace(
        provider_name="fixture",
        generate=AsyncMock(
            return_value={
                "content": "evidence",
                "model": "fixture-model",
                "provider": "fixture",
                "finish_reason": "stop",
                "usage": {"completion_tokens": 2},
            }
        ),
    )

    async def execute(_, envelope):
        await generate_unified(provider, user_prompt="private prompt")
        return StepOutput(payload=PlanPayload(), step_ids=["parsed:1"], signal_flags={"has_parsed_content": True})

    install_step(monkeypatch, execute)
    result = await orch.execute_step("task")
    receipt = orch._action_journal.repo.get("task", result["action_id"])
    (attempt,) = receipt.observation.provider_attempts
    assert attempt.task_id == "task" and attempt.action_id == result["action_id"]
    assert attempt.elapsed_seconds >= 0 and attempt.finish_reason == "stop"
    assert attempt.usage == {"completion_tokens": 2}
    assert "private prompt" not in receipt.model_dump_json()
    assert json.loads(repo.get("task")["orchestrator_state"])["first_useful_result_seconds"] >= 0


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["failed", "cancelled"])
async def test_exception_and_cancellation_get_terminal_receipts(setup, monkeypatch, outcome):
    orch, repo, _ = setup

    async def execute(_, envelope):
        if outcome == "cancelled":
            raise asyncio.CancelledError()
        raise ValueError("fixture failure")

    install_step(monkeypatch, execute)
    if outcome == "cancelled":
        with pytest.raises(asyncio.CancelledError):
            await orch.execute_step("task")
    else:
        assert (await orch.execute_step("task"))["status"] == "error"
    state = json.loads(repo.get("task")["orchestrator_state"])
    receipt = orch._action_journal.repo.get("task", state["last_action_id"])
    assert receipt.status == outcome
    assert state["active_action_id"] is None


@pytest.mark.asyncio
async def test_checkpoint_failure_keeps_durable_running_action(setup, monkeypatch):
    orch, repo, app = setup
    install_step(monkeypatch, AsyncMock(return_value=StepOutput(payload=PlanPayload())))
    journal = orch._action_journal
    original = journal.repo.checkpoint

    def checkpoint(receipt, state_json, *, starting=False):
        if not starting:
            raise OSError("fixture disk failure")
        original(receipt, state_json, starting=starting)

    monkeypatch.setattr(journal.repo, "checkpoint", checkpoint)
    with pytest.raises(OSError):
        await orch.execute_step("task")
    state = json.loads(repo.get("task")["orchestrator_state"])
    assert state["phase"] == "planning" and state["active_action_id"]
    assert journal.repo.get("task", state["active_action_id"]).status == "running"
    restarted = SomaticResearchOrchestrator(app)
    restarted.resume_task("task")
    with pytest.raises(InterruptedResearchActionError):
        await restarted.execute_step("task")


@pytest.mark.asyncio
async def test_legacy_resume_does_not_enable_journal(setup, monkeypatch):
    _, repo, app = setup
    repo.update("task", orchestrator_state=json.dumps({"phase": "planning", "all_findings": []}))
    orch = SomaticResearchOrchestrator(app)
    state = orch.init_task("task")
    assert state["action_journal_policy"]["enabled"] is False
    install_step(monkeypatch, AsyncMock(return_value=StepOutput(payload=PlanPayload())))
    assert "action_id" not in await orch.execute_step("task")
    assert orch._get_state("task")["action_journal_policy"]["coverage"] == "legacy_unknown"


def test_two_executors_cannot_start_from_same_checkpoint(setup):
    orch, repo, _ = setup
    state = orch._get_state("task")
    stale = dict(state)
    first = orch._action_journal.begin("task", state, "planning", {})
    with pytest.raises(ReceiptConflictError):
        orch._action_journal.begin("task", stale, "planning", {})
    orch._action_journal.finish(first, state, "complete", (), 0.01, False)
    with pytest.raises(ReceiptConflictError):
        orch._action_journal.begin("task", stale, "planning", {})
    assert json.loads(repo.get("task")["orchestrator_state"])["last_action_id"] == first.action_id


def test_receipt_and_checkpoint_rollback_together(setup):
    orch, repo, _ = setup
    state = orch._get_state("task")
    journal = orch._action_journal
    running = journal.begin("task", state, "planning", {})
    conn = sqlite3.connect(repo._db_path)
    conn.execute(
        "CREATE TRIGGER reject_checkpoint BEFORE UPDATE ON research_tasks BEGIN SELECT RAISE(ABORT, 'fixture checkpoint failure'); END"
    )
    conn.commit()
    conn.close()
    with pytest.raises(sqlite3.IntegrityError):
        journal.finish(running, state, "complete", ("step",), 0.1, False)
    assert journal.repo.get("task", running.action_id).status == "running"
    persisted = json.loads(repo.get("task")["orchestrator_state"])
    assert persisted["active_action_id"] == running.action_id
    assert persisted.get("last_action_id") is None


def test_policy_is_frozen_before_first_action(setup):
    orch, repo, app = setup
    policy = orch._get_state("task")["action_journal_policy"]
    assert json.loads(repo.get("task")["orchestrator_state"])["action_journal_policy"] == policy
    app.config["research_orchestrator"]["action_receipts_enabled"] = False
    restarted = SomaticResearchOrchestrator(app)
    assert restarted.resume_task("task")["action_journal_policy"] == policy
    assert restarted.init_task("task")["action_journal_policy"] == policy
