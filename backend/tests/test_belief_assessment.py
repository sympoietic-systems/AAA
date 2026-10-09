"""T9 deterministic advisory oracles; classifier doubles are not accuracy evidence."""

import asyncio
import hashlib
import json
from datetime import UTC, datetime

import pytest

from backend.errors import ConstraintViolation, ResourceNotFound, ValidationGlitch
from backend.modules.providers.typesafe_provider import TypeSafeDecisionClient
from backend.modules.sensory.belief_context import ClaimContext, ReferenceBinding
from backend.modules.sensory.evidence_triage import EvidenceTriage
from backend.services.belief_admission import _capacity, admit_candidate
from backend.services.belief_assessment import AssessmentSettings, assess_encounter
from backend.services.belief_explicit_intake import explicit_intake
from backend.services.belief_passive_intake import passive_intake
from backend.services.belief_review_contracts import Actor, Encounter, ReviewDecision, SourceReference
from backend.services.belief_review_store import BeliefDecisionStore, BeliefReviewStore
from backend.storage.repositories import BeliefRepository, NotificationRepository
from backend.storage.repositories.cognitive.belief_assessment import BeliefAssessmentRepository
from backend.storage.repositories.cognitive.belief_explicit import ExplicitBeliefRepository
from backend.tests.test_belief_admission import admission_db as admission_db
from backend.tests.test_belief_admission import candidate
from backend.tests.test_belief_review_persistence import sql

CONFIG = {"belief_review": {"origin_intake": {"explicit_chat": True}, "assessment": {"enabled": True}}}
INTAKE = {"belief_review": {"origin_intake": {"explicit_chat": True}}}


class Client:
    model = "jev-requested"
    is_configured = True

    def __init__(self, relation="contradiction", consequence="unclear", factual="unclear", callback=None):
        self.calls = []
        self.relation = relation
        self.consequence = consequence
        self.factual = factual
        self.callback = callback
        self.returned_model = "jev-returned"

    async def evaluate(self, state, questions):
        self.calls.append((state, questions))
        if self.callback:
            await self.callback()
        choices = {
            "consequence": self.consequence,
            "factual_grounding": self.factual,
            "artistic_grounding": "supported",
            "tension": "present",
        }
        answers = {key: {"choice": choices.get(key, self.relation), "confidence": 0.95} for key in questions}
        return {"success": True, "answers": answers, "model": self.returned_model}


async def emit(admission_db, statement="Memory replay must change subsequent decisions.", **changes):
    path, messages, parent, _ = admission_db
    message = messages.insert(
        speaker="apparatus",
        content="Candidate representation: " + statement,
        embedding=b"",
        embedding_model="fixture",
        embedding_dim=0,
        conversation_id=parent.conversation_id,
        parent_message_id=parent.id,
    )
    receipt = await explicit_intake(
        path,
        parent.conversation_id,
        message.id,
        candidate(statement=statement, evidence_quote=parent.content, **changes),
        config=INTAKE,
        origin="chat",
    )
    return receipt, message


async def pair(admission_db):
    path = admission_db[0]
    sql(path, "DELETE FROM belief_nodes")
    left, _ = await emit(admission_db)
    right, _ = await emit(admission_db, "Memory replay must preserve identical decisions.")
    return left, right


@pytest.mark.asyncio
async def test_v4_v8_v10_conflict_survives_uncertain_warrant_without_authority(admission_db):
    path = admission_db[0]
    left, right = await pair(admission_db)
    before = sql(path, "SELECT id,status,nucleation_mass,confidence FROM belief_proposals ORDER BY id")
    client = Client()
    assessment = await assess_encounter(
        path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(client)
    )
    assert assessment.evaluator_status == "evaluated"
    assert assessment.relations[0].relation == "contradiction"
    assert assessment.relations[0].comparison_id == right["proposal_id"]
    assert assessment.previous_assessment_id == left["assessment_id"]
    assert assessment.requested_model == "jev-requested" and assessment.returned_model == "jev-returned"
    assert "Consequence=unclear" in assessment.challenge
    assert {w.name for w in assessment.warrant_dimensions} == {
        "empirical_traced",
        "artistic_axiomatic",
        "unresolved_tension",
    }
    assert assessment.warrant_dimensions[0].independence_status == "unknown"
    assert assessment.warrant_dimensions[0].source_refs == (f"message:{admission_db[2].id}",)
    assert all(w.independence_status == "internal" for w in assessment.warrant_dimensions[1:])
    assert "factual_grounding=unclear" in assessment.warrant_dimensions[0].basis
    assert "artistic_grounding=supported" in assessment.warrant_dimensions[1].basis
    assert sql(path, "SELECT id,status,nucleation_mass,confidence FROM belief_proposals ORDER BY id") == before
    assert not sql(path, "SELECT id FROM belief_review_decisions")
    projection = ExplicitBeliefRepository(path).projection("symbia", left["encounter_id"])
    assert projection["assessment_id"] == assessment.id
    assert projection["recommendation"] == "conflict"
    assert projection["evaluation"]["answers"]["grounding"]["choice"] == "unclear"
    assert projection["evaluation"]["input_sha256"] == assessment.context_hash
    assert len(BeliefRepository(path).get_proposal(left["proposal_id"]).admission_history) == 2
    trace = next(n for n in NotificationRepository(path).list_all() if n["id"] == assessment.id + ":assessed")
    assert json.loads(trace["snippet"].split("\n\nAdmission receipt:\n")[1]) == projection


@pytest.mark.asyncio
async def test_v2_v6_concurrent_retry_is_single_call_and_failed_outcome_not_replayed(admission_db):
    path = admission_db[0]
    left, _ = await pair(admission_db)
    client = Client()
    results = await asyncio.gather(
        *[
            assess_encounter(path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(client))
            for _ in range(6)
        ]
    )
    assert len(client.calls) == 1
    assert len({r.id for r in results}) == 1
    final = await assess_encounter(
        path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(client)
    )
    assert final.evaluator_status == "evaluated" and len(client.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", ["contradiction " * 100, "unknown-label", True, "", "insufficient"])
async def test_v6_repetitive_and_malformed_choices_are_visible(admission_db, answer):
    path = admission_db[0]
    left, _ = await pair(admission_db)
    client = Client(relation=answer)
    result = await assess_encounter(
        path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(client)
    )
    if answer == "insufficient":
        assert result.evaluator_status == "evaluated"
        assert result.relations[0].relation == "insufficient_context"
    else:
        assert result.evaluator_status == "abstained" and not result.relations
        assert result.abstain_reason == "invalid_repetitive_or_uncertain_answers"
    await assess_encounter(path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(client))
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_v3_unresolved_or_stale_referents_abstain_before_provider(admission_db):
    path = admission_db[0]
    left, _ = await emit(admission_db, "It must change later decisions.")
    client = Client()
    result = await assess_encounter(
        path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(client)
    )
    assert result.evaluator_status == "abstained" and not client.calls
    assert not result.relations


@pytest.mark.asyncio
async def test_v3_unknown_comparison_context_cannot_acquire_relation(admission_db):
    path = admission_db[0]
    left, _ = await pair(admission_db)
    # Own stored legacy text is available, but its claim conditions are unknown.
    sql(path, "UPDATE belief_review_state SET state='deferred' WHERE record_id!=?", (left["proposal_id"],))
    right, _ = await emit(admission_db, "A local replay observation.", scope="unknown", temporal_scope="unknown")
    client = Client()
    result = await assess_encounter(
        path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(client)
    )
    relation = next(r for r in result.relations if r.comparison_id == right["proposal_id"])
    assert relation.relation == "insufficient_context" and relation.assessment_confidence is None
    assert all(p["id"] != right["proposal_id"] for p in client.calls[0][0]["comparisons"])


@pytest.mark.asyncio
async def test_v3_v10_different_conditions_do_not_form_equivalence_or_contradiction(admission_db):
    path = admission_db[0]
    sql(path, "DELETE FROM belief_nodes")
    left, _ = await emit(admission_db)
    right, _ = await emit(
        admission_db,
        "Memory replay preserves decisions under changed conditions.",
        scope="Different trial",
        temporal_scope="Future trial",
    )
    client = Client()
    result = await assess_encounter(
        path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(client)
    )
    assert result.relations[0].comparison_id == right["proposal_id"]
    assert result.relations[0].relation == "insufficient_context"
    assert (
        result.relations[0].raw_relation == "contradiction" and result.relations[0].reason == "scope_or_time_mismatch"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("target", ["source", "parent", "comparison", "scope"])
async def test_v3_v6_changed_inputs_during_provider_are_stale(admission_db, target):
    path, _, parent, _ = admission_db
    left, right = await pair(admission_db)

    async def mutate():
        if target == "source":
            statement = "UPDATE conversation_log SET content='changed' WHERE id=(SELECT source_id FROM belief_encounters WHERE id=?)"
            params = (left["encounter_id"],)
        elif target == "parent":
            statement, params = "UPDATE conversation_log SET content='changed' WHERE id=?", (parent.id,)
        elif target == "comparison":
            statement, params = (
                "UPDATE belief_proposals SET suggested_statement='changed' WHERE id=?",
                (right["proposal_id"],),
            )
        else:
            statement, params = (
                "UPDATE belief_review_state SET scope='changed',version=version+1 WHERE record_id=?",
                (right["proposal_id"],),
            )
        await asyncio.to_thread(sql, path, statement, params)

    result = await assess_encounter(
        path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(Client(callback=mutate))
    )
    assert result.evaluator_status == "stale"
    assert all(r.relation == "insufficient_context" for r in result.relations)
    assert not sql(path, "SELECT id FROM belief_review_decisions")


@pytest.mark.asyncio
async def test_v6_stale_completed_replay_is_rejected_and_new_attempt_retains_history(admission_db):
    path = admission_db[0]
    left, right = await pair(admission_db)
    client = Client()
    first = await assess_encounter(
        path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(client)
    )
    sql(
        path,
        "UPDATE belief_proposals SET suggested_statement='Different comparison' WHERE id=?",
        (right["proposal_id"],),
    )
    with pytest.raises(ConstraintViolation):
        await assess_encounter(path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(client))
    second = await assess_encounter(
        path,
        "symbia",
        left["encounter_id"],
        config=CONFIG,
        evaluator=EvidenceTriage(client),
        attempt_id="operator-retry",
    )
    assert second.previous_assessment_id == first.id and len(client.calls) == 2
    assert await BeliefReviewStore(path).get_assessment("symbia", first.id) == first
    assert len(ExplicitBeliefRepository(path).history(left["proposal_id"])) == 3


@pytest.mark.asyncio
async def test_v6_v19_outage_and_cancellation_do_not_replay(admission_db):
    path = admission_db[0]
    left, _ = await pair(admission_db)

    async def outage():
        raise OSError("Sensitive provider body must not be recorded")

    client = Client(callback=outage)
    result = await assess_encounter(
        path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(client)
    )
    assert result.evaluator_status == "unavailable" and result.abstain_reason == "OSError"
    await assess_encounter(path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(client))
    assert len(client.calls) == 1
    started = asyncio.Event()

    async def wait():
        started.set()
        await asyncio.Event().wait()

    cancelled_client = Client(callback=wait)
    task = asyncio.create_task(
        assess_encounter(
            path,
            "symbia",
            left["encounter_id"],
            config=CONFIG,
            evaluator=EvidenceTriage(cancelled_client),
            attempt_id="operator-cancel",
        )
    )
    await asyncio.wait_for(started.wait(), timeout=5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    result = await assess_encounter(
        path,
        "symbia",
        left["encounter_id"],
        config=CONFIG,
        evaluator=EvidenceTriage(cancelled_client),
        attempt_id="operator-cancel",
    )
    assert result.evaluator_status == "failed" and "outcome_unknown" in result.abstain_reason
    assert len(cancelled_client.calls) == 1


@pytest.mark.asyncio
async def test_v19_capacity_exhaustion_is_visible_without_call(admission_db):
    path = admission_db[0]
    left, _ = await pair(admission_db)
    capacity = _capacity()
    await capacity.acquire()
    await capacity.acquire()
    client = Client()
    config = {"belief_review": {"assessment": {"enabled": True, "capacity_wait": 0.01}}}
    try:
        result = await assess_encounter(
            path, "symbia", left["encounter_id"], config=config, evaluator=EvidenceTriage(client)
        )
    finally:
        capacity.release()
        capacity.release()
    assert result.evaluator_status == "unavailable" and result.abstain_reason == "capacity_exhausted"
    assert not client.calls


@pytest.mark.asyncio
async def test_v6_v20_prior_verdicts_are_not_classifier_evidence(admission_db):
    path = admission_db[0]
    left, right = await pair(admission_db)
    client = Client()
    await assess_encounter(path, "symbia", right["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(client))
    client.calls.clear()
    await assess_encounter(path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(client))
    payload = json.dumps(client.calls[0][0])
    for forbidden in (
        "evaluator_status",
        "legacy_status",
        "review_state",
        "assessment_confidence",
        "returned_model",
        "previous_assessment_id",
    ):
        assert forbidden not in payload
    assert "source_activity" in payload and "No adoption" in json.dumps(client.calls[0][1])
    with pytest.raises(ResourceNotFound):
        await assess_encounter(path, "other", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(Client()))


@pytest.mark.asyncio
async def test_v1_actual_explicit_admission_uses_default_off_independent_flag(admission_db):
    path, _, parent, message = admission_db
    sql(path, "DELETE FROM belief_nodes")
    client = Client()
    disabled = await admit_candidate(
        path, parent.conversation_id, message.id, candidate(), config=INTAKE, evaluator=EvidenceTriage(client)
    )
    assert not client.calls and disabled["policy_version"] == "belief-v2-explicit-deferred"
    enabled = await admit_candidate(
        path, parent.conversation_id, message.id, candidate(), config=CONFIG, evaluator=EvidenceTriage(client)
    )
    assert len(client.calls) == 1 and enabled["policy_version"] == "belief-v2-advisory-v1"
    assert enabled["evaluation"]["status"] == "evaluated"
    assert enabled["decision"] == "needs_review"


def test_v19_settings_are_strict_and_finite():
    from pydantic import ValidationError

    for values in (
        {"enabled": "false"},
        {"max_active": 0},
        {"max_active": 1025},
        {"call_timeout": 31.0},
        {"capacity_wait": 6.0},
        {"confidence_floor": float("nan")},
    ):
        with pytest.raises(ValidationError):
            AssessmentSettings.model_validate(values)


@pytest.mark.asyncio
@pytest.mark.parametrize("resolution", ["valid", "ambiguous", "stale", "unknown_scope"])
async def test_v3_explicit_referent_bindings_never_invent_antecedents(admission_db, resolution):
    path, messages, parent, _ = admission_db
    statement = "It changes subsequent decisions."
    message = messages.insert(
        speaker="human",
        content=statement,
        embedding=b"",
        embedding_model="fixture",
        embedding_dim=0,
        conversation_id=parent.conversation_id,
    )
    digest = hashlib.sha256(statement.encode()).hexdigest()
    saved = await BeliefReviewStore(path).register(
        Encounter(
            id="referent-encounter",
            agent_id="symbia",
            origin="passive_chat",
            segment_id="segment:0",
            statement=statement,
            statement_sha256=digest,
            received_at=datetime.now(UTC),
            source=SourceReference(
                source_type="message",
                source_id=str(message.id),
                source_sha256=digest,
                quote=statement,
                context_status="available",
            ),
        )
    )
    context = ClaimContext(
        statement_sha256="0" * 64 if resolution == "stale" else digest,
        scope="unknown" if resolution == "unknown_scope" else "Named memory replay trial",
        temporal_scope="During the trial",
        provenance="explicit-test-annotation",
        resolution="resolved",
        bindings=(
            ReferenceBinding(
                start=0,
                end=2,
                candidates=("memory replay", "another apparatus") if resolution == "ambiguous" else ("memory replay",),
                confidence=0.95,
            ),
        ),
    )
    client = Client()
    result = await assess_encounter(
        path, "symbia", saved.encounter.id, config=CONFIG, evaluator=EvidenceTriage(client), context=context
    )
    assert (result.evaluator_status == "evaluated") == (resolution == "valid")
    assert len(client.calls) == int(resolution == "valid")
    if resolution == "valid":
        assert result.referent_contexts[0].context.bindings[0].candidates == ("memory replay",)
    else:
        assert not result.referent_contexts


@pytest.mark.asyncio
async def test_v5_nomination_includes_pending_adopted_and_deferred(admission_db):
    path = admission_db[0]
    left, pending = await pair(admission_db)
    adopted, _ = await emit(admission_db, "Replay selection follows a declared commitment.")
    deferred, _ = await emit(admission_db, "Replay attention requires another trial.")
    actor = Actor(kind="operator", principal_id="fixture-operator", auth_context_id="fixture-auth")
    for record, state in ((adopted, "adopted"), (deferred, "deferred")):
        saved = await BeliefReviewStore(path).get_encounter("symbia", record["encounter_id"])
        decision = ReviewDecision(
            id="decision:" + state,
            agent_id="symbia",
            record_id=record["proposal_id"],
            statement_sha256=saved.encounter.statement_sha256,
            actor=actor,
            authority="operator_review",
            policy_version="fixture-declared",
            expected_review_version=0,
            previous_state="candidate",
            next_state=state,
            scope=saved.encounter.scope,
            rationale="Explicit fixture decision",
            consequence="Retain declared trial",
            challenge="Retain disagreement",
            timestamp=datetime.now(UTC),
            assessment_ids=(record["assessment_id"],),
        )
        await BeliefDecisionStore(path).commit(decision, authenticated_actor=actor)
    before = sql(path, "SELECT decision_json FROM belief_review_decisions ORDER BY id")
    result = await assess_encounter(
        path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(Client())
    )
    snapshots = {s.record_id: s for s in result.comparison_snapshots}
    assert {pending["proposal_id"], adopted["proposal_id"], deferred["proposal_id"]} <= set(snapshots)
    assert snapshots[adopted["proposal_id"]].review_state == "adopted"
    assert snapshots[deferred["proposal_id"]].review_state == "deferred"
    assert sql(path, "SELECT decision_json FROM belief_review_decisions ORDER BY id") == before


@pytest.mark.asyncio
async def test_v5_v19_nomination_scan_and_comparisons_are_bounded(admission_db):
    path = admission_db[0]
    left, _ = await pair(admission_db)
    for i in range(115):
        sql(
            path,
            "INSERT INTO belief_nodes(id,label,statement,agent_id,vector_16d) VALUES(?,?,?,'symbia','[]')",
            (f"legacy:{i:03}", f"legacy-{i}", "Replay changes a local apparatus."),
        )
    for i in range(70):
        sql(
            path,
            "INSERT INTO belief_proposals(id,agent_id,provisional_statement,status,source_trace,initial_signature) VALUES(?,'symbia',?,'pending','[]','[]')",
            (f"pending:{i:03}", "Replay changes a local condition."),
        )
    records = BeliefAssessmentRepository(path).nominees("symbia", left["proposal_id"])
    assert len([r for r in records if r["stratum"] == "adopted_or_legacy"]) == 100
    assert len([r for r in records if r["stratum"] == "pending"]) == 64
    result = await assess_encounter(
        path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(Client())
    )
    assert len(result.comparison_snapshots) == 10
    assert any(s.record_kind == "belief" for s in result.comparison_snapshots)
    assert any(s.record_kind == "proposal" for s in result.comparison_snapshots)


@pytest.mark.asyncio
async def test_v19_durable_queue_exhaustion_has_terminal_receipt(admission_db):
    path = admission_db[0]
    left, right = await pair(admission_db)
    started = asyncio.Event()
    release = asyncio.Event()

    async def wait():
        started.set()
        await release.wait()

    config = {"belief_review": {"assessment": {"enabled": True, "max_active": 1}}}
    first = asyncio.create_task(
        assess_encounter(
            path, "symbia", left["encounter_id"], config=config, evaluator=EvidenceTriage(Client(callback=wait))
        )
    )
    await asyncio.wait_for(started.wait(), timeout=5)
    second_client = Client()
    try:
        second = await assess_encounter(
            path, "symbia", right["encounter_id"], config=config, evaluator=EvidenceTriage(second_client)
        )
        assert second.evaluator_status == "unavailable" and second.abstain_reason == "queue_exhausted"
        assert not second_client.calls
        assert sql(path, "SELECT count(*) FROM belief_admission WHERE status='assessing'")[0][0] == 1
    finally:
        release.set()
        await first


@pytest.mark.asyncio
async def test_v6_source_stale_before_dispatch_is_recorded_without_call(admission_db):
    path, _, parent, _ = admission_db
    left, _ = await pair(admission_db)
    sql(path, "UPDATE conversation_log SET content='changed' WHERE id=?", (parent.id,))
    client = Client()
    result = await assess_encounter(
        path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(client)
    )
    assert result.evaluator_status == "stale" and not client.calls


@pytest.mark.asyncio
async def test_v19_zero_capacity_wait_acquires_free_slot(admission_db):
    path = admission_db[0]
    left, _ = await pair(admission_db)
    client = Client()
    result = await assess_encounter(
        path,
        "symbia",
        left["encounter_id"],
        config={"belief_review": {"assessment": {"enabled": True, "capacity_wait": 0.0}}},
        evaluator=EvidenceTriage(client),
    )
    assert result.evaluator_status == "evaluated" and len(client.calls) == 1


@pytest.mark.asyncio
async def test_v6_v19_timeout_is_bounded_without_replay(admission_db):
    path = admission_db[0]
    left, _ = await pair(admission_db)

    async def hang():
        await asyncio.Event().wait()

    client = Client(callback=hang)
    config = {"belief_review": {"assessment": {"enabled": True, "call_timeout": 1.0}}}
    result = await assess_encounter(
        path, "symbia", left["encounter_id"], config=config, evaluator=EvidenceTriage(client)
    )
    assert result.evaluator_status == "unavailable" and result.abstain_reason == "TimeoutError"
    await assess_encounter(path, "symbia", left["encounter_id"], config=config, evaluator=EvidenceTriage(client))
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_v1_paused_origin_cannot_run_evaluator(admission_db):
    path, messages, parent, _ = admission_db
    await pair(admission_db)  # Durable promotion marker.
    message = messages.insert(
        speaker="apparatus",
        content="Fresh paused nomination",
        embedding=b"",
        embedding_model="fixture",
        embedding_dim=0,
        conversation_id=parent.conversation_id,
        parent_message_id=parent.id,
    )
    client = Client()
    config = {"belief_review": {"origin_intake": {"explicit_chat": False}, "assessment": {"enabled": True}}}
    result = await admit_candidate(
        path,
        parent.conversation_id,
        message.id,
        candidate(statement="Replay attention remains provisional."),
        config=config,
        evaluator=EvidenceTriage(client),
    )
    assert result["evaluation"]["reason"] == "origin_paused" and not client.calls


@pytest.mark.asyncio
async def test_v20_unsafe_returned_metadata_fails_without_sediment(admission_db, monkeypatch):
    path = admission_db[0]
    left, _ = await pair(admission_db)
    secret = "synthetic-only-private-credential"
    monkeypatch.setenv("AAA_PASSWORD", secret)
    client = Client()
    client.returned_model = secret
    result = await assess_encounter(
        path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(client)
    )
    assert result.evaluator_status == "failed" and result.abstain_reason == "unsafe_provider_metadata"
    assert result.returned_model is None and not result.relations
    assert all(secret not in row[0] for row in sql(path, "SELECT receipt FROM belief_admission"))
    assert all(secret not in row[0] for row in sql(path, "SELECT snippet FROM notifications"))


@pytest.mark.asyncio
async def test_v20_unsafe_source_rejected_before_provider(admission_db, monkeypatch):
    path, _, parent, _ = admission_db
    left, _ = await pair(admission_db)
    monkeypatch.setenv("AAA_PASSWORD", parent.content)
    client = Client()
    with pytest.raises(ValidationGlitch):
        await assess_encounter(path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(client))
    assert not client.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("origin", ["passive_chat", "document"])
async def test_v1_v3_supplied_context_reviews_actual_origin_without_rewriting_encounter(admission_db, origin):
    path, _, parent, _ = admission_db
    if origin == "document":
        from backend.tests.test_belief_external_intake import document

        document(path)
    initial = passive_intake(
        path,
        "symbia",
        parent.content,
        origin=origin,
        source_id="file.txt" if origin == "document" else str(parent.id),
        segment_id="source:0",
        conversation_id=parent.conversation_id,
        config={"belief_review": {"origin_intake": {origin: True}}},
    )
    context = ClaimContext(
        statement_sha256=hashlib.sha256(initial["statement"].encode()).hexdigest(),
        scope="Declared source observation",
        temporal_scope="During fixture trial",
        provenance="explicit-operator-declaration",
        resolution="resolved",
    )
    result = await assess_encounter(
        path, "symbia", initial["encounter_id"], config=CONFIG, context=context, evaluator=EvidenceTriage(Client())
    )
    assert result.evaluator_status == "evaluated"
    projection = ExplicitBeliefRepository(path).projection("symbia", initial["encounter_id"])
    assert projection["scope"] == context.scope and projection["temporal_scope"] == context.temporal_scope
    assert projection["source"]["scope"] == ""
    assert "scope_and_temporal_scope_unresolved" not in projection["context_issues"]
    assert "scope_and_temporal_scope_unresolved" in projection["origin_context_issues"]
    saved = await BeliefReviewStore(path).get_encounter("symbia", initial["encounter_id"])
    assert saved.encounter.scope == "" and saved.encounter.temporal_scope == ""


@pytest.mark.asyncio
async def test_v6_v20_provider_metadata_is_honest_and_error_bodies_not_logged(caplog):
    from unittest.mock import AsyncMock, MagicMock, patch

    client = TypeSafeDecisionClient(api_key="synthetic-key", model="requested-fixture")
    definitions = {"q": {"type": "choice", "criteria": {"safe": "Safe"}}}
    response = MagicMock(status_code=200)
    response.json.return_value = {"answers": {"q": {"choice": "safe", "confidence": 0.95}}}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=response):
        result = await EvidenceTriage(client).evaluate({"source": "data"}, definitions)
    assert result["status"] == "evaluated" and result["returned_model"] is None
    response.status_code = 403
    response.text = "SENSITIVE_PROVIDER_ERROR_BODY"
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=response):
        result = await EvidenceTriage(client).evaluate({"source": "data"}, definitions)
    assert result["status"] == "unavailable" and result["reason"] == "provider_failure"
    assert "SENSITIVE_PROVIDER_ERROR_BODY" not in caplog.text
    assert "SENSITIVE_PROVIDER_ERROR_BODY" not in json.dumps(result)
