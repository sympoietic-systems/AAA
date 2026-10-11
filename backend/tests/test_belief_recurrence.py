"""V27 real SQLite read-only recurrence boundaries."""

import json

import pytest

from backend.services.belief_admission import admit_candidate
from backend.services.belief_recurrence import eligible, project, recurrence_projection
from backend.services.belief_serializer import serialize_proposal
from backend.storage.repositories import BeliefRepository
from backend.tests.test_belief_admission import admission_db as admission_db
from backend.tests.test_belief_review_persistence import sql

CONFIG = {"belief_review": {"origin_intake": {"explicit_chat": True}}}


async def emit(fixture, parent, **changes):
    path, messages, _, _ = fixture
    message = messages.insert(
        speaker="apparatus",
        content="Repeated fragment emitted.",
        embedding=b"",
        embedding_model="fixture",
        embedding_dim=0,
        conversation_id=parent.conversation_id,
        parent_message_id=parent.id,
    )
    receipt = await admit_candidate(
        path,
        parent.conversation_id,
        message.id,
        {"statement": "Refusal prevents habitual routing.", "label": "refusal", **changes},
        config=CONFIG,
    )
    return message, receipt


def items(path):
    return [serialize_proposal(p) for p in BeliefRepository(path).list_proposals("symbia")]


@pytest.mark.asyncio
async def test_v27_branch_context_and_readonly_grouping(admission_db):
    path, _, parent, _ = admission_db
    first, left = await emit(admission_db, parent)
    second, right = await emit(admission_db, first)
    _, sibling = await emit(admission_db, parent)
    _, enriched = await emit(admission_db, second, evidence_quote=second.content)
    before = sql(path, "SELECT id,confidence,nucleation_mass,status FROM belief_proposals ORDER BY id")
    projected = await recurrence_projection(items(path), BeliefRepository(path), "symbia")
    groups = [p["recurrence_group"] for p in projected if "recurrence_group" in p]
    # Sibling may pair with the shared ancestor, but a group never spans both divergent children.
    assert groups and all(g["count"] == 2 for g in groups)
    assert all(not {right["proposal_id"], sibling["proposal_id"]}.issubset(g["member_ids"]) for g in groups)
    assert all(enriched["proposal_id"] not in g["member_ids"] for g in groups)
    assert all(g["independent_warrant_delta"] == 0 and g["semantic_equivalence"] == "unknown" for g in groups)
    assert before == sql(path, "SELECT id,confidence,nucleation_mass,status FROM belief_proposals ORDER BY id")
    assert not sql(path, "SELECT id FROM belief_review_decisions")
    assert await recurrence_projection(items(path), BeliefRepository(path), "other") == items(path)
    assert left["proposal_id"] != right["proposal_id"]


@pytest.mark.asyncio
async def test_v27_stale_and_reviewed_sources_never_group(admission_db):
    path, _, parent, _ = admission_db
    first, _ = await emit(admission_db, parent)
    _, right = await emit(admission_db, first)
    assert any(
        "recurrence_group" in p for p in await recurrence_projection(items(path), BeliefRepository(path), "symbia")
    )
    sql(path, "UPDATE conversation_log SET content='Changed source' WHERE id=?", (first.id,))
    assert all(
        "recurrence_group" not in p for p in await recurrence_projection(items(path), BeliefRepository(path), "symbia")
    )
    sql(path, "UPDATE belief_review_state SET state='declined' WHERE record_id=?", (right["proposal_id"],))
    assert all(
        "recurrence_group" not in p for p in await recurrence_projection(items(path), BeliefRepository(path), "symbia")
    )


def test_v27_scan_limit_is_visible_and_input_unchanged():
    class Paths:
        def sources(self, agent, entries):
            return {e["id"]: frozenset(range(1, 60)) for e in entries}

    entries = [
        {
            "id": f"{i:02d}",
            "statement": "Exact fragment.",
            "proposal_status": "pending",
            "admission_history": [
                {
                    "policy_version": "belief-v2-explicit-deferred",
                    "statement": "Exact fragment.",
                    "source": {
                        "origin": "chat",
                        "message_id": i + 1,
                        "conversation_id": "c",
                        "message_sha256": "a" * 64,
                    },
                    "context_issues": [
                        "missing_scope",
                        "missing_temporal_scope",
                        "missing_evidence_quote",
                        "missing_consequence",
                    ],
                    "evaluation": {"status": "abstained"},
                }
            ],
        }
        for i in range(51)
    ]
    original = json.dumps(entries, sort_keys=True)
    result = project(entries, Paths(), "symbia")
    assert result[0]["recurrence_group"]["count"] == 50
    assert result[0]["recurrence_group"]["scan_truncated"]
    assert "recurrence_group" not in result[-1]
    assert json.dumps(entries, sort_keys=True) == original
    enriched = dict(entries[0])
    enriched["admission_history"] = [
        entries[0]["admission_history"][0] | {"context_issues": [], "evaluation": {"status": "evaluated"}},
        *entries[0]["admission_history"],
    ]
    assert eligible(enriched) is None
