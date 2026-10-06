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
def setup(tmp_path, request):
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
        config={
            "research_orchestrator": {"action_receipts_enabled": True, "provider_limits": getattr(request, "param", {})}
        },
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
async def test_acquisition_receipts_persist_cache_access_without_new_observation(setup, monkeypatch):
    import backend.services.research.orchestrator as orchestration
    from backend.services.research.acquisition import AcquisitionRuntime
    from backend.storage.repositories.research.acquisition import ResearchAcquisitionRepository

    orch, repo, app = setup
    monkeypatch.setattr(orchestration, "validate_safe_url", lambda url: url)
    monkeypatch.setattr(
        orchestration,
        "AcquisitionRuntime",
        lambda policy, **kwargs: AcquisitionRuntime(policy, validator=lambda url: url, **kwargs),
    )
    calls = 0

    async def execute(_, envelope):
        async def load():
            nonlocal calls
            calls += 1
            return "Evidence"

        first = await orch.acquire("task", "https://example.test/source", load)
        second = await orch.acquire("task", "https://example.test/source", load)
        assert not first.cache_hit and second.cache_hit and first.observed_at == second.observed_at
        return StepOutput(payload=PlanPayload())

    install_step(monkeypatch, execute)
    result = await orch.execute_step("task")
    acquisitions = ResearchAcquisitionRepository(repo._db_path).list_action("task", result["action_id"])
    assert calls == 1 and [item.outcome for item in acquisitions] == ["fetched", "cache_hit"]
    assert acquisitions[1].origin_acquisition_id == acquisitions[0].acquisition_id
    saved = orch._action_journal.repo.get("task", result["action_id"])
    assert saved.observation.acquisition_ids == tuple(item.acquisition_id for item in acquisitions)
    from backend.storage.research_evidence import EvidenceBundle

    bundle = EvidenceBundle.model_validate(orch._evidence_store.repo.export_bundle("task"))
    assert bundle.acquisitions == acquisitions
    await orch.aclose()


@pytest.mark.asyncio
async def test_failed_acquisition_has_sanitized_durable_observation(setup, monkeypatch):
    import backend.services.research.orchestrator as orchestration
    from backend.services.research.acquisition import AcquisitionRuntime
    from backend.storage.repositories.research.acquisition import ResearchAcquisitionRepository

    orch, repo, _ = setup
    monkeypatch.setattr(orchestration, "validate_safe_url", lambda url: url)
    monkeypatch.setattr(
        orchestration,
        "AcquisitionRuntime",
        lambda policy, **kwargs: AcquisitionRuntime(policy, validator=lambda url: url, **kwargs),
    )

    async def execute(_, envelope):
        async def fail():
            raise RuntimeError("private key secret")

        await orch.acquire("task", "https://example.test/source", fail)
        return StepOutput(payload=PlanPayload())

    install_step(monkeypatch, execute)
    result = await orch.execute_step("task")
    records = ResearchAcquisitionRepository(repo._db_path).list_action("task", result["action_id"])
    assert records[0].outcome == "failed" and records[0].error_category == "RuntimeError"
    assert "private key secret" not in records[0].model_dump_json()
    await orch.aclose()


@pytest.mark.asyncio
async def test_v119_parallel_cache_access_waits_for_durable_origin(setup, monkeypatch):
    import backend.services.research.orchestrator as orchestration
    from backend.services.research.acquisition import AcquisitionRuntime
    from backend.storage.repositories.research.acquisition import ResearchAcquisitionRepository

    orch, repo, _ = setup
    monkeypatch.setattr(orchestration, "validate_safe_url", lambda url: url)
    monkeypatch.setattr(
        orchestration,
        "AcquisitionRuntime",
        lambda policy, **kwargs: AcquisitionRuntime(policy, validator=lambda url: url, **kwargs),
    )
    original_finish = ResearchAcquisitionRepository.finish

    def finish(self, receipt):
        if receipt.outcome == "fetched":
            import time

            time.sleep(0.03)
        return original_finish(self, receipt)

    monkeypatch.setattr(ResearchAcquisitionRepository, "finish", finish)
    calls = 0

    async def execute(_, envelope):
        async def load():
            nonlocal calls
            calls += 1
            return "Evidence"

        results = await asyncio.gather(*(orch.acquire("task", "https://example.test/source", load) for _ in range(2)))
        assert {result.cache_hit for result in results} == {False, True}
        return StepOutput(payload=PlanPayload())

    install_step(monkeypatch, execute)
    result = await orch.execute_step("task")
    assert calls == 1
    rows = ResearchAcquisitionRepository(repo._db_path).list_action("task", result["action_id"])
    assert {item.outcome for item in rows} == {"fetched", "cache_hit"}
    assert all(item.source_id and item.source_version for item in rows)
    assert orch._action_journal.repo.get("task", result["action_id"]).status == "complete"
    await orch.aclose()


@pytest.mark.asyncio
async def test_pending_acquisition_marks_partial_and_closes_on_action_end(setup, monkeypatch):
    from datetime import UTC, datetime, timedelta

    from backend.storage.repositories.research.acquisition import ResearchAcquisitionRepository
    from backend.storage.research_acquisition import AcquisitionReceipt

    orch, repo, _ = setup
    acquisition_repo = ResearchAcquisitionRepository(repo._db_path)
    initial = None

    async def execute(_, envelope):
        nonlocal initial
        initial = AcquisitionReceipt(
            acquisition_id="pending-acquisition",
            task_id="task",
            action_id=orch._get_state("task")["active_action_id"],
            canonical_url="https://example.test/source",
            config_hash="fixture",
            started_at=datetime.now(UTC),
        )
        await asyncio.to_thread(acquisition_repo.reserve, initial)
        return StepOutput(payload=PlanPayload())

    install_step(monkeypatch, execute)
    result = await orch.execute_step("task")
    action = orch._action_journal.repo.get("task", result["action_id"])
    assert action.status == "partial"
    records = acquisition_repo.list_action("task", result["action_id"])
    assert records[0].outcome == "cancelled" and records[0].error_category == "action_ended"
    assert action.observation.acquisition_ids == ("pending-acquisition",)
    now = datetime.now(UTC)
    with pytest.raises(ReceiptConflictError, match="immutable"):
        acquisition_repo.finish(
            initial.model_copy(
                update=dict(
                    outcome="fetched",
                    completed_at=now,
                    observed_at=now,
                    valid_until=now + timedelta(seconds=30),
                    origin_acquisition_id=initial.acquisition_id,
                )
            )
        )
    await orch.aclose()


@pytest.mark.asyncio
async def test_truncated_synthesis_finishes_partial_and_manager_cannot_complete(setup, monkeypatch):
    from backend.services.research.task_manager import ResearchTaskManager

    orch, repo, app = setup
    state = orch._get_state("task")
    state["phase"] = "synthesizing"

    class Provider:
        async def generate(self, messages, **params):
            return {"content": "partial", "finish_reason": "length", "truncated": True}

    async def execute(_, envelope):
        await generate_unified(Provider(), user_prompt="fixture")
        return StepOutput(payload=PlanPayload(), step_ids=["partial:1"])

    install_step(monkeypatch, execute)
    result = await orch.execute_step("task")
    assert result["status"] == "partial" and result["next_phase"] == "complete"
    assert repo.get("task")["status"] == "partial"
    manager = ResearchTaskManager(app)
    manager.complete("task", "late success claim")
    assert repo.get("task")["status"] == "partial"
    delivery = manager.get_task("task")["provider_delivery"]
    assert delivery["degraded"] and delivery["pending_attempts"] == 0 and delivery["attempts"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("setup", [{"max_task_attempts": 1}], indirect=True)
async def test_exhausted_provider_fallback_cannot_become_complete(setup, monkeypatch):
    orch, repo, _ = setup
    state = orch._get_state("task")
    calls = 0

    class Provider:
        async def generate(self, messages, **params):
            nonlocal calls
            calls += 1
            assert calls == 1
            return {"content": "first", "finish_reason": "stop"}

    async def execute(_, envelope):
        response = await generate_unified(
            Provider(), user_prompt="fixture", fallback_value={"answer": "Research complete"}
        )
        assert response.get("error") or response["content"] == "first"
        return StepOutput(payload=PlanPayload())

    install_step(monkeypatch, execute)
    await orch.execute_step("task")
    state["phase"] = "synthesizing"
    result = await orch.execute_step("task")
    assert result["status"] == "partial"
    assert repo.get("task")["status"] == "partial"
    assert calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("setup", [{"task_timeout_seconds": 0.02}], indirect=True)
async def test_expired_task_deadline_ends_without_executing_phase(setup, monkeypatch):
    orch, repo, _ = setup
    execute = AsyncMock()
    install_step(monkeypatch, execute)
    await asyncio.sleep(0.03)
    result = await orch.execute_step("task")
    assert result["status"] == "error" and result["next_phase"] == "complete"
    execute.assert_not_awaited()
    assert repo.get("task")["status"] == "failed"


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
