import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.services.research.evidence_store import ResearchEvidenceStore
from backend.storage.database import init_db
from backend.storage.repositories.research.action_receipt import ReceiptConflictError, ResearchActionReceiptRepository
from backend.storage.repositories.research.evidence import ResearchEvidenceRepository
from backend.storage.repositories.research.research_task import ResearchTaskRepository
from backend.storage.research_evidence import (
    ClaimEvidence,
    EvidenceBundle,
    ResearchContract,
    RubricItem,
    SourceReference,
)
from backend.storage.research_receipts import ResearchActionReceipt


@pytest.fixture
def repo(tmp_path: Path):
    path = str(tmp_path / "evidence.db")
    init_db(path).close()
    tasks = ResearchTaskRepository(path)
    for task_id in ("task", "other"):
        tasks.create(
            dict(
                id=task_id,
                title="Evidence",
                objective="Observe support",
                trigger_source="test",
                status="queued",
                priority=1,
                max_depth=1,
                max_breadth=1,
                budget_limit_usd=1,
            )
        )
    repository = ResearchEvidenceRepository(path)
    repository.put_contract(
        ResearchContract(
            task_id="task",
            objective="Observe support",
            policy_version=3,
            rubric=(RubricItem(rubric_id="hard", description="Keep contrary evidence"),),
            resource_ceilings={"tokens": 100},
        )
    )
    return repository


def source(repo, text="α🙂\nContrary finding."):
    return ResearchEvidenceStore(repo).record_text("task", "https://example.org/report#section", text)


def claim(artifact, segment, **changes):
    return ClaimEvidence.model_validate(
        dict(
            task_id="task",
            claim_id="claim",
            contract_revision=1,
            text="A finding requiring review",
            rubric_ids=["hard"],
            source_lineage=[SourceReference(source_id=artifact.source_id, source_version=artifact.source_version)],
            contrary_segment_ids=[segment.segment_id],
            citation_status="resolvable",
            **changes,
        )
    )


def test_restart_export_resolves_unicode_spans_and_retains_contrary(repo):
    artifact, segments = source(repo)
    item = claim(artifact, segments[0], unresolved_objections=["Contrary finding remains unresolved"])
    repo.put_claim(item)
    restarted = ResearchEvidenceRepository(repo._db_path)
    bundle = EvidenceBundle.model_validate_json(
        EvidenceBundle.model_validate(restarted.export_bundle("task")).model_dump_json()
    )
    saved_source, saved_segment = bundle.resolve_locator(segments[0].locator())
    assert saved_source == artifact
    assert saved_segment.text == "α🙂\nContrary finding."
    assert saved_segment.end == len(saved_segment.text)
    assert bundle.claims[0].contrary_segment_ids == (saved_segment.segment_id,)
    assert bundle.claims[0].support_status == "unverified"
    assert "original_bytes_unavailable" in saved_segment.quality.warnings
    with pytest.raises(ReceiptConflictError):
        restarted.resolve("other", saved_segment.segment_id)
    assert saved_source.original_byte_hash is None


@pytest.mark.parametrize("kind", ["text", "quality", "coordinate", "hash"])
def test_rejects_span_or_provenance_laundering(repo, kind):
    artifact, segments = source(repo)
    segment = segments[0]
    changes = (
        {"text": "z" * len(segment.text)}
        if kind == "text"
        else (
            {"quality": segment.quality.model_copy(update={"score": 1.0})}
            if kind == "quality"
            else {"coordinate_system": "raw_bytes"}
        )
    )
    if kind == "hash":
        changes = {"text_hash": "forged"}
    with pytest.raises(ReceiptConflictError):
        repo.put_source(artifact, segment.text, (segment.model_copy(update=changes),))


def test_available_and_unavailable_versions_survive_update(repo):
    artifact, segments = source(repo)
    updated, _ = source(repo, "Changed source")
    absent, empty = source(repo, "")
    assert len({artifact.source_version, updated.source_version, absent.source_version}) == 3
    assert empty == () and absent.fetch_status == "unavailable"
    assert absent.unavailable_reason == "empty_extraction"
    assert repo.resolve("task", segments[0].segment_id)[0] == artifact
    assert len(repo.export_bundle("task")["sources"]) == 3


def test_resolvable_quote_does_not_certify_semantic_support(repo):
    artifact, segments = source(repo)
    item = claim(artifact, segments[0], inference_label="source_quote")
    assert item.support_status == "unverified"
    with pytest.raises(ValidationError, match="reviewer"):
        claim(artifact, segments[0], support_status="supported")
    with pytest.raises(ReceiptConflictError):
        repo.put_claim(item.model_copy(update={"task_id": "other"}))


@pytest.mark.parametrize("changes", [{"rubric": ()}, {"resource_ceilings": {"tokens": 101}}])
def test_contract_revision_cannot_weaken_hard_requirements(repo, changes):
    current = repo.get_contract("task", 1)
    with pytest.raises(ReceiptConflictError):
        repo.put_contract(current.model_copy(update={"revision": 2, **changes}))


def test_imported_snapshot_preserves_origin_without_local_authority(repo):
    artifact, segments = source(repo)
    repo.put_claim(claim(artifact, segments[0]))
    bundle = EvidenceBundle.model_validate(repo.export_bundle("task"))
    repo.preserve_import("other", bundle)
    saved = ResearchEvidenceRepository(repo._db_path).imported_bundle("other")
    assert saved == bundle
    assert saved.resolve_locator(segments[0].locator())[0] == artifact
    assert repo.get_contract("other", 1) is None
    with pytest.raises(ReceiptConflictError):
        repo.resolve("other", segments[0].segment_id)


def test_export_rejects_tampered_source_text(repo):
    source(repo)
    payload = repo.export_bundle("task")
    payload["sources"][0]["representation_text"] = "Forged"
    with pytest.raises(ValidationError, match="source text changed"):
        EvidenceBundle.model_validate(payload)


def test_service_clamps_before_segment_allocation(repo):
    with pytest.raises(ValueError, match="text limit"):
        source(repo, "x" * 2_000_001)
    assert not repo.export_bundle("task")["sources"]


def running_action(repo, expired=False):
    now = datetime.now(UTC)
    contract = repo.get_contract("task", 1)
    action = ResearchActionReceipt(
        action_id="action",
        task_id="task",
        kind="digesting",
        intent="interpret",
        budget_reserved=0,
        input_version="v1",
        rationale="Observe claims",
        contract_hash=contract.content_hash(),
        policy_hash="policy",
        deadline=now + timedelta(seconds=-1 if expired else 60),
    )
    journal = ResearchActionReceiptRepository(repo._db_path)
    journal.create(action)
    journal.transition(action.transition("running", now), expected_status="pending")
    state = dict(
        active_action_id="action",
        contract_revision=1,
        action_journal_policy=dict(contract_hash=contract.content_hash(), policy_hash="policy"),
    )
    ResearchTaskRepository(repo._db_path).update("task", orchestrator_state=json.dumps(state))
    return state


def test_digest_preserves_quality_objections_and_typed_exclusions(repo):
    state = running_action(repo)
    store = ResearchEvidenceStore(repo)
    artifact, _ = source(repo)
    claims = store.record_interpretation(
        "task",
        state,
        artifact,
        dict(learnings=["An interpretation"], diffractive_notes=["Contrary result not resolved"]),
    )
    store.record_interpretation("task", state, artifact, dict(learnings=[]))
    bundle = EvidenceBundle.model_validate(repo.export_bundle("task"))
    assert claims == (bundle.claims[0].claim_id,)
    assert bundle.claims[0].citation_status == "absent"
    assert bundle.claims[0].support_status == "unverified"
    assert "Contrary result not resolved" in bundle.claims[0].unresolved_objections
    assert "original_bytes_unavailable" in bundle.claims[0].unresolved_objections
    assert bundle.decisions[1].exclusions[0].reason == "no_anchor_in_legacy"


def test_late_source_is_retained_but_decision_cannot_enter_task(repo):
    state = running_action(repo, expired=True)
    artifact, segments = source(repo)
    with pytest.raises(ReceiptConflictError, match="Late"):
        ResearchEvidenceStore(repo).record_interpretation("task", state, artifact, dict(learnings=[]))
    assert repo.resolve("task", segments[0].segment_id)[0] == artifact
    assert repo.export_bundle("task")["decisions"] == []


def test_json_import_reexport_retains_original_locator_and_origin(repo):
    from backend.services.export.research import ResearchExportBuilder, research_evidence_bundle
    from backend.services.research.import_service import import_research_task

    artifact, segments = source(repo)
    bundle = repo.export_bundle("task")
    tasks = ResearchTaskRepository(repo._db_path)
    app = SimpleNamespace(research_task_repo=tasks)

    def export(task_id, evidence):
        return ResearchExportBuilder.build_research_export_json(
            tasks.get(task_id), [], [], [], None, [], [], [], evidence
        )

    payload = export("task", bundle)
    imported = import_research_task(payload, app)
    assert imported.imported and imported.warnings
    archived = research_evidence_bundle(app, imported.new_task_id)
    assert EvidenceBundle.model_validate(archived).resolve_locator(segments[0].locator())[0] == artifact
    second = import_research_task(export(imported.new_task_id, archived), app)
    assert second.imported
    assert repo.imported_bundle(second.new_task_id).task_id == "task"
    markdown = ResearchExportBuilder.build_research_export(
        tasks.get(imported.new_task_id), [], [], [], None, {}, [], archived
    )
    assert "## EVIDENCE PROVENANCE" in markdown
    assert "Origin task: `task`" in markdown
    assert "parser quality unknown" in markdown


@pytest.mark.asyncio
async def test_parse_packets_resolve_and_digest_keeps_support_unverified(repo, monkeypatch):
    from backend.services.research.steps import digest, parse
    from backend.services.research.task_state import ParsePayload

    state = running_action(repo)
    store = ResearchEvidenceStore(repo)
    sources = [dict(url="https://example.org/report", content="Observed text", title="Report", query_group=1)]

    async def fetch(*args):
        return sources

    async def analyze(*args, **kwargs):
        return dict(learnings=["Interpretation"], diffractive_notes=["Counter-reading"])

    monkeypatch.setattr(parse, "parallel_parse_grouped", fetch)
    monkeypatch.setattr(digest, "analyze_source_content", analyze)
    orch = SimpleNamespace(
        evidence_store_for=lambda task: store,
        _get_state=lambda task: state,
        _create_or_update_step=lambda *args, **kwargs: "step",
        step_repo=None,
        step_result_repo=None,
        _load_cache=lambda task: {},
        _save_cache=lambda *args: None,
        _get_semaphore=lambda: asyncio.Semaphore(2),
    )
    envelope = SimpleNamespace(
        task_id="task",
        plan_id="plan",
        payload=ParsePayload(
            search_results_cache=[
                dict(url="https://example.org/report", query_group=1),
                dict(url="https://example.org/unavailable", query_group=1),
            ]
        ),
    )
    output = await parse.ParseStep().execute(orch, envelope)
    assert len(output.evidence_packets) == 2
    packet = output.evidence_packets[0]
    assert packet.raw_span_locator is None
    bundle = EvidenceBundle.model_validate(repo.export_bundle("task"))
    assert bundle.resolve_locator(packet.representation_span_locators[0])[1].text == "Observed text"
    assert output.evidence_packets[1].unavailable_evidence
    results = await digest.parallel_digest_grouped(orch, "task", {1: "step"}, sources, ["query"], "objective", 0, 1)
    assert results[0]["evidence_packet"]["claim_ids"]
    claim_record = repo.export_bundle("task")["claims"][0]
    assert claim_record["support_status"] == "unverified" and claim_record["citation_status"] == "absent"
    assert "Counter-reading" in claim_record["unresolved_objections"]


def test_initializer_contract_and_policy_commit_atomically(repo):
    journal = ResearchActionReceiptRepository(repo._db_path)
    contract = ResearchContract(task_id="other", objective="Atomic contract", policy_version=3)
    with pytest.raises(ReceiptConflictError):
        journal.initialize_task_state(
            "other", json.dumps(dict(action_journal_policy=dict(contract_hash="wrong"))), contract
        )
    assert not ResearchTaskRepository(repo._db_path).get("other")["orchestrator_state"]
    assert repo.get_contract("other", 1) is None
    journal.initialize_task_state(
        "other", json.dumps(dict(action_journal_policy=dict(contract_hash=contract.content_hash()))), contract
    )
    assert repo.get_contract("other", 1) == contract
