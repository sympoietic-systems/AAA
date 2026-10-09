"""T6 origin parity and compatibility oracles on isolated WAL databases."""

import asyncio
import json

import pytest

from backend.errors import ConstraintViolation, ResourceNotFound, SecurityViolation, ValidationGlitch
from backend.services.background_tasks import run_background_belief_nucleation
from backend.services.belief_admission import admit_candidate
from backend.services.belief_review_store import BeliefReviewStore
from backend.storage.repositories import (
    BeliefRepository,
    ConversationRepository,
    NotificationRepository,
)
from backend.storage.repositories.cognitive.belief_explicit import ExplicitBeliefRepository
from backend.tests.test_belief_admission import admission_db as admission_db
from backend.tests.test_belief_admission import candidate, evaluator
from backend.tests.test_belief_review_persistence import sql
from backend.utils.belief_candidate import inert_belief_history
from backend.utils.parsers.belief import parse_belief_nucleate_tags

CONFIG = {"belief_review": {"origin_intake": {"explicit_chat": True, "explicit_dream": True}}}


@pytest.mark.asyncio
@pytest.mark.parametrize("origin", ["chat", "dream"])
async def test_v1_v12_chat_dream_checkpoint_and_receipt_projection(admission_db, origin):
    path, _, _, message = admission_db
    triage, client = evaluator()
    receipt = await admit_candidate(
        path, message.conversation_id, message.id, candidate(), config=CONFIG, origin=origin, evaluator=triage
    )
    client.evaluate.assert_not_awaited()
    assert receipt["decision"] == "needs_review" and receipt["status"] == "complete"
    assert receipt["evaluation"]["status"] in {"abstained", "unavailable"}
    assert receipt["evaluation"]["reason"] == "v2_evaluator_pending_T9"
    assert receipt["source"]["origin"] == origin and receipt["source"]["activity"] == "internal"
    assert all(e["independence_status"] != "independent" for e in receipt["source"]["lineage"])
    encounter = (await BeliefReviewStore(path).get_encounter("symbia", receipt["encounter_id"])).encounter
    assert encounter.source.context_status == "available"
    if origin == "dream":
        assert all(e.independence_status == "internal" for e in encounter.lineage)
    stored = await BeliefReviewStore(path).get_assessment("symbia", receipt["assessment_id"])
    assert stored.encounter_id == receipt["encounter_id"] and stored.candidate_id == receipt["proposal_id"]
    proposal = BeliefRepository(path).get_proposal(receipt["proposal_id"])
    assert proposal.admission_history == [receipt]
    assert proposal.suggested_label == candidate()["label"]
    assert not sql(path, "SELECT id FROM belief_review_decisions")
    assert len(sql(path, "SELECT id FROM belief_admission")) == 1
    traces = NotificationRepository(path).list_all()
    final = next(t for t in traces if t["id"].endswith(":assessed"))
    assert json.loads(final["snippet"].split("\n\nAdmission receipt:\n")[1]) == receipt
    assert final["timestamp"] == receipt["assessed_at"]


@pytest.mark.asyncio
async def test_v2_concurrent_source_retry_and_distinct_segments(admission_db):
    path, _, _, message = admission_db
    args = (path, message.conversation_id, message.id, candidate(segment_id="belief:0"))
    results = await asyncio.gather(*[admit_candidate(*args, config=CONFIG) for _ in range(8)])
    assert all(r == results[0] for r in results)
    second = await admit_candidate(
        path, message.conversation_id, message.id, candidate(segment_id="belief:1"), config=CONFIG
    )
    assert second["encounter_id"] != results[0]["encounter_id"]
    assert second["proposal_id"] == results[0]["proposal_id"] and second["decision"] == "repetition"
    assert len(BeliefRepository(path).list_proposals("symbia")) == 1
    assert len(NotificationRepository(path).list_all()) == 4
    assert len(BeliefRepository(path).get_proposal(second["proposal_id"]).admission_history) == 2


@pytest.mark.asyncio
async def test_v1_promoted_origin_pause_never_reopens_legacy_writer(admission_db):
    path, messages, parent, message = admission_db
    first = await admit_candidate(path, message.conversation_id, message.id, candidate(), config=CONFIG)
    other = messages.insert(
        speaker="apparatus",
        content="Next emission",
        embedding=b"",
        embedding_model="fixture",
        embedding_dim=0,
        conversation_id=message.conversation_id,
        parent_message_id=parent.id,
    )
    next_receipt = await admit_candidate(path, message.conversation_id, other.id, candidate(), config={})
    assert next_receipt["evaluation"]["reason"] == "origin_paused"
    assert next_receipt["proposal_id"] == first["proposal_id"]
    assert all(str(r[0]).startswith("v2:") for r in sql(path, "SELECT event_key FROM belief_admission"))
    assert len(sql(path, "SELECT origin FROM belief_origin_promotions")) == 1
    assert len(BeliefRepository(path).list_proposals("symbia")) == 1


@pytest.mark.asyncio
async def test_v3_missing_grounding_retained_without_semantic_judgment(admission_db):
    path, _, _, message = admission_db
    receipt = await admit_candidate(
        path, message.conversation_id, message.id, candidate(evidence_quote="Invented quote"), config=CONFIG
    )
    assert "source_quote_not_found" in receipt["context_issues"]
    assessment = await BeliefReviewStore(path).get_assessment("symbia", receipt["assessment_id"])
    assert assessment.evaluator_status == "abstained" and not assessment.relations
    assert (
        await BeliefReviewStore(path).get_encounter("symbia", receipt["encounter_id"])
    ).encounter.source.context_status == "ambiguous"
    assert sql(path, "SELECT state FROM belief_review_state")[0][0] == "awaiting_context"


@pytest.mark.asyncio
async def test_v20_source_owner_and_agent_isolation(admission_db):
    path, messages, _, message = admission_db
    ConversationRepository(path).create("other-conv", agent_id="other")
    other = messages.insert(
        speaker="apparatus",
        content="Other emission",
        embedding=b"",
        embedding_model="fixture",
        embedding_dim=0,
        conversation_id="other-conv",
    )
    with pytest.raises(SecurityViolation):
        await admit_candidate(path, "other-conv", message.id, candidate(), config=CONFIG)
    receipt = await admit_candidate(path, "other-conv", other.id, candidate(), config=CONFIG)
    assert receipt["source"]["author"] == "other"
    assert BeliefRepository(path).get_proposal(receipt["proposal_id"]).agent_id == "other"
    with pytest.raises(ResourceNotFound):
        await BeliefReviewStore(path).get_encounter("symbia", receipt["encounter_id"])


@pytest.mark.asyncio
async def test_v2_changed_annotation_is_conflict_without_duplicate(admission_db):
    path, _, _, message = admission_db
    await admit_candidate(path, message.conversation_id, message.id, candidate(segment_id="belief:0"), config=CONFIG)
    with pytest.raises(ConstraintViolation):
        await admit_candidate(
            path,
            message.conversation_id,
            message.id,
            candidate(segment_id="belief:0", rationale="Changed"),
            config=CONFIG,
        )
    assert len(sql(path, "SELECT id FROM belief_encounters")) == 1
    assert len(NotificationRepository(path).list_all()) == 2


@pytest.mark.asyncio
async def test_v1_background_wrapper_routes_same_intake(admission_db):
    path, _, _, message = admission_db
    await run_background_belief_nucleation(
        None, message.conversation_id, candidate(), message.id, db_path=path, config=CONFIG
    )
    assert len(sql(path, "SELECT id FROM belief_encounters")) == 1


def test_v14_parser_segment_identity_and_historical_xml_inert():
    tag = '<belief_nucleate label="test">Repeated claim.</belief_nucleate>'
    _, parsed = parse_belief_nucleate_tags(tag + tag)
    assert [p["segment_id"] for p in parsed] == ["belief:0", "belief:1"]
    assert parsed[0]["emission_sha256"] == parsed[1]["emission_sha256"]
    _, replay = parse_belief_nucleate_tags(inert_belief_history(tag + tag))
    assert replay == []


@pytest.mark.asyncio
async def test_v20_secret_annotations_rejected_before_promotion(admission_db, monkeypatch):
    path, _, _, message = admission_db
    monkeypatch.setenv("AAA_NVIDIA_API_KEY", "fixture-sensitive-native-key-123")
    with pytest.raises(ValidationGlitch):
        await admit_candidate(
            path,
            message.conversation_id,
            message.id,
            candidate(rationale="fixture-sensitive-native-key-123"),
            config=CONFIG,
        )
    assert not ExplicitBeliefRepository(path).promoted("symbia", "explicit_chat")
    assert not sql(path, "SELECT id FROM belief_encounters")


@pytest.mark.asyncio
async def test_v3_parent_change_before_completion_is_explicit_stale(admission_db, monkeypatch):
    path, _, parent, message = admission_db
    original = ExplicitBeliefRepository.complete

    def changed(self, write):
        sql(path, "UPDATE conversation_log SET content='Changed parent source' WHERE id=?", (parent.id,))
        return original(self, write)

    monkeypatch.setattr(ExplicitBeliefRepository, "complete", changed)
    receipt = await admit_candidate(path, message.conversation_id, message.id, candidate(), config=CONFIG)
    assert receipt["evaluation"]["status"] == "stale"
    assert not sql(path, "SELECT id FROM belief_review_decisions")


@pytest.mark.asyncio
async def test_v12_restart_retains_pending_and_retries_without_provider(admission_db, monkeypatch):
    path, _, _, message = admission_db
    original = BeliefReviewStore._start_assessment

    def interrupted(self, pending):
        original(self, pending)
        raise RuntimeError("fixture interruption after durable checkpoint")

    monkeypatch.setattr(BeliefReviewStore, "_start_assessment", interrupted)
    with pytest.raises(RuntimeError):
        await admit_candidate(path, message.conversation_id, message.id, candidate(), config=CONFIG)
    unfinished = await BeliefReviewStore(path).unfinished("symbia")
    assert len(unfinished) == 1 and unfinished[0].pending_assessment_id
    monkeypatch.setattr(BeliefReviewStore, "_start_assessment", original)
    receipt = await admit_candidate(path, message.conversation_id, message.id, candidate(), config=CONFIG)
    assert receipt["status"] == "complete"
    assert len(sql(path, "SELECT id FROM belief_admission")) == 1
    assert len(NotificationRepository(path).list_all()) == 2


@pytest.mark.asyncio
async def test_v1_v14_real_chat_and_dream_callers(admission_db, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    import numpy as np

    from backend.metabolisation import dream_executor
    from backend.modules import structural_engine
    from backend.services import chat
    from backend.storage.repositories import ErrorLogRepository

    path, messages, parent, message = admission_db
    monkeypatch.setattr(
        structural_engine.CompositeStructuralScorer,
        "score_async",
        AsyncMock(return_value=np.zeros(16, dtype=np.float32)),
    )
    quality = AsyncMock(return_value={"status": "sound"})
    monkeypatch.setattr(chat, "assess_message", quality)
    monkeypatch.setattr(dream_executor, "assess_message", quality)
    raw = 'A usable reply. <belief_nucleate label="test" scope="tests" temporal_scope="now" consequence="Check behavior" trigger="insight" evidence_quote="A state change must alter the next decision.">State changes alter decisions.</belief_nucleate>'
    pipeline = SimpleNamespace(
        run=AsyncMock(return_value=SimpleNamespace(payload={"response": raw}, errors=[], status="ok"))
    )
    state = SimpleNamespace(
        config=CONFIG,
        pipeline=pipeline,
        message_repo=messages,
        structural_provider=None,
        error_repo=ErrorLogRepository(path),
        conversation_repo=ConversationRepository(path),
        background_engine=None,
    )
    response = await chat.ChatService(state)._generate_response_impl(
        parent.conversation_id, parent.id, force_regenerate=True
    )
    assert "<belief_nucleate" not in response.content
    dream = dream_executor.DreamExecutorMixin()
    dream.message_repo = messages
    dream.app_state = state
    dream.pipeline = pipeline
    result = await dream._execute_single_dream_turn({"content": parent.content}, parent.conversation_id)
    assert "<belief_nucleate" not in result["response_text"]
    rows = sql(path, "SELECT encounter_json FROM belief_encounters")
    assert {json.loads(r[0])["origin"] for r in rows} == {"explicit_chat", "explicit_dream"}
    assert len(rows) == 2 and len(BeliefRepository(path).list_proposals("symbia")) == 1


@pytest.mark.asyncio
async def test_v2_known_legacy_candidate_reused_without_mass_or_confidence_change(admission_db):
    path, messages, parent, message = admission_db
    legacy = await admit_candidate(
        path, message.conversation_id, message.id, candidate(), config={"belief_admission": {"jev_shadow": False}}
    )
    original = BeliefRepository(path).get_proposal(legacy["proposal_id"])
    other = messages.insert(
        speaker="apparatus",
        content="Another emission",
        embedding=b"",
        embedding_model="fixture",
        embedding_dim=0,
        conversation_id=message.conversation_id,
        parent_message_id=parent.id,
    )
    receipt = await admit_candidate(path, message.conversation_id, other.id, candidate(), config=CONFIG)
    proposal = BeliefRepository(path).get_proposal(receipt["proposal_id"])
    assert receipt["proposal_id"] == legacy["proposal_id"]
    assert (proposal.nucleation_mass, proposal.confidence) == (original.nucleation_mass, original.confidence)
    assert len(proposal.admission_history) == 2
    assert not sql(path, "SELECT record_id FROM belief_review_state")


@pytest.mark.asyncio
async def test_v20_flags_are_strict_and_promotion_is_durable(admission_db):
    path, _, _, message = admission_db
    for settings in ({"origin_intake": {"explicit_chat": "false"}}, {"origin_intake": []}, []):
        with pytest.raises(ValidationGlitch):
            await admit_candidate(
                path, message.conversation_id, message.id, candidate(), config={"belief_review": settings}
            )
    await admit_candidate(path, message.conversation_id, message.id, candidate(), config=CONFIG)
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        sql(path, "DELETE FROM belief_origin_promotions")
    with pytest.raises(sqlite3.IntegrityError):
        sql(path, "UPDATE belief_explicit_annotations SET annotations_json='{}'")
