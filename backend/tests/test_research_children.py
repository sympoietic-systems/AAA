import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.services.research import action_scheduler
from backend.services.research.action_journal import InterruptedResearchActionError, ResearchActionJournal
from backend.services.research.orchestrator import SomaticResearchOrchestrator
from backend.services.research.steps.base import ResearchStepRegistry
from backend.services.research.steps.branch_gather import BranchGatherStep
from backend.services.research.task_state import DigestPayload, ParsePayload, SearchPayload, StepOutput
from backend.storage.repositories.research.action_receipt import ReceiptConflictError, ResearchActionReceiptRepository
from backend.storage.repositories.research.child_run import ResearchChildRunRepository
from backend.storage.repositories.research.provider_attempt import ResearchProviderAttemptRepository
from backend.storage.research_children import ChildEvidencePacket
from backend.storage.research_evidence import EvidenceBundle
from backend.storage.research_receipts import ProviderAttemptReceipt
from backend.tests.test_research_branch_proposals import setup as proposal_setup


@pytest.fixture
def setup(tmp_path, request, monkeypatch):
    return proposal_setup.__wrapped__(tmp_path, request, monkeypatch)


async def approved(setup):
    orch, tasks, app, proposals = setup
    await orch.execute_step("task")
    proposal = proposals.current("task")
    proposals.resolve("task", proposal.proposal_id, "approved", boundary_acknowledged=True, manual=True)
    orch._state_mgr.states.pop("task", None)
    return orch, tasks, app, proposals


def gathering_action(orch):
    state = orch.init_task("task")
    assert state["phase"] == "branch_gathering"
    receipt = ResearchActionJournal(ResearchActionReceiptRepository(orch.task_repo._db_path)).begin(
        "task", state, "branch_gathering", {}
    )
    return receipt


@pytest.mark.asyncio
async def test_v113_v115_two_approved_scopes_isolated_and_idempotent(setup):
    orch, tasks, app, proposals = await approved(setup)
    action = gathering_action(orch)
    repo = ResearchChildRunRepository(tasks._db_path)
    children = repo.allocate("task", action.action_id)
    assert len(children) == 2
    assert repo.allocate("task", action.action_id) == children
    assert len(tasks.list_all()) == 3
    for row in children:
        child = json.loads(tasks.get(row["child_task_id"])["orchestrator_state"])
        parent = orch._get_state("task")
        assert (
            child["action_journal_policy"]["provider_policy"]["deadline"]
            == parent["action_journal_policy"]["provider_policy"]["deadline"]
        )
        assert child["action_journal_policy"]["provider_policy"]["max_task_attempts"] == 8
        assert child["action_journal_policy"]["subresearch_policy"] == "off"
        assert action_scheduler.reason("consolidating", child, []) == "child_capability_forbidden"
        assert action_scheduler.reason("branch_gathering", child, []) == "child_capability_forbidden"
    restarted = SomaticResearchOrchestrator(app)
    assert restarted.init_task(children[0]["child_task_id"])["research_child"]["parent_task_id"] == "task"
    assert repo.start(children[0]["child_task_id"], action.action_id)
    with pytest.raises(ReceiptConflictError, match="Interrupted"):
        repo.start(children[0]["child_task_id"], action.action_id)
    await orch.aclose()


@pytest.mark.asyncio
async def test_v115_child_attempt_caps_and_parent_reserve(setup):
    orch, tasks, _, _ = await approved(setup)
    parent_action = gathering_action(orch)
    children_repo = ResearchChildRunRepository(tasks._db_path)
    children = children_repo.allocate("task", parent_action.action_id)
    attempts = ResearchProviderAttemptRepository(tasks._db_path)
    child_id = children[0]["child_task_id"]
    children_repo.start(child_id, parent_action.action_id)
    state = orch.init_task(child_id)
    child_action = orch._action_journal.begin(child_id, state, "searching", {})

    def receipt():
        return ProviderAttemptReceipt(
            attempt_id=str(uuid.uuid4()),
            task_id=child_id,
            action_id=child_action.action_id,
            request_id=str(uuid.uuid4()),
            attempt_number=1,
            provider="nvidia_fixture",
            budget_reserved_usd=0,
            model="fixture",
            started_at=datetime.now(UTC),
        )

    for _ in range(8):
        attempts.reserve(receipt(), 256)
    with pytest.raises(ReceiptConflictError, match="Child attempt allocation"):
        attempts.reserve(receipt(), 256)
    tasks.transition_status("task", "cancelled")
    children_repo.cancel_parent("task")
    with pytest.raises(ReceiptConflictError, match="current running action"):
        attempts.reserve(receipt(), 256)
    assert attempts.summary(child_id) == {"pending": 8}
    await orch.aclose()


@pytest.mark.asyncio
async def test_v114_parent_alone_merges_raw_archives_and_conflicts(setup, monkeypatch):
    orch, tasks, _, proposals = await approved(setup)

    async def execute(_, envelope):
        child_id = envelope.task_id
        phase = orch._get_state(child_id)["phase"]
        if phase == "searching":
            return StepOutput(
                payload=SearchPayload(search_results=[{"url": "https://fixture.test/shared"}]),
                signal_flags={"has_results": True},
            )
        if phase == "parsing":

            async def load():
                return "Common raw source with conflicting interpretations"

            await orch.acquire(child_id, "https://fixture.test/shared", load)
            return StepOutput(
                payload=ParsePayload(parsed_sources=[{"url": "https://fixture.test/shared", "content": "raw"}]),
                signal_flags={"has_parsed_content": True},
            )
        scope = orch._get_state(child_id)["research_child"]["scope"]["scope_id"]
        return StepOutput(payload=DigestPayload(learnings=[scope]), new_findings=[f"scope {scope}: incompatible claim"])

    monkeypatch.setattr(
        ResearchStepRegistry,
        "get_step",
        lambda phase: BranchGatherStep() if phase == "branch_gathering" else SimpleNamespace(execute=execute),
    )
    orch.init_task("task")
    result = await orch.execute_step("task")
    assert result["next_phase"] == "consolidating"
    rows = ResearchChildRunRepository(tasks._db_path).list_parent("task")
    assert [row["status"] for row in rows] == ["complete", "complete"]
    assert orch._metabolize_step.await_count == 1  # only parent gathering has findings; children remain isolated
    assert orch._metabolize_step.await_args.args[:2] == ("task", "branch_gathering")
    for row in rows:
        packet = json.loads(row["packet_json"])
        assert packet["evidence"]["segments"][0]["text"] == "Common raw source with conflicting interpretations"
        assert packet["evidence"]["acquisitions"][0]["outcome"] == "fetched"
        assert packet["evidence_role"] == "child_archive_unreviewed"
        assert packet["unresolved_objections"] == ["child_semantic_support_unreviewed"]
    context = orch._get_state("task")["child_evidence_context"]
    assert all(row["child_task_id"] in context for row in rows)
    assert len(orch._get_state("task")["all_findings"]) == 2
    receipt = orch._action_journal.repo.get("task", result["action_id"])
    assert set(receipt.observation.child_task_ids) == {row["child_task_id"] for row in rows}
    assert len(receipt.observation.child_packet_hashes) == 2
    # An explicitly repeated gather reuses the committed archives without
    # spending again or appending the same interpretations to the parent twice.
    orch._get_state("task")["phase"] = "branch_gathering"
    orch._persist_state("task")
    repeated = await orch.execute_step("task")
    assert repeated["next_phase"] == "consolidating"
    assert len(orch._get_state("task")["all_findings"]) == 2
    assert ResearchChildRunRepository(tasks._db_path).list_parent("task") == rows
    assert "shared_source_groups" in orch._get_state("task")["child_evidence_context"]
    await orch.aclose()


@pytest.mark.asyncio
async def test_v119_same_content_refetch_preserves_both_observations(setup, monkeypatch):
    orch, tasks, _, _ = setup
    state = orch._get_state("task")
    import backend.services.research.orchestrator as orchestration
    from backend.services.research.acquisition import AcquisitionRuntime

    monkeypatch.setattr(
        orchestration,
        "AcquisitionRuntime",
        lambda policy, **kwargs: AcquisitionRuntime(
            policy.model_copy(update={"cache_ttl_seconds": 0}), validator=lambda url: url, **kwargs
        ),
    )
    orch._action_journal.begin("task", state, "parsing", {})

    async def load():
        return "Unchanged source"

    first = await orch.acquire("task", "https://fixture.test/unchanged", load)
    second = await orch.acquire("task", "https://fixture.test/unchanged", load)
    assert not second.cache_hit and first.observed_at < second.observed_at
    bundle = EvidenceBundle.model_validate(orch._evidence_store.repo.export_bundle("task"))
    assert len(bundle.sources) == 2
    assert bundle.sources[0].artifact.representation_hash == bundle.sources[1].artifact.representation_hash
    assert len(orch._evidence_store.repo.afferent_snapshot("task")) == 0  # both TTLs expired
    await orch.aclose()


@pytest.mark.asyncio
async def test_v115_monetary_allocations_require_declared_ceiling(setup):
    orch, tasks, _, _ = await approved(setup)
    parent_action = gathering_action(orch)
    children = ResearchChildRunRepository(tasks._db_path)
    rows = children.allocate("task", parent_action.action_id)
    child_id = rows[0]["child_task_id"]
    children.start(child_id, parent_action.action_id)
    state = orch.init_task(child_id)
    action = orch._action_journal.begin(child_id, state, "searching", {})
    attempts = ResearchProviderAttemptRepository(tasks._db_path)
    base = dict(
        task_id=child_id,
        action_id=action.action_id,
        request_id="request",
        attempt_number=1,
        provider="unpriced",
        model="fixture",
        started_at=datetime.now(UTC),
    )
    with pytest.raises(ReceiptConflictError, match="declared monetary ceiling"):
        attempts.reserve(ProviderAttemptReceipt(attempt_id="unpriced", **base), 8)
    base["provider"] = "priced_fixture"
    attempts.reserve(ProviderAttemptReceipt(attempt_id="priced-1", budget_reserved_usd=0.06, **base), 8)
    with pytest.raises(ReceiptConflictError, match="Child monetary allocation"):
        attempts.reserve(ProviderAttemptReceipt(attempt_id="priced-2", budget_reserved_usd=0.06, **base), 8)
    assert attempts.summary(child_id) == {"pending": 1}
    await orch.aclose()


@pytest.mark.asyncio
async def test_v116_terminal_delivery_immutable_and_cancel_revokes_late_packet(setup):
    orch, tasks, _, _ = await approved(setup)
    parent_action = gathering_action(orch)
    repo = ResearchChildRunRepository(tasks._db_path)
    rows = repo.allocate("task", parent_action.action_id)
    child_id = rows[0]["child_task_id"]
    repo.start(child_id, parent_action.action_id)
    packet = ChildEvidencePacket(
        child_task_id=child_id,
        parent_task_id="task",
        proposal_id=rows[0]["proposal_id"],
        scope=json.loads(rows[0]["allocation_json"]),
        status="partial",
        evidence=EvidenceBundle.model_validate(orch._evidence_store.repo.export_bundle(child_id)),
        unresolved_objections=("fixture interruption",),
    )
    repo.finish(packet, parent_action.action_id)
    repo.finish(packet, parent_action.action_id)
    with pytest.raises(ReceiptConflictError, match="immutable"):
        repo.finish(
            packet.model_copy(update={"interpretations": ("late fabricated conclusion",)}), parent_action.action_id
        )
    second = rows[1]
    repo.start(second["child_task_id"], parent_action.action_id)
    tasks.transition_status("task", "cancelled")
    repo.cancel_parent("task")
    stale = packet.model_copy(
        update={
            "child_task_id": second["child_task_id"],
            "scope": packet.scope.model_validate_json(second["allocation_json"]),
            "evidence": EvidenceBundle.model_validate(orch._evidence_store.repo.export_bundle(second["child_task_id"])),
        }
    )
    with pytest.raises(ReceiptConflictError, match="revoked"):
        repo.finish(stale, parent_action.action_id)
    assert repo.list_parent("task")[0]["packet_json"] == packet.model_dump_json()
    exported = EvidenceBundle.model_validate(orch._evidence_store.repo.export_bundle("task"))
    assert exported.child_archives[0].evidence.task_id == child_id
    assert exported.child_archives[0].unresolved_objections == ("fixture interruption",)
    await orch.aclose()


@pytest.mark.asyncio
async def test_v113_unapproved_parent_cannot_allocate(setup):
    orch, tasks, _, _ = setup
    repo = ResearchChildRunRepository(tasks._db_path)
    with pytest.raises(ReceiptConflictError, match="current parent"):
        repo.allocate("task", "invented-action")
    assert len(tasks.list_all()) == 1
    await orch.aclose()


@pytest.mark.asyncio
async def test_v115_failure_preserves_raw_evidence_and_other_scope(setup, monkeypatch):
    orch, tasks, _, _ = await approved(setup)

    async def execute(_, envelope):
        state = orch._get_state(envelope.task_id)
        if state["phase"] == "searching":
            return StepOutput(
                payload=SearchPayload(search_results=[{"url": "https://fixture.test/conflict"}]),
                signal_flags={"has_results": True},
            )

        async def load():
            return "Raw disagreement survives digest failure"

        await orch.acquire(envelope.task_id, "https://fixture.test/conflict", load)
        if state["research_child"]["scope"]["scope_id"] == "a":
            raise RuntimeError("fixture failure")
        return StepOutput(payload=ParsePayload(parsed_sources=[]))

    monkeypatch.setattr(
        ResearchStepRegistry,
        "get_step",
        lambda phase: BranchGatherStep() if phase == "branch_gathering" else SimpleNamespace(execute=execute),
    )
    orch.init_task("task")
    result = await orch.execute_step("task")
    assert result["status"] == "partial"
    rows = ResearchChildRunRepository(tasks._db_path).list_parent("task")
    assert [row["status"] for row in rows] == ["failed", "partial"]
    bundle = EvidenceBundle.model_validate(orch._evidence_store.repo.export_bundle("task"))
    assert len(bundle.child_archives) == 2
    assert all(
        child.evidence.segments[0].text == "Raw disagreement survives digest failure" for child in bundle.child_archives
    )
    assert orch._get_state("task")["delivery_degraded"]
    await orch.aclose()


@pytest.mark.asyncio
async def test_v115_interrupted_child_cannot_replay_after_restart(setup):
    orch, tasks, app, _ = await approved(setup)
    action = gathering_action(orch)
    repo = ResearchChildRunRepository(tasks._db_path)
    rows = repo.allocate("task", action.action_id)
    repo.start(rows[0]["child_task_id"], action.action_id)
    restarted = SomaticResearchOrchestrator(app)
    before = repo.list_parent("task")
    with pytest.raises(InterruptedResearchActionError, match="Interrupted research action"):
        await restarted.execute_step("task")
    assert repo.list_parent("task") == before
    assert len(tasks.list_all()) == 3
    bundle = EvidenceBundle.model_validate(orch._evidence_store.repo.export_bundle("task"))
    assert len(bundle.child_archives) == 2
    assert all(child.status == "partial" for child in bundle.child_archives)
    await orch.aclose()


@pytest.mark.asyncio
async def test_v115_child_family_cannot_spend_parent_verification_reserve(setup):
    orch, tasks, _, _ = await approved(setup)
    parent_action = gathering_action(orch)
    attempts = ResearchProviderAttemptRepository(tasks._db_path)

    def intent(task_id, action_id):
        return ProviderAttemptReceipt(
            attempt_id=str(uuid.uuid4()),
            task_id=task_id,
            action_id=action_id,
            request_id=str(uuid.uuid4()),
            attempt_number=1,
            provider="nvidia_fixture",
            model="fixture",
            started_at=datetime.now(UTC),
            budget_reserved_usd=0,
        )

    for _ in range(40):
        attempts.reserve(intent("task", parent_action.action_id), 64)
    children = ResearchChildRunRepository(tasks._db_path)
    rows = children.allocate("task", parent_action.action_id)
    for _ in range(2):
        attempts.reserve(intent("task", parent_action.action_id), 64)
    for i, row in enumerate(rows):
        child_id = row["child_task_id"]
        children.start(child_id, parent_action.action_id)
        state = orch.init_task(child_id)
        action = orch._action_journal.begin(child_id, state, "searching", {})
        for _ in range(8 if i == 0 else 6):
            attempts.reserve(intent(child_id, action.action_id), 8)
        if i == 1:
            with pytest.raises(ReceiptConflictError, match="Parent verification reserve"):
                attempts.reserve(intent(child_id, action.action_id), 8)
    family = sum(sum(attempts.summary(row["child_task_id"]).values()) for row in rows) + sum(
        attempts.summary("task").values()
    )
    assert family == 56  # original ceiling64 minus protected reserve8
    await orch.aclose()


@pytest.mark.asyncio
async def test_v114_parent_cortex_prompt_preserves_conflict_and_ignores_stale_preview(monkeypatch):
    from backend.services.research.steps.consolidate import run_consolidation

    orch = MagicMock()
    context = json.dumps(
        {
            "child_a": {"claim": "support", "norm": "replication"},
            "child_b": {"claim": "contrary", "norm": "situated interpretation"},
        }
    )
    orch._get_state.return_value = {"child_evidence_context": context}
    orch._get_cached_phase.return_value = {
        "current_depth": 0,
        "persona": "parent persona",
        "system_prompt": "parent system",
        "user_prompt": "STALE_PREVIEW",
    }
    orch.step_repo = None
    orch.step_result_repo = None
    orch._get_parsed_urls.return_value = []
    orch._format_reflection_markdown.return_value = ""
    generated = AsyncMock(return_value={"json_data": {"completeness_score": 0.5}})
    monkeypatch.setattr("backend.services.research.steps.consolidate.generate_unified", generated)
    await run_consolidation(orch, "parent", "one parent objective", "one goal", 0, 1, ["existing finding"], {})
    prompt = generated.call_args.kwargs["user_prompt"]
    assert context in prompt and "existing finding" in prompt
    assert "preserve contrary claims" in prompt and "Shared sources are not independent corroboration" in prompt
    assert "STALE_PREVIEW" not in prompt


@pytest.mark.asyncio
async def test_v114_synthesis_counts_unique_parent_and_child_sources(setup, monkeypatch):
    from backend.services.research.steps import synthesize
    from backend.services.research.task_state import StepEnvelope, SynthesizePayload
    from backend.storage.research_evidence import SourceArtifact, SourceSnapshot, text_hash

    orch, tasks, _, _ = await approved(setup)
    action = gathering_action(orch)
    repo = ResearchChildRunRepository(tasks._db_path)
    rows = repo.allocate("task", action.action_id)
    text = "Captured source evidence with explicit limits. " * 10
    for row in rows:
        child_id = row["child_task_id"]
        repo.start(child_id, action.action_id)
        snapshots = tuple(
            SourceSnapshot(
                artifact=SourceArtifact(
                    task_id=child_id,
                    source_id=str(index),
                    source_version="1",
                    canonical_url=url,
                    representation="text",
                    representation_hash=text_hash(text),
                    fetch_status="available",
                ),
                representation_text=text,
            )
            for index, url in enumerate(("https://example.org/shared", "https://example.org/child"))
        )
        repo.finish(
            ChildEvidencePacket(
                child_task_id=child_id,
                parent_task_id="task",
                proposal_id=row["proposal_id"],
                scope=json.loads(row["allocation_json"]),
                status="partial",
                evidence=EvidenceBundle(task_id=child_id, sources=snapshots),
            ),
            action.action_id,
        )
    monkeypatch.setattr(orch, "_get_parsed_urls", lambda _: [{"url": "https://example.org/shared", "status": "ok"}])
    monkeypatch.setattr(synthesize, "run_synthesis", AsyncMock(return_value="Bounded report"))
    monkeypatch.setattr(orch, "_create_or_update_step", lambda *args: "fixture-synthesis")
    orch._state.research_step_result_repo = object()
    output = await synthesize.SynthesizeStep().execute(
        orch,
        StepEnvelope(
            task_id="task",
            objective="Compare evidence",
            max_depth=1,
            budget=1.0,
            current_depth=0,
            all_findings=[],
            payload=SynthesizePayload(sources_analyzed=99),
        ),
    )
    assert output.payload.sources_analyzed == 2
    assert tasks.get("task")["branches_created"] == 2
    await orch.aclose()
