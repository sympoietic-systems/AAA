import asyncio
import json
import time
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.services.research.action_journal import ResearchActionJournal
from backend.services.research.api import prepare_step_recovery
from backend.services.research.orchestrator import SomaticResearchOrchestrator
from backend.services.research.provider_policy import ProviderPolicy, query_limit
from backend.services.research.steps import digest
from backend.storage.database import init_db
from backend.storage.repositories.research.action_receipt import ReceiptConflictError, ResearchActionReceiptRepository
from backend.storage.repositories.research.provider_attempt import ResearchProviderAttemptRepository
from backend.storage.repositories.research.research_plan import ResearchPlanRepository
from backend.storage.repositories.research.research_step import ResearchStepRepository
from backend.storage.repositories.research.research_step_result import ResearchStepResultRepository
from backend.storage.repositories.research.research_task import ResearchTaskRepository
from backend.storage.research_receipts import ProviderAttemptReceipt


@pytest.fixture
def recovery(tmp_path):
    db = str(tmp_path / "recovery.db")
    init_db(db).close()
    tasks = ResearchTaskRepository(db)
    plans = ResearchPlanRepository(db)
    steps = ResearchStepRepository(db)
    results = ResearchStepResultRepository(db)
    receipts = ResearchActionReceiptRepository(db)
    tasks.create(
        {
            "id": "task",
            "title": "Recover",
            "objective": "o",
            "trigger_source": "test",
            "status": "active",
            "max_depth": 3,
            "budget_limit_usd": 1,
        }
    )
    plans.create({"id": "plan", "task_id": "task", "plan_json": "{}"})
    state = {
        "phase": "parsing",
        "objective": "o",
        "max_depth": 3,
        "budget": 1,
        "plan_id": "plan",
        "plan": {"search_queries": ["one", "two"]},
        "current_depth": 1,
        "phase_group": 6,
        "last_block": "query_block",
        "all_findings": ["prior finding"],
        "action_journal_policy": {
            "enabled": True,
            "scheduler_version": 1,
            "policy_hash": "original",
            "contract_hash": "contract",
            "provider_policy": ProviderPolicy(task_timeout_seconds=1).freeze(),
        },
    }
    journal = ResearchActionJournal(receipts)
    parsed = journal.begin("task", state, "parsing", {})
    journal.finish(parsed, state, "complete", (), 1, True)
    failed = journal.begin("task", state, "digesting", {})
    ResearchProviderAttemptRepository(db).reserve(
        ProviderAttemptReceipt(
            attempt_id="old-attempt",
            task_id="task",
            action_id=failed.action_id,
            request_id="old-request",
            provider="fixture",
            model="fixture",
            attempt_number=1,
            started_at=datetime.now(UTC),
        ),
        1,
    )
    state.update(phase="complete", delivery_degraded=True)
    journal.finish(failed, state, "failed", (), 1, False)
    tasks.update("task", status="failed")
    for group in (1, 2):
        for kind, sequence in (("parallel_parse", 1), ("digest", 2)):
            steps.create(
                {
                    "id": f"{kind}{group}",
                    "task_id": "task",
                    "plan_id": "plan",
                    "step_number": 6,
                    "phase_group": 6,
                    "query_group": group,
                    "sub_sequence": sequence,
                    "step_type": kind,
                    "status": "completed" if kind == "parallel_parse" else "failed",
                    "step_data": json.dumps({"depth": 1}),
                }
            )
        results.create(
            {
                "id": f"source{group}",
                "task_id": "task",
                "step_id": f"parallel_parse{group}",
                "source_url": f"https://example.org/{group}",
                "source_title": f"Source {group}",
                "raw_content": "Retained source text",
                "analyzed_json": json.dumps({"analysis_status": "complete", "learnings": ["retained learning"]})
                if group == 1
                else None,
            }
        )
    states = {"task": state}
    orch = SimpleNamespace(
        config={},
        step_repo=steps,
        step_result_repo=results,
        _get_step_depth=SomaticResearchOrchestrator._get_step_depth,
        ensure_state=lambda task_id: states[task_id],
        _get_state=lambda task_id: states[task_id],
        _state_mgr=SimpleNamespace(states=states),
    )
    manager = SimpleNamespace(task_repo=tasks, orchestrator=orch)
    return manager, journal, parsed, failed, results, receipts


def test_failed_digest_recovery_keeps_task_sources_and_original_receipts(recovery):
    manager, journal, parsed, failed, results, receipts = recovery
    original = receipts.get("task", failed.action_id)
    remaining = (original.deadline - datetime.now(UTC)).total_seconds()
    time.sleep(max(0, remaining) + 0.01)
    assert original.deadline < datetime.now(UTC)
    prepare_step_recovery(manager, "task", "digesting", "digest", "digest1")
    task = manager.task_repo.get("task")
    state = json.loads(task["orchestrator_state"])
    assert task["status"] == "active"
    assert state["phase"] == "digesting"
    assert state["current_depth"] == 1 and state["max_depth"] == 3
    assert state["all_findings"] == ["prior finding"]
    assert state["last_action_id"] == parsed.action_id
    assert datetime.fromisoformat(state["action_journal_policy"]["provider_policy"]["deadline"]) > datetime.now(
        UTC
    ) + timedelta(minutes=29)
    assert state["recovery_history"][0]["previous_policy"]["policy_hash"] == "original"
    assert state["action_journal_policy"]["policy_hash"] != "original"
    assert state["_rerun_group_ids"] == {"1": "digest1", "2": "digest2"}
    assert len(state["parsed_sources_cache"]) == 2
    assert len(results.get_by_task("task")) == 2
    assert receipts.get("task", failed.action_id) == original
    new = journal.begin("task", manager.orchestrator._get_state("task"), "digesting", {})
    assert new.dependency_ids == (parsed.action_id,)
    assert new.action_id != failed.action_id


def test_recovery_rejects_foreign_step_without_changes(recovery):
    manager, *_ = recovery
    before = manager.task_repo.get("task")
    with pytest.raises(ReceiptConflictError):
        prepare_step_recovery(manager, "task", "digesting", "digest", "foreign")
    assert manager.task_repo.get("task") == before


def test_recovery_attempt_allowance_is_new_but_old_receipts_remain(recovery):
    manager, journal, parsed, failed, results, receipts = recovery
    repo = ResearchProviderAttemptRepository(manager.task_repo._db_path)
    prepare_step_recovery(manager, "task", "digesting", "digest", "digest1")
    state = manager.orchestrator._get_state("task")
    current = journal.begin("task", state, "digesting", {})
    receipt = ProviderAttemptReceipt(
        attempt_id="new",
        task_id="task",
        action_id=current.action_id,
        request_id="new",
        provider="fixture",
        model="fixture",
        attempt_number=1,
        started_at=datetime.now(UTC),
    )
    repo.reserve(receipt, 1)
    with pytest.raises(ReceiptConflictError, match="budget exhausted"):
        repo.reserve(receipt.model_copy(update={"attempt_id": "second"}), 1)
    assert receipts.get("task", failed.action_id).status == "failed"


def test_late_old_action_cannot_replace_recovered_source_analysis(recovery):
    manager, journal, parsed, failed, results, receipts = recovery
    prepare_step_recovery(manager, "task", "digesting", "digest", "digest1")
    before = results.get_by_step("parallel_parse1")[0]["analyzed_json"]
    results.update_analysis("source1", '{"learnings":["late"]}', expected_action_id=failed.action_id)
    assert results.get_by_step("parallel_parse1")[0]["analyzed_json"] == before


@pytest.mark.asyncio
async def test_digest_recovery_reuses_complete_analysis_and_calls_model_only_for_missing(recovery, monkeypatch):
    manager, *_ = recovery
    prepare_step_recovery(manager, "task", "digesting", "digest", "digest1")
    orch = manager.orchestrator
    orch._get_semaphore = lambda: asyncio.Semaphore(2)
    orch.evidence_store_for = lambda task_id: None
    analyzer = AsyncMock(return_value={"analysis_status": "complete", "learnings": ["new learning"]})
    monkeypatch.setattr(digest, "analyze_source_content", analyzer)
    state = orch._get_state("task")
    output = await digest.parallel_digest_grouped(
        orch, "task", {1: "digest1", 2: "digest2"}, state["parsed_sources_cache"], ["one", "two"], "o", 1, 3
    )
    assert len(output) == 2
    assert analyzer.await_count == 1
    assert analyzer.call_args.args[2] == "https://example.org/2"
    assert output[0]["result"]["learnings"] == ["retained learning"]


@pytest.mark.parametrize("configured,expected", [(4, 4), (6, 6), (11, 6), (0, 1)])
def test_each_cycle_query_limit(configured, expected):
    assert query_limit({"max_queries": configured}, {}) == expected


@pytest.mark.asyncio
async def test_search_execution_and_preview_cap_reflection_queries_at_six(monkeypatch):
    from backend.services.research.steps import search
    from backend.services.research.task_state import SearchPayload, StepEnvelope

    orch = MagicMock()
    orch._state.config = {"research_orchestrator": {"max_queries": 6}}
    orch._state.llm_provider = None
    orch._create_or_update_step.return_value = "fixture-step"
    orch.default_top_n = 1
    orch.acquisition_enabled.return_value = False
    orch._get_state.return_value = {}
    orch._load_cache.return_value = {}
    finder = AsyncMock(return_value=[])
    monkeypatch.setattr(search, "web_search", finder)
    monkeypatch.setattr(search.asyncio, "sleep", AsyncMock())
    envelope = StepEnvelope(
        task_id="task",
        objective="o",
        current_depth=1,
        max_depth=3,
        budget=1,
        payload=SearchPayload(queries=[f"query {i}" for i in range(11)]),
    )
    preview = await search.SearchStep().preview(orch, envelope, {})
    assert len(preview["pending_queries"]) == 6
    await search.SearchStep().execute(orch, envelope)
    assert finder.await_count == 6


@pytest.mark.asyncio
@pytest.mark.parametrize("manual", [False, True])
async def test_recovered_step_continues_only_in_automatic_mode(recovery, manual):
    from backend.api.routes.research.steps import execute_step

    manager, *_ = recovery
    manager.orchestrator._state_mgr.locks = {}
    manager.get_task = manager.task_repo.get
    manager.config = {"manual_mode": manual}
    manager._active_tasks = {}
    manager.orchestrator_step = AsyncMock(return_value={"status": "completed"})
    manager.orchestrator.get_task_phase = lambda task_id: "consolidating"
    manager._execute_task = AsyncMock()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(research_task_manager=manager)))
    result = await execute_step("task", request, rerun_step_type="digest", rerun_step_id="digest1")
    assert result["status"] == "completed"
    if manual:
        manager._execute_task.assert_not_called()
    else:
        await manager._active_tasks["task"]
        manager._execute_task.assert_awaited_once_with("task", resume=True)


@pytest.mark.asyncio
async def test_auto_recovery_worker_resumes_existing_orchestrator_state():
    from backend.services.research.task_manager import ResearchTaskManager

    manager = SimpleNamespace(
        _get_semaphore=lambda: asyncio.Semaphore(1),
        task_repo=MagicMock(),
        orchestrator=SimpleNamespace(execute=AsyncMock(return_value={})),
        complete=MagicMock(),
        fail=MagicMock(),
        config={"manual_mode": True},
        _active_tasks={},
    )
    manager.task_repo.get.side_effect = [{"title": "fixture", "status": "active"}, {"status": "completed"}]
    await ResearchTaskManager._execute_task(manager, "task", resume=True)
    manager.orchestrator.execute.assert_awaited_once_with("task", resume=True)
    manager.complete.assert_not_called()


def test_recovery_group_id_cannot_reuse_another_phase_step(recovery):
    manager, *_ = recovery
    orch = manager.orchestrator
    state = orch._get_state("task")
    state["_rerun_group_ids"] = {"1": "digest1"}
    new_id = SomaticResearchOrchestrator._create_or_update_step(orch, state, "task", "search", query_group=1)
    assert new_id != "digest1"
    assert orch.step_repo.get("digest1")["status"] == "failed"
    assert orch.step_repo.get(new_id)["step_type"] == "search"


def test_recovery_retains_source_identity_only_for_matching_representation(recovery):
    from backend.services.research.task_state import serialize_research_state

    manager, *_ = recovery
    state = manager.orchestrator._get_state("task")
    state["parsed_sources_cache"] = [
        {
            "url": "https://example.org/1",
            "content": "another representation",
            "source_id": "wrong",
            "source_version": "wrong",
        },
    ]
    manager.task_repo.update("task", orchestrator_state=serialize_research_state(state))
    prepare_step_recovery(manager, "task", "digesting", "digest", "digest1")
    restored = manager.orchestrator._get_state("task")["parsed_sources_cache"][0]
    assert "source_id" not in restored and "source_version" not in restored
    assert restored["content"] != "another representation"
