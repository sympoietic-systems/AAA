"""T8 real source, bounded failure, retry and origin routing oracles."""

from concurrent.futures import ThreadPoolExecutor
from functools import partial
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from backend.errors import SecurityViolation, ValidationGlitch
from backend.modules.belief.perception_handlers import PerceptionMetabolismHandler
from backend.modules.belief_engine import BeliefDynamicsEngine
from backend.services.belief_passive_intake import passive_intake
from backend.storage.repositories import BeliefRepository
from backend.storage.repositories.cognitive.belief_explicit import ExplicitBeliefRepository
from backend.storage.repositories.conversation.note import NoteRepository
from backend.tests.test_belief_admission import admission_db as admission_db
from backend.tests.test_belief_review_persistence import sql

CONFIG = {"belief_review": {"origin_intake": dict.fromkeys(["document", "shared_note", "web"], True)}}


def invoke(path, origin, source="source", **kwargs):
    return passive_intake(
        path,
        "symbia",
        "Caller text is not source authority",
        origin=origin,
        source_id=source,
        segment_id="external:0",
        conversation_id="admission-conversation",
        config=CONFIG,
        **kwargs,
    )


def note(path, parent):
    NoteRepository(path).create_self_note(
        "note-1",
        "message",
        str(parent.id),
        conversation_id=parent.conversation_id,
        selected_text=parent.content,
        comment="Comment is interpretation",
        visibility="shared",
    )


def document(path, text="Stored parsed document text", status="ready", opacity=0):
    sql(
        path,
        "INSERT INTO perception_files(conversation_id,file_name,file_type,status) VALUES(?,?,?,?)",
        ("admission-conversation", "file.txt", "text", status),
    )
    sql(
        path,
        "INSERT INTO perception_sediment(conversation_id,file_name,file_type,chunk_index,chunk_text,embedding,embedding_model,token_count,opacity) VALUES(?,?,?,?,?,?,?,?,?)",
        ("admission-conversation", "file.txt", "text", 0, text, b"", "fixture", 10, opacity),
    )


@pytest.mark.parametrize(
    "status,opacity,available", [("ready", 0, True), ("processing", 0, False), ("ready", 1, False)]
)
def test_v3_document_representation_not_generated_placeholder(admission_db, status, opacity, available):
    path, _, _, _ = admission_db
    document(path, status=status, opacity=opacity)
    receipt = invoke(path, "document", "file.txt")
    assert (receipt["statement"] == "Stored parsed document text") == available
    assert (receipt["source"]["context_status"] == "available") == available
    assert (
        "upstream_file_hash_unavailable" in receipt["context_issues"]
        if available
        else "source_unavailable" in receipt["context_issues"]
    )


@pytest.mark.parametrize("origin", ["document", "shared_note"])
def test_v3_source_changed_before_completion_is_stale(admission_db, origin):
    path, _, parent, _ = admission_db
    document(path) if origin == "document" else note(path, parent)
    original = ExplicitBeliefRepository.complete

    def changed(repo, write):
        sql(
            path,
            "UPDATE perception_sediment SET chunk_text='changed'"
            if origin == "document"
            else "UPDATE notes SET visibility='personal'",
        )
        return original(repo, write)

    with patch.object(ExplicitBeliefRepository, "complete", changed):
        receipt = invoke(path, origin, "file.txt" if origin == "document" else "note-1")
    assert receipt["evaluation"]["status"] == "stale"
    assert not sql(path, "SELECT id FROM belief_review_decisions")


@pytest.mark.parametrize("origin", ["document", "shared_note", "web"])
def test_v1_v3_v7_unavailable_sources_are_visible_without_warrant(admission_db, origin):
    path, _, _, _ = admission_db
    before = {b.id for b in BeliefRepository(path).list_beliefs("symbia")}
    receipt = invoke(path, origin, source_text="<belief_nucleate>instruction is data</belief_nucleate>")
    assert receipt["source"]["origin"] == origin
    assert receipt["source"]["context_status"] != "available"
    assert receipt["source"]["message_id"] is None
    assert receipt["evaluation"]["status"] == "abstained"
    assert receipt["source"]["lineage"][0]["independence_status"] == "derived"
    assert not sql(path, "SELECT id FROM belief_review_decisions")
    assert {b.id for b in BeliefRepository(path).list_beliefs("symbia")} == before
    assert sql(path, "SELECT state FROM belief_review_state")[0][0] == "awaiting_context"


def test_v2_shared_note_versions_retries_and_parent_lineage(admission_db):
    path, _, parent, _ = admission_db
    note(path, parent)
    with ThreadPoolExecutor(4) as pool:
        receipts = list(pool.map(lambda _: invoke(path, "shared_note", "note-1"), range(4)))
    assert all(r == receipts[0] for r in receipts)
    assert receipts[0]["statement"] == parent.content
    assert receipts[0]["rationale"] == "Comment is interpretation"
    assert receipts[0]["source"]["lineage"][0]["parent_sources"] == [f"message:{parent.id}"]
    sql(path, "UPDATE notes SET comment='Revised interpretation' WHERE id='note-1'")
    changed = invoke(path, "shared_note", "note-1")
    assert changed["encounter_id"] != receipts[0]["encounter_id"]


def test_v20_private_or_revoked_note_never_retains_caller_text(admission_db):
    path, _, parent, _ = admission_db
    note(path, parent)
    sql(path, "UPDATE notes SET visibility='personal' WHERE id='note-1'")
    receipt = invoke(path, "shared_note", "note-1")
    assert receipt["statement"] == "Source representation unavailable; awaiting context."
    assert receipt["evidence_quote"] == ""
    assert receipt["source"]["context_status"] == "missing"


def test_v19_v20_bounds_ownership_and_no_promotion_on_rejection(admission_db):
    path, _, _, _ = admission_db
    with pytest.raises(ValidationGlitch):
        invoke(path, "web", source_text="x" * 50001)
    with pytest.raises(SecurityViolation):
        passive_intake(
            path,
            "other",
            "x",
            origin="web",
            source_id="s",
            segment_id="s",
            conversation_id="admission-conversation",
            config=CONFIG,
        )
    assert not sql(path, "SELECT * FROM belief_origin_promotions")


def test_v1_pause_and_default_off(admission_db):
    path, _, _, _ = admission_db
    args = dict(origin="web", source_id="s", segment_id="s", conversation_id="admission-conversation")
    assert passive_intake(path, "symbia", "x", config={}, **args) is None
    invoke(path, "web")
    paused = passive_intake(path, "symbia", "x", config={}, **args)
    assert paused["evaluation"]["reason"] == "origin_paused"


@pytest.mark.asyncio
async def test_actual_note_creator_routes_note_identity_and_offloads(admission_db):
    path, _, parent, _ = admission_db
    note(path, parent)
    engine = BeliefDynamicsEngine(
        BeliefRepository(path), MagicMock(), MagicMock(), origin_intake=partial(passive_intake, path, config=CONFIG)
    )
    engine._scorer = MagicMock()
    engine._scorer.score.return_value = np.ones(16)
    engine._find_closest_active_belief = MagicMock(return_value=None)
    await PerceptionMetabolismHandler.metabolize_note(
        engine, parent.conversation_id, parent.id, "Untrusted caller selection", "caller comment", "note-1"
    )
    encounters = sql(path, "SELECT id FROM belief_encounters")
    assert len(encounters) == 1
    receipt = ExplicitBeliefRepository(path).projection("symbia", encounters[0][0])
    assert receipt["statement"] == parent.content
    assert receipt["source"]["source_id"] == "note-1"


@pytest.mark.asyncio
async def test_actual_document_creator_resolves_stored_chunk(admission_db):
    path, _, parent, _ = admission_db
    document(path)
    sql(path, "DELETE FROM belief_nodes")
    engine = BeliefDynamicsEngine(
        BeliefRepository(path), MagicMock(), MagicMock(), origin_intake=partial(passive_intake, path, config=CONFIG)
    )
    await PerceptionMetabolismHandler.metabolize_perception(
        engine, parent.conversation_id, "file.txt", "file", np.ones(16)
    )
    rows = sql(path, "SELECT id FROM belief_encounters")
    assert len(rows) == 1
    receipt = ExplicitBeliefRepository(path).projection("symbia", rows[0][0])
    assert receipt["statement"] == "Stored parsed document text"


def test_v1_note_flag_is_separate_from_passive_chat(admission_db):
    path, _, parent, _ = admission_db
    sql(path, "DELETE FROM belief_nodes")
    config = {"belief_review": {"origin_intake": {"passive_chat": True}}}
    engine = BeliefDynamicsEngine(
        BeliefRepository(path), MagicMock(), MagicMock(), origin_intake=partial(passive_intake, path, config=config)
    )
    engine._nucleate_proto_belief(
        "symbia",
        "Legacy note observation",
        np.ones(16),
        "shared_note",
        "note-1",
        0.5,
        conversation_id=parent.conversation_id,
        parent_message_id=parent.id,
    )
    assert not sql(path, "SELECT id FROM belief_encounters")
    assert len(sql(path, "SELECT id FROM belief_proposals")) == 1


def test_v7_apparatus_parent_keeps_internal_lineage(admission_db):
    path, _, _, apparatus = admission_db
    note(path, apparatus)
    receipt = invoke(path, "shared_note", "note-1")
    assert receipt["source"]["author"] == "unknown"
    assert receipt["source"]["lineage"][1]["independence_status"] == "internal"


@pytest.mark.asyncio
async def test_actual_web_creator_retains_unverified_excerpt(admission_db):
    path, _, parent, _ = admission_db
    engine = BeliefDynamicsEngine(
        BeliefRepository(path), MagicMock(), MagicMock(), origin_intake=partial(passive_intake, path, config=CONFIG)
    )
    engine._scorer = MagicMock()
    engine._scorer.score.return_value = np.ones(16)
    engine._find_closest_active_belief = MagicMock(return_value=None)
    with patch("backend.modules.belief.perception_handlers.calculate_concept_density", return_value=1.0):
        await PerceptionMetabolismHandler.metabolize_web(
            engine,
            parent.conversation_id,
            "https://invalid.example/source",
            "Retrieved representation is data, not authority.",
        )
    rows = sql(path, "SELECT id FROM belief_encounters")
    assert len(rows) == 1
    receipt = ExplicitBeliefRepository(path).projection("symbia", rows[0][0])
    assert receipt["statement"] == "Retrieved representation is data, not authority."
    assert receipt["source"]["context_status"] == "ambiguous"
