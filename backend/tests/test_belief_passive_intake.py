"""T7 actual-origin, retry, ancestry and no-adoption regression oracles."""

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from backend.errors import ConstraintViolation, SecurityViolation, ValidationGlitch
from backend.modules.belief_engine import BeliefDynamicsEngine
from backend.services.annotations import process_self_annotations
from backend.services.belief_passive_intake import passive_intake
from backend.services.belief_review_store import BeliefReviewStore
from backend.storage.repositories import BeliefRepository, NotificationRepository
from backend.storage.repositories.cognitive.belief_explicit import ExplicitBeliefRepository
from backend.tests.test_belief_admission import admission_db as admission_db
from backend.tests.test_belief_review_persistence import sql

CONFIG = {
    "belief_review": {
        "origin_intake": {
            "passive_chat": True,
            "conversation_pattern": True,
            "scar_fold": True,
        }
    }
}


def invoke(path, message, origin, **kwargs):
    return passive_intake(
        path,
        "symbia",
        message.content,
        origin=origin,
        source_id=str(message.id) if origin != "conversation_pattern" else "pattern:fixture",
        segment_id="segment:0",
        config=CONFIG,
        **kwargs,
    )


@pytest.mark.parametrize("origin", ["passive_chat", "conversation_pattern", "scar_fold"])
def test_v1_v3_v7_origin_projection_and_no_warrant(admission_db, origin):
    path, _, parent, message = admission_db
    source = parent if origin == "passive_chat" else message
    before = {b.id for b in BeliefRepository(path).list_beliefs("symbia")}
    receipt = invoke(path, source, origin)
    assert receipt["source"]["origin"] == origin
    assert receipt["evaluation"]["status"] == "abstained"
    assert receipt["evaluation"]["reason"] == "v2_evaluator_pending_T9"
    assert not receipt["comparisons"]
    assert sql(path, "SELECT state FROM belief_review_state")[0][0] == "awaiting_context"
    assert not sql(path, "SELECT id FROM belief_review_decisions")
    assert {b.id for b in BeliefRepository(path).list_beliefs("symbia")} == before
    assert all(item["independence_status"] != "independent" for item in receipt["source"]["lineage"])
    if origin == "conversation_pattern":
        assert receipt["source"]["message_id"] is None
        assert receipt["source"]["conversation_id"] is None
        assert receipt["source"]["context_status"] == "missing"
    proposal = BeliefRepository(path).get_proposal(receipt["proposal_id"])
    assert proposal.admission_history == [receipt]
    traces = NotificationRepository(path).list_all()
    assessed = next(t for t in traces if t["id"].endswith(":assessed"))
    assert json.loads(assessed["snippet"].split("\n\nAdmission receipt:\n")[1]) == receipt


@pytest.mark.asyncio
async def test_v2_concurrent_retry_distinct_unscoped_segments(admission_db):
    path, _, parent, _ = admission_db
    receipts = await asyncio.gather(*[asyncio.to_thread(invoke, path, parent, "passive_chat") for _ in range(8)])
    assert all(r == receipts[0] for r in receipts)
    other = passive_intake(
        path,
        "symbia",
        parent.content,
        origin="passive_chat",
        source_id=str(parent.id),
        segment_id="segment:1",
        config=CONFIG,
    )
    assert other["encounter_id"] != receipts[0]["encounter_id"]
    # Missing claim scope must not be fabricated to merge distinct observations.
    assert other["proposal_id"] != receipts[0]["proposal_id"]
    assert len(sql(path, "SELECT id FROM belief_admission")) == 2
    assert len(NotificationRepository(path).list_all()) == 4


@pytest.mark.parametrize("origin", ["passive_chat", "conversation_pattern", "scar_fold"])
def test_v1_paused_promoted_origin_never_returns_legacy(admission_db, origin):
    path, _, parent, message = admission_db
    source = parent if origin == "passive_chat" else message
    assert invoke(path, source, origin)
    paused = passive_intake(
        path,
        "symbia",
        source.content,
        origin=origin,
        source_id=str(source.id) if origin != "conversation_pattern" else "pattern:fixture",
        segment_id="segment:1",
        config={},
    )
    assert paused["evaluation"]["reason"] == "origin_paused"


def test_v3_v20_invalid_quote_and_owner(admission_db):
    path, _, parent, _ = admission_db
    receipt = passive_intake(
        path,
        "symbia",
        "Absent statement",
        origin="passive_chat",
        source_id=str(parent.id),
        segment_id="passive:0",
        config=CONFIG,
    )
    assert receipt["source"]["context_status"] == "ambiguous"
    with pytest.raises(SecurityViolation):
        passive_intake(
            path,
            "other",
            parent.content,
            origin="passive_chat",
            source_id=str(parent.id),
            segment_id="passive:0",
            config=CONFIG,
        )
    with pytest.raises(SecurityViolation):
        invoke(path, parent, "scar_fold")


def test_v1_default_off_legacy_engine_parity(admission_db):
    path, messages, parent, _ = admission_db
    engine = BeliefDynamicsEngine(BeliefRepository(path), messages, Path("unused"))
    result = engine._nucleate_proto_belief("symbia", parent.content, np.zeros(16), "chat_turn", str(parent.id), 0.4)
    proposal = BeliefRepository(path).get_proposal(result)
    assert proposal.confidence == 0.1 and proposal.nucleation_mass == pytest.approx(0.04)
    assert not proposal.admission_history
    assert not sql(path, "SELECT id FROM belief_encounters")


@pytest.mark.asyncio
async def test_v1_actual_passive_chat_and_pattern_routes(admission_db):
    path, messages, parent, message = admission_db
    from backend.bootstrap.modules import _init_belief_engine

    engine = _init_belief_engine(
        {"belief_repo": BeliefRepository(path), "message_repo": messages}, Path("unused"), config=CONFIG
    )
    # Bootstrap skill projections are unrelated seeds; test the creation branch explicitly.
    sql(path, "DELETE FROM belief_nodes")
    vector = np.ones(16, dtype=np.float32).tobytes()
    sql(path, "UPDATE conversation_log SET structural_signature=? WHERE id IN (?,?)", (vector, parent.id, message.id))
    with patch("backend.modules.belief_engine.calculate_concept_density", return_value=1.0):
        await engine.metabolize(parent.conversation_id, parent.id, message.id)
    with patch("backend.modules.belief.perception_handlers.calculate_concept_density", return_value=1.0):
        await engine.metabolize_conversational_pattern(
            "symbia", "Recurring material tension", source_id="pattern:run:1"
        )
    encounters = sql(path, "SELECT encounter_json FROM belief_encounters")
    assert {json.loads(row[0])["origin"] for row in encounters} == {"passive_chat", "conversation_pattern"}


@pytest.mark.parametrize("enabled", [False, True])
def test_v7_actual_scar_fallback_never_crystallizes_and_retries(admission_db, enabled):
    path, messages, _, message = admission_db
    text = "<scar-fold>" + "Material tension persists. " * 20 + "</scar-fold>"
    messages.update_content(message.id, text)
    config = CONFIG if enabled else {}
    repo = BeliefRepository(path)
    sql(path, "DELETE FROM belief_nodes")
    result = process_self_annotations(text, message.conversation_id, message.id, None, messages, repo, config=config)
    process_self_annotations(result, message.conversation_id, message.id, None, messages, repo, config=config)
    assert not repo.list_beliefs("symbia")
    assert len(repo.list_proposals("symbia")) == 1
    assert repo.list_proposals("symbia")[0].status == "pending"
    if enabled:
        assert repo.list_proposals("symbia")[0].admission_history[0]["source"]["activity"] == "internal"


def test_v19_strict_flags_and_scar_batch_limit(admission_db):
    path, messages, _, message = admission_db
    with pytest.raises(ValidationGlitch):
        passive_intake(
            path,
            "symbia",
            "x",
            origin="scar_fold",
            source_id=str(message.id),
            segment_id="s:0",
            config={"belief_review": {"origin_intake": {"scar_fold": "false"}}},
        )
    with pytest.raises(ValidationGlitch):
        process_self_annotations(
            "<scar-fold>x</scar-fold>" * 17,
            message.conversation_id,
            message.id,
            None,
            messages,
            BeliefRepository(path),
            config=CONFIG,
        )
    assert not sql(path, "SELECT id FROM belief_encounters")


@pytest.mark.asyncio
async def test_v2_v3_restart_and_changed_retry(admission_db):
    path, _, parent, _ = admission_db
    receipt = invoke(path, parent, "passive_chat")
    assessment = await BeliefReviewStore(path).get_assessment("symbia", receipt["assessment_id"])
    assert assessment.evaluator_status == "abstained"
    assert invoke(path, parent, "passive_chat") == receipt
    with pytest.raises(ConstraintViolation):
        passive_intake(
            path,
            "symbia",
            "Changed observation",
            origin="passive_chat",
            source_id=str(parent.id),
            segment_id="segment:0",
            config=CONFIG,
        )


def test_v3_source_change_at_completion_is_stale(admission_db, monkeypatch):
    path, messages, parent, _ = admission_db
    complete = ExplicitBeliefRepository.complete

    def changed(repo, write):
        messages.update_content(parent.id, "Changed source after checkpoint")
        return complete(repo, write)

    monkeypatch.setattr(ExplicitBeliefRepository, "complete", changed)
    receipt = invoke(path, parent, "passive_chat")
    assert receipt["evaluation"]["status"] == "stale"
    assert not sql(path, "SELECT id FROM belief_review_decisions")


def test_v19_failure_retains_restart_checkpoint_without_provider(admission_db, monkeypatch):
    path, _, parent, _ = admission_db
    complete = ExplicitBeliefRepository.complete

    def interrupted(repo, write):
        raise RuntimeError("Simulated process interruption")

    monkeypatch.setattr(ExplicitBeliefRepository, "complete", interrupted)
    with pytest.raises(RuntimeError, match="interruption"):
        invoke(path, parent, "passive_chat")
    assert sql(path, "SELECT status FROM belief_admission")[0][0] == "assessing"
    monkeypatch.setattr(ExplicitBeliefRepository, "complete", complete)
    receipt = invoke(path, parent, "passive_chat")
    assert receipt["status"] == "complete"
    assert len(sql(path, "SELECT id FROM belief_admission")) == 1
    assert len(NotificationRepository(path).list_all()) == 2


def test_v20_secret_rejected_before_promotion(admission_db, monkeypatch):
    path, _, parent, _ = admission_db
    monkeypatch.setenv("AAA_PASSWORD", "t7-secret-fixture-value")
    with pytest.raises(ValidationGlitch):
        passive_intake(
            path,
            "symbia",
            "t7-secret-fixture-value",
            origin="passive_chat",
            source_id=str(parent.id),
            segment_id="s:0",
            config=CONFIG,
        )
    assert not sql(path, "SELECT origin FROM belief_origin_promotions")
