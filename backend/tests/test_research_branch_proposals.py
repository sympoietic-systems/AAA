import asyncio
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from backend.services.research.orchestrator import SomaticResearchOrchestrator
from backend.services.research.steps.base import ResearchStepRegistry
from backend.services.research.task_state import ReflectionPayload, StepOutput
from backend.storage.database import init_db
from backend.storage.repositories.research.action_receipt import ReceiptConflictError
from backend.storage.repositories.research.branch_proposal import ResearchBranchProposalRepository
from backend.storage.repositories.research.research_task import ResearchTaskRepository
from backend.storage.research_branch_proposal import BranchProposalDraft, BranchScope


def draft(anchors):
    return BranchProposalDraft(
        question="Compare the validation requirements",
        rationale="The quoted records use different validation norms",
        cut_kind="validation_norm",
        witness_segment_ids=tuple(anchors[:2]),
        overlap="Shared parent question",
        risk="Fragmenting coupled claims",
        parent_budget_reserve_usd=0.1,
        scopes=(
            BranchScope(
                scope_id="a",
                question="Inspect experimental claims",
                retrieval_vocabulary=("experiment",),
                validation_norm="Empirical replication",
                attempt_allocation=8,
                budget_allocation_usd=0.1,
            ),
            BranchScope(
                scope_id="b",
                question="Inspect interpretive claims",
                retrieval_vocabulary=("interpretation",),
                validation_norm="Situated interpretation",
                attempt_allocation=8,
                budget_allocation_usd=0.1,
            ),
        ),
    )


@pytest.fixture
def setup(tmp_path, request, monkeypatch):
    path = str(tmp_path / "proposals.db")
    init_db(path).close()
    repo = ResearchTaskRepository(path)
    repo.create(
        dict(
            id="task",
            title="Fixture",
            objective="Compare claims within one parent question",
            trigger_source="test",
            status="active",
            priority=1,
            max_depth=2,
            max_breadth=2,
            budget_limit_usd=0.5,
            subresearch_policy=getattr(request, "param", "propose"),
        )
    )
    app = SimpleNamespace(
        config={"research_orchestrator": {"action_receipts_enabled": True}, "research_tasks": {"manual_mode": True}},
        research_task_repo=repo,
        research_plan_repo=None,
        research_step_repo=None,
        research_meta_log_repo=None,
    )
    orch = SomaticResearchOrchestrator(app)
    orch.init_task("task")
    orch._get_state("task")["phase"] = "reflection"
    orch._metabolize_step = AsyncMock()
    import backend.services.research.orchestrator as orchestration

    monkeypatch.setattr(orchestration, "validate_safe_url", lambda url: url)
    from backend.services.research.acquisition import AcquisitionRuntime

    monkeypatch.setattr(
        orchestration,
        "AcquisitionRuntime",
        lambda policy, **kwargs: AcquisitionRuntime(policy, validator=lambda url: url, **kwargs),
    )

    async def execute(_, envelope):
        async def load():
            return "Experimental evidence. " * 100 + "Interpretive evidence. " * 100

        await orch.acquire("task", "https://fixture.test/evidence", load)
        snapshot = await asyncio.to_thread(orch._evidence_store.repo.afferent_snapshot, "task")
        return StepOutput(payload=ReflectionPayload(), branch_proposal=draft(snapshot[0]["segment_ids"]))

    processor = SimpleNamespace(execute=execute)
    monkeypatch.setattr(ResearchStepRegistry, "get_step", lambda phase: processor)
    return orch, repo, app, ResearchBranchProposalRepository(path)


@pytest.mark.asyncio
async def test_v113_waiting_is_durable_and_spends_no_child_budget(setup):
    orch, tasks, app, proposals = setup
    result = await orch.execute_step("task")
    assert result["status"] == "waiting_for_branch_approval"
    assert tasks.get("task")["status"] == "waiting_for_branch_approval"
    proposal = proposals.current("task")
    assert proposal.status == "pending"
    assert len(tasks.list_all()) == 1
    restarted = SomaticResearchOrchestrator(app)
    assert restarted.init_task("task")["phase"] == "waiting_for_branch_approval"
    paused = await restarted.execute_step("task")
    assert paused["status"] == "waiting_for_branch_approval"
    assert paused["proposal_id"] == proposal.proposal_id
    await orch.aclose()


@pytest.mark.parametrize("setup", ["off"], indirect=True)
@pytest.mark.asyncio
async def test_v113_off_policy_ignores_proposal_and_continues_single_line(setup):
    orch, tasks, _, proposals = setup
    result = await orch.execute_step("task")
    assert result["next_phase"] == "evaluating"
    assert proposals.current("task") is None
    assert len(tasks.list_all()) == 1
    await orch.aclose()


@pytest.mark.asyncio
async def test_v113_approve_edit_is_immutable_and_preserves_deadline(setup):
    orch, tasks, app, proposals = setup
    await orch.execute_step("task")
    original = proposals.current("task")
    before = json.loads(tasks.get("task")["orchestrator_state"])["action_journal_policy"]
    edits = (
        original.draft.scopes[0].model_copy(update={"question": "Narrow experimental claims"}),
        original.draft.scopes[1],
    )
    with pytest.raises(ReceiptConflictError, match="parent objective"):
        proposals.resolve("task", original.proposal_id, "approved", scopes=edits, manual=True)
    approved = proposals.resolve(
        "task", original.proposal_id, "approved", scopes=edits, boundary_acknowledged=True, manual=True
    )
    assert approved.approved_scopes == edits
    assert (
        proposals.resolve(
            "task", original.proposal_id, "approved", scopes=edits, boundary_acknowledged=True, manual=True
        )
        == approved
    )
    with pytest.raises(ReceiptConflictError, match="immutable"):
        proposals.resolve("task", original.proposal_id, "approved", manual=True)
    state = SomaticResearchOrchestrator(app).init_task("task")
    assert state["phase"] == original.resume_phase
    assert state["action_journal_policy"] == before
    assert len(tasks.list_all()) == 1
    await orch.aclose()


@pytest.mark.asyncio
async def test_v113_decline_resumes_parent_without_spend(setup):
    orch, tasks, app, proposals = setup
    await orch.execute_step("task")
    original = proposals.current("task")
    resolved = proposals.resolve("task", original.proposal_id, "declined", manual=True)
    assert resolved.status == "declined"
    assert tasks.get("task")["status"] == "active"
    assert SomaticResearchOrchestrator(app).init_task("task")["phase"] == original.resume_phase
    assert len(tasks.list_all()) == 1
    with pytest.raises(ReceiptConflictError, match="resolved"):
        proposals.resolve("task", original.proposal_id, "approved", boundary_acknowledged=True)
    await orch.aclose()


@pytest.mark.parametrize("seconds,expected", [(180, "active"), (3600, "partial")])
@pytest.mark.asyncio
async def test_v113_expiry_never_approves_and_respects_parent_deadline(setup, monkeypatch, seconds, expected):
    orch, tasks, _, proposals = setup
    await orch.execute_step("task")
    original = proposals.current("task")
    import backend.storage.repositories.research.branch_proposal as module

    future = datetime.now(UTC) + timedelta(seconds=seconds)
    monkeypatch.setattr(module, "datetime", SimpleNamespace(now=lambda _: future, fromisoformat=datetime.fromisoformat))
    assert proposals.expired_waiting() == [("task", original.proposal_id)]
    expired = proposals.resolve("task", original.proposal_id, "approved", boundary_acknowledged=True, manual=True)
    assert expired.status == "expired" and expired.approved_scopes is None
    assert tasks.get("task")["status"] == expected
    assert len(tasks.list_all()) == 1
    await orch.aclose()


@pytest.mark.asyncio
async def test_v115_edits_cannot_consume_parent_reserve(setup):
    orch, tasks, _, proposals = setup
    await orch.execute_step("task")
    original = proposals.current("task")
    edits = tuple(scope.model_copy(update={"budget_allocation_usd": 0.5}) for scope in original.draft.scopes)
    with pytest.raises(ReceiptConflictError, match="budget"):
        proposals.resolve(
            "task", original.proposal_id, "approved", scopes=edits, boundary_acknowledged=True, manual=True
        )
    assert proposals.current("task").status == "pending"
    await orch.aclose()


def test_v113_facet_count_coupling_and_unbounded_inputs_cannot_form_cut():
    original = draft(["one", "two"])
    with pytest.raises(ValidationError, match="Coupled"):
        BranchProposalDraft.model_validate({**original.model_dump(), "coupled_relational": True})
    with pytest.raises(ValidationError):
        BranchProposalDraft.model_validate({**original.model_dump(), "witness_segment_ids": []})
    with pytest.raises(ValidationError):
        BranchScope.model_validate({**original.scopes[0].model_dump(), "retrieval_vocabulary": ["x" * 201]})


@pytest.mark.asyncio
async def test_v113_review_api_exposes_exact_witnesses_and_requires_boundary_acknowledgment(setup):
    import httpx
    from fastapi import FastAPI

    from backend.api.routes.research.branch_proposals import router
    from backend.services.research.task_manager import ResearchTaskManager

    orch, tasks, app_state, proposals = setup
    await orch.execute_step("task")
    proposal = proposals.current("task")
    manager = ResearchTaskManager(app_state)
    manager._orchestrator = orch
    app = FastAPI()
    app.state.research_task_manager = manager
    app.include_router(router)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://fixture") as client:
        response = await client.get("/research/tasks/task/branch-proposal")
        assert response.status_code == 200
        assert len(response.json()["witnesses"]) == 2
        assert all(item["text"] for item in response.json()["witnesses"])
        url = f"/research/tasks/task/branch-proposals/{proposal.proposal_id}/approve"
        assert (await client.post(url, json={"boundary_acknowledged": False})).status_code == 409
        assert (await client.post(url, json={"boundary_acknowledged": True})).json()["status"] == "approved"
        assert (
            await client.post(f"/research/tasks/task/branch-proposals/{proposal.proposal_id}/decline")
        ).status_code == 409
    assert len(tasks.list_all()) == 1
    await orch.aclose()


@pytest.mark.asyncio
async def test_v113_auto_mode_returns_waiting_without_false_completion(setup):
    orch, tasks, _, _ = setup
    await orch.execute_step("task")
    result = await orch.execute("task")
    assert result["status"] == "waiting_for_branch_approval"
    assert tasks.get("task")["status"] == "waiting_for_branch_approval"
    await orch.aclose()


@pytest.mark.asyncio
async def test_v113_expiry_worker_restores_parent_without_child_work(setup, monkeypatch):
    import backend.storage.repositories.research.branch_proposal as module
    from backend.services.research.task_manager import ResearchTaskManager

    orch, tasks, app, proposals = setup
    await orch.execute_step("task")
    manager = ResearchTaskManager(app)
    manager._orchestrator = orch
    future = datetime.now(UTC) + timedelta(seconds=180)
    monkeypatch.setattr(module, "datetime", SimpleNamespace(now=lambda _: future, fromisoformat=datetime.fromisoformat))
    await manager.start_branch_watch()
    for _ in range(100):
        await asyncio.sleep(0.005)
        if proposals.current("task").status == "expired":
            break
    await manager.close_branch_watch()
    assert proposals.current("task").status == "expired"
    assert tasks.get("task")["status"] == "active"
    assert len(tasks.list_all()) == 1
    await orch.aclose()


@pytest.mark.asyncio
async def test_v113_cancelled_parent_closes_proposal_without_child_spend(setup):
    from backend.services.research.task_manager import ResearchTaskManager

    orch, tasks, app, proposals = setup
    await orch.execute_step("task")
    manager = ResearchTaskManager(app)
    manager._orchestrator = orch
    manager.transition("task", "cancelled")
    proposal = proposals.current("task")
    assert proposal.status == "declined" and proposal.resolution_reason == "parent_cancelled"
    assert tasks.get("task")["status"] == "cancelled"
    assert len(tasks.list_all()) == 1
    with pytest.raises(ReceiptConflictError):
        proposals.resolve("task", proposal.proposal_id, "approved", boundary_acknowledged=True)
    await orch.aclose()


@pytest.mark.asyncio
async def test_v113_per_task_opt_in_preserves_context_and_restores_expiry_monitor(setup):
    from backend.services.research.task_manager import ResearchTaskManager

    orch, tasks, app, proposals = setup
    tasks.create(
        dict(
            id="explicit",
            title="Context",
            objective="Keep one parent question",
            trigger_source="test",
            status="active",
            priority=1,
            max_depth=1,
            max_breadth=1,
            budget_limit_usd=0.5,
            subresearch_policy="propose",
            orchestrator_state=json.dumps({"previous_context": "Document context"}),
        )
    )
    app.config["research_orchestrator"]["action_receipts_enabled"] = False
    other = SomaticResearchOrchestrator(app)
    state = other.init_task("explicit")
    assert state["action_journal_policy"]["enabled"]
    assert state["action_journal_policy"]["subresearch_policy"] == "propose"
    assert state["previous_context"] == "Document context"
    assert (
        json.loads(tasks.get("explicit")["orchestrator_state"])["action_journal_policy"]
        == state["action_journal_policy"]
    )
    await orch.execute_step("task")
    manager = ResearchTaskManager(app)
    await manager.start_branch_watch()
    assert manager._branch_watch is not None
    await manager.close_branch_watch()
    await orch.aclose()
    await other.aclose()
