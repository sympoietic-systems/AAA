"""V126/V127: real repository admission, retry/concurrency, and trace contracts."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.modules.sensory.evidence_triage import EvidenceTriage
from backend.services.belief_admission import admit_candidate
from backend.services.belief_admission_policy import Candidate, context_issues, recommendation
from backend.services.belief_serializer import serialize_proposal
from backend.storage.database import init_db
from backend.storage.repositories import (
    BeliefRepository,
    ConversationRepository,
    MessageRepository,
    NotificationRepository,
)
from backend.utils.belief_candidate import inert_belief_history
from backend.utils.parsers.belief import parse_belief_nucleate_tags


@pytest.fixture
def admission_db(tmp_path):
    path = str(tmp_path / "admission.db")
    init_db(path).close()
    ConversationRepository(path).create("admission-conversation", agent_id="symbia")
    messages = MessageRepository(path)
    parent = messages.insert(
        speaker="human",
        content="A state change must alter the next decision.",
        embedding=b"",
        embedding_model="fixture",
        embedding_dim=0,
        conversation_id="admission-conversation",
    )
    message = messages.insert(
        speaker="apparatus",
        content="Candidate emitted in reply.",
        embedding=b"",
        embedding_model="fixture",
        embedding_dim=0,
        conversation_id="admission-conversation",
        parent_message_id=parent.id,
    )
    return path, messages, parent, message


def candidate(**overrides):
    return {
        "statement": "Stateful memory must change subsequent decisions.",
        "label": "consequential-memory",
        "confidence": 0.88,
        "rationale": "The observed replay failed to change behavior.",
        "consequence": "Reject memory implementations with identical replay decisions.",
        "scope": "Memory replay experiments",
        "temporal_scope": "During repeated-input trials",
        "trigger": "counterexample",
        "evidence_quote": "A state change must alter the next decision.",
        **overrides,
    }


def evaluator():
    client = SimpleNamespace(
        model="fixture-jev",
        is_configured=True,
        evaluate=AsyncMock(
            return_value={
                "success": True,
                "answers": {
                    "consequence": {"choice": "durable", "confidence": 0.99},
                    "grounding": {"choice": "supported", "confidence": 0.99},
                },
            }
        ),
    )

    async def evaluate(state, question_set):
        result = client.evaluate.return_value
        if result.get("success"):
            for key in question_set:
                if key.startswith("relation_"):
                    result["answers"][key] = {"choice": "independent", "confidence": 0.99}
        return result

    client.evaluate.side_effect = evaluate
    return EvidenceTriage(client), client


@pytest.mark.asyncio
async def test_v126_shadow_keeps_single_decisive_insight_for_review(admission_db):
    path, _, _, message = admission_db
    triage, client = evaluator()
    receipt = await admit_candidate(path, message.conversation_id, message.id, candidate(), config={}, evaluator=triage)
    assert receipt["recommendation"] == "new_insight"
    assert receipt["decision"] == "needs_review"
    assert receipt["source"]["message_id"] == message.id
    assert receipt["created_at"].endswith("+00:00") and receipt["assessed_at"].endswith("+00:00")
    proposal = BeliefRepository(path).get_proposal(receipt["proposal_id"])
    assert serialize_proposal(proposal)["lifecycle_stage"] == "candidate"
    assert proposal.admission_history == [receipt]
    assert not any(b.id == receipt["id"] for b in BeliefRepository(path).list_beliefs("symbia"))
    client.evaluate.assert_awaited_once()


@pytest.mark.asyncio
async def test_v126_same_event_retry_does_not_reevaluate_or_retrace(admission_db):
    path, _, _, message = admission_db
    triage, client = evaluator()
    args = (path, message.conversation_id, message.id, candidate())
    first = await admit_candidate(*args, config={}, evaluator=triage)
    assert await admit_candidate(*args, config={}, evaluator=triage) == first
    assert len(BeliefRepository(path).list_proposals("symbia")) == 1
    assert len(NotificationRepository(path).list_all()) == 2
    client.evaluate.assert_awaited_once()


@pytest.mark.asyncio
async def test_v126_concurrent_occurrences_recheck_pending_queue(admission_db):
    path, messages, parent, message = admission_db
    other = messages.insert(
        speaker="apparatus",
        content="Another occurrence",
        embedding=b"",
        embedding_model="fixture",
        embedding_dim=0,
        conversation_id=message.conversation_id,
        parent_message_id=parent.id,
    )
    results = await asyncio.gather(
        *[
            admit_candidate(
                path, message.conversation_id, item.id, candidate(), config={"belief_admission": {"jev_shadow": False}}
            )
            for item in (message, other)
        ]
    )
    assert {r["decision"] for r in results} == {"needs_review", "repetition"}
    proposals = BeliefRepository(path).list_proposals("symbia")
    assert len(proposals) == 1 and len(proposals[0].admission_history) == 2


@pytest.mark.asyncio
async def test_v126_missing_quote_abstains_before_model_and_is_visible(admission_db):
    path, _, _, message = admission_db
    triage, client = evaluator()
    receipt = await admit_candidate(
        path,
        message.conversation_id,
        message.id,
        candidate(evidence_quote="Invented quote"),
        config={},
        evaluator=triage,
    )
    client.evaluate.assert_not_awaited()
    assert "source_quote_not_found" in receipt["context_issues"]
    assert receipt["decision"] == "needs_review"
    assert len(BeliefRepository(path).list_proposals("symbia")) == 1


@pytest.mark.asyncio
async def test_v127_page_and_trace_share_receipt_and_refinement_preserves_it(admission_db):
    path, _, _, message = admission_db
    receipt = await admit_candidate(
        path, message.conversation_id, message.id, candidate(), config={"belief_admission": {"jev_shadow": False}}
    )
    repo = BeliefRepository(path)
    repo.update_proposal_suggestions(receipt["proposal_id"], "refined-label", "Changed statement", None, "refined")
    assert serialize_proposal(repo.get_proposal(receipt["proposal_id"]))["admission_history"] == [receipt]
    traces = NotificationRepository(path).list_all()
    assessed = next(n for n in traces if n["id"].endswith(":assessed"))
    assert assessed["timestamp"] == receipt["assessed_at"]
    assert assessed["source_id"] == receipt["proposal_id"]
    assert json.loads(assessed["snippet"].split("\n\nAdmission receipt:\n")[1]) == receipt


@pytest.mark.asyncio
async def test_v126_provider_failure_retains_review_candidate(admission_db):
    path, _, _, message = admission_db
    triage, client = evaluator()
    client.evaluate.return_value = {"success": False, "error": "private provider body"}
    receipt = await admit_candidate(path, message.conversation_id, message.id, candidate(), config={}, evaluator=triage)
    assert receipt["decision"] == "needs_review"
    assert receipt["evaluation"]["reason"] == "provider_failure"
    assert "private provider body" not in json.dumps(receipt)


def test_v126_conflict_survives_equivalence_and_uncertainty_abstains():
    answers = {
        "consequence": {"choice": "durable", "confidence": 0.99},
        "grounding": {"choice": "supported", "confidence": 0.99},
        "relation_0": {"choice": "equivalent", "confidence": 0.99},
        "relation_1": {"choice": "contradiction", "confidence": 0.99},
    }
    assert recommendation({"status": "evaluated", "answers": answers}, 2) == "conflict"
    answers["relation_1"]["confidence"] = float("nan")
    assert recommendation({"status": "evaluated", "answers": answers}, 2) == "needs_review"


def test_v127_parser_preserves_fields_and_history_is_inert():
    text = '<belief_nucleate label="test" consequence="Compare A &amp; B" scope="art" temporal_scope="now" trigger="insight" evidence_quote="quote">A new claim.</belief_nucleate>'
    cleaned, candidates = parse_belief_nucleate_tags(text)
    assert cleaned == "" and candidates[0]["consequence"] == "Compare A & B"
    assert "<belief_nucleate" not in inert_belief_history(text)
    assert "A new claim." in inert_belief_history(text)
    assert context_issues(Candidate.model_validate(candidate(statement="It changes.")), "")[-1] == "unresolved_referent"
