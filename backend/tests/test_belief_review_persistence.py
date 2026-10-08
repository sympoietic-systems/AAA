"""T5 storage oracles: real isolated WAL databases, no providers or production access."""

import asyncio
import hashlib
import sqlite3
import threading
from contextlib import closing
from datetime import timedelta

import pytest
from pydantic import ValidationError

from backend.errors import ConstraintViolation, ResourceNotFound, SecurityViolation, ValidationGlitch
from backend.services.belief_review_contracts import (
    Actor,
    Assessment,
    ComparisonSnapshot,
    RelationObservation,
    ReviewDecision,
    SourceReference,
)
from backend.services.belief_review_store import BeliefDecisionStore, BeliefReviewStore
from backend.storage.database import get_connection, init_db
from backend.storage.migrations.m060_belief_admission import up as old_admission_schema
from backend.storage.migrations.m064_belief_review_persistence import up
from backend.storage.repositories.cognitive.belief import BeliefRepository
from backend.storage.repositories.cognitive.belief_admission import AdmissionRepository
from backend.tests.test_belief_review_contracts import HASH, NOW, STATEMENT, encounter


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "belief_review.db")
    init_db(path).close()
    sql(
        path,
        "INSERT INTO conversations(id,title,agent_id) VALUES ('fixture','Fixture','symbia'),('other','Other','other')",
    )
    sql(
        path,
        "INSERT INTO conversation_log(id,speaker,content,conversation_id,embedding,embedding_model,embedding_dim) "
        "VALUES (42,'human',?,'fixture',X'','fixture',0),(43,'human',?,'other',X'','fixture',0)",
        (STATEMENT, STATEMENT),
    )
    return path


def incoming(**changes):
    source = changes.pop(
        "source",
        SourceReference(
            source_type="message",
            context_status="available",
            source_id="43" if changes.get("agent_id") == "other" else "42",
            source_sha256=HASH,
            quote=STATEMENT,
        ),
    )
    return encounter(
        source=source,
        **changes,
    )


def assessment(saved, **changes):
    return Assessment(
        **(
            {
                "id": "assessment:1",
                "agent_id": saved.encounter.agent_id,
                "encounter_id": saved.encounter.id,
                "candidate_id": saved.record_id,
                "policy_version": "v2-shadow",
                "rubric_version": "v1",
                "context_hash": HASH,
                "referent_status": "unknown",
                "evaluator_status": "pending",
                "started_at": NOW,
                "requested_model": "fixture",
            }
            | changes
        )
    )


def complete(value, **changes):
    return Assessment.model_validate(
        value.model_dump()
        | {
            "evaluator_status": "evaluated",
            "referent_status": "validated",
            "completed_at": NOW + timedelta(seconds=1),
        }
        | changes
    )


OPERATOR = Actor(kind="operator", principal_id="operator", auth_context_id="session:fixture")


def decision(saved, **changes):
    return ReviewDecision(
        **(
            {
                "id": "decision:1",
                "agent_id": saved.encounter.agent_id,
                "record_id": saved.record_id,
                "statement_sha256": saved.encounter.statement_sha256,
                "actor": OPERATOR,
                "authority": "operator_review",
                "policy_version": "operator-review-v1",
                "expected_review_version": 0,
                "previous_state": "candidate",
                "next_state": "adopted",
                "scope": saved.encounter.scope,
                "rationale": "Explicit situated commitment",
                "consequence": "Change replay selection",
                "challenge": "Test counterexamples",
                "dissent": ("Retain scoped objection",),
                "timestamp": NOW + timedelta(seconds=3),
            }
            | changes
        )
    )


def sql(db, query, params=()):
    with closing(get_connection(db)) as conn, conn:
        result = conn.execute(query, params).fetchall()
    return result


@pytest.mark.asyncio
async def test_v2_concurrent_source_retry_and_scoped_claim_grouping(db):
    store = BeliefReviewStore(db)
    results = await asyncio.gather(*(store.register(incoming(id=f"encounter:{i}")) for i in range(12)))
    assert sum(r.created for r in results) == 1
    assert len({r.encounter.id for r in results}) == 1
    assert len(sql(db, "SELECT id FROM belief_proposals")) == 1
    second = await store.register(incoming(id="another", segment_id="tag:1"))
    assert second.created and second.record_id == results[0].record_id
    assert len(sql(db, "SELECT id FROM belief_encounters")) == 2
    assert sql(db, "SELECT version,state FROM belief_review_state")[0][0:] == (0, "candidate")


@pytest.mark.asyncio
async def test_v2_changed_retry_input_is_conflict_not_overwrite(db):
    store = BeliefReviewStore(db)
    await store.register(incoming())
    with pytest.raises(ConstraintViolation):
        await store.register(incoming(id="retry", scope="different scope"))
    with pytest.raises(ConstraintViolation):
        await store.register(incoming(segment_id="different emission"))
    assert len(sql(db, "SELECT id FROM belief_encounters")) == 1


@pytest.mark.asyncio
async def test_v3_unknown_context_or_scope_does_not_mint_grouping_guarantees(db):
    store = BeliefReviewStore(db)
    missing = SourceReference(source_type="message", context_status="missing", unavailable_reason="Missing binding")
    a = await store.register(incoming(id="a", source=missing, scope=""))
    b = await store.register(incoming(id="b", source=missing, scope=""))
    c = await store.register(incoming(id="c", scope="unknown"))
    d = await store.register(incoming(id="d", scope="unknown", segment_id="different"))
    assert len({r.record_id for r in (a, b, c, d)}) == 4
    assert all(row[0] == "awaiting_context" for row in sql(db, "SELECT state FROM belief_review_state"))


@pytest.mark.asyncio
async def test_v20_agent_isolation_in_records_receipts_and_decisions(db):
    store = BeliefReviewStore(db)
    a = await store.register(incoming())
    b = await store.register(incoming(agent_id="other"))
    assert a.record_id != b.record_id
    pending = assessment(a)
    await store.start_assessment(pending)
    with pytest.raises(ResourceNotFound):
        await store.get_assessment("other", pending.id)
    await store.complete_assessment(complete(pending))
    decisions = BeliefDecisionStore(db)
    await decisions.commit(decision(a), authenticated_actor=OPERATOR)
    with pytest.raises(ResourceNotFound):
        await decisions.get_decision("other", "decision:1")
    with pytest.raises(ResourceNotFound):
        await decisions.get_state("other", a.record_id)
    with pytest.raises(ConstraintViolation):
        await store.start_assessment(assessment(b, candidate_id=a.record_id))
    assert (await store.get_encounter("SYMBIA", a.encounter.id)).record_id == a.record_id


@pytest.mark.asyncio
async def test_v12_v21_pending_restart_is_visible_and_never_auto_replayed(db):
    store = BeliefReviewStore(db)
    saved = await store.register(incoming())
    pending = assessment(saved)
    await store.start_assessment(pending)
    restarted = BeliefReviewStore(db)
    work = await restarted.unfinished("symbia")
    assert len(work) == 1 and work[0].pending_assessment_id == pending.id
    assert (await restarted.start_assessment(pending)).evaluator_status == "pending"
    with pytest.raises(ConstraintViolation):
        await restarted.start_assessment(assessment(saved, id="competing"))
    finished = await restarted.complete_assessment(complete(pending))
    assert finished == await restarted.complete_assessment(complete(pending))
    assert not await restarted.unfinished("symbia")
    assert not hasattr(restarted, "commit")
    assert not hasattr(restarted.repository, "commit_decision")
    assert (await BeliefDecisionStore(db).get_state("symbia", saved.record_id)).state == "candidate"


@pytest.mark.asyncio
async def test_v12_completed_assessment_and_history_are_immutable(db):
    store = BeliefReviewStore(db)
    saved = await store.register(incoming())
    pending = assessment(saved)
    await store.start_assessment(pending)
    await store.complete_assessment(complete(pending))
    with pytest.raises(ConstraintViolation):
        await store.complete_assessment(complete(pending, challenge="Changed after completion"))
    for query in (
        "UPDATE belief_admission SET receipt='{}' WHERE assessment_id IS NOT NULL",
        "DELETE FROM belief_encounters",
        "DELETE FROM belief_review_assessments",
        "DELETE FROM belief_admission",
    ):
        with pytest.raises(sqlite3.IntegrityError):
            sql(db, query)
    second = assessment(
        saved, id="assessment:2", previous_assessment_id=pending.id, started_at=NOW + timedelta(seconds=2)
    )
    await store.start_assessment(second)
    await store.complete_assessment(complete(second, completed_at=NOW + timedelta(seconds=3)))
    assert len(sql(db, "SELECT id FROM belief_review_assessments")) == 2
    assert not AdmissionRepository(db).history(saved.record_id)


@pytest.mark.asyncio
async def test_v11_concurrent_decisions_compare_and_swap_one_winner(db):
    saved = await BeliefReviewStore(db).register(incoming())
    store = BeliefDecisionStore(db)
    results = await asyncio.gather(
        *(store.commit(decision(saved, id=f"decision:{i}"), authenticated_actor=OPERATOR) for i in range(8)),
        return_exceptions=True,
    )
    assert sum(isinstance(r, ReviewDecision) for r in results) == 1
    assert sum(isinstance(r, ConstraintViolation) for r in results) == 7
    assert len(sql(db, "SELECT id FROM belief_review_decisions")) == 1
    state = await store.get_state("symbia", saved.record_id)
    assert state.version == 1 and state.state == "adopted"
    assert sql(db, "SELECT status FROM belief_proposals")[0][0] == "pending"


@pytest.mark.asyncio
async def test_v11_v25_decision_retry_authentication_and_statement_binding(db):
    saved = await BeliefReviewStore(db).register(incoming())
    store = BeliefDecisionStore(db)
    command = decision(saved)
    with pytest.raises(SecurityViolation):
        await store.commit(command, authenticated_actor=Actor(kind="system", principal_id="worker"))
    result = await store.commit(command, authenticated_actor=OPERATOR)
    assert result == await store.commit(command, authenticated_actor=OPERATOR)
    with pytest.raises(ConstraintViolation):
        await store.commit(decision(saved, rationale="Changed retry"), authenticated_actor=OPERATOR)
    changed = "Changed record"
    sql(db, "UPDATE belief_proposals SET provisional_statement=? WHERE id=?", (changed, saved.record_id))
    with pytest.raises(ConstraintViolation):
        await store.commit(
            decision(saved, id="new", expected_review_version=1, previous_state="adopted"), authenticated_actor=OPERATOR
        )
    assert len(sql(db, "SELECT id FROM belief_review_decisions")) == 1
    standing = await store.get_state("symbia", saved.record_id)
    assert standing.state == "adopted" and standing.binding_status == "stale"
    assert standing.statement_hash != standing.current_statement_hash
    with pytest.raises(ConstraintViolation):
        await BeliefReviewStore(db).register(incoming(id="new-encounter", segment_id="new emission"))


@pytest.mark.asyncio
async def test_v11_decision_and_state_rollback_together(db):
    saved = await BeliefReviewStore(db).register(incoming())
    sql(db, "CREATE TRIGGER fail_state BEFORE UPDATE ON belief_review_state BEGIN SELECT RAISE(ABORT,'fixture'); END")
    with pytest.raises(sqlite3.IntegrityError):
        await BeliefDecisionStore(db).commit(decision(saved), authenticated_actor=OPERATOR)
    assert not sql(db, "SELECT id FROM belief_review_decisions")
    assert sql(db, "SELECT version,state FROM belief_review_state")[0][0:] == (0, "candidate")


@pytest.mark.asyncio
async def test_v3_atomic_candidate_recheck_finishes_stale_without_verdict(db):
    store = BeliefReviewStore(db)
    saved = await store.register(incoming())
    pending = assessment(saved)
    await store.start_assessment(pending)
    sql(db, "UPDATE belief_proposals SET provisional_statement='Changed' WHERE id=?", (saved.record_id,))
    result = await store.complete_assessment(complete(pending))
    assert result.evaluator_status == "stale" and result.referent_status == "stale"
    assert (await BeliefDecisionStore(db).get_state("symbia", saved.record_id)).state == "candidate"


def test_v21_additive_migration_is_idempotent_and_preserves_legacy_rows(db):
    sql(
        db,
        "INSERT INTO belief_admission (id,event_key,statement_key,status,receipt,created_at) "
        "VALUES ('legacy','legacy-key','legacy-statement','complete','{}','2026-01-01')",
    )
    with get_connection(db) as conn:
        before = tuple(conn.execute("SELECT * FROM belief_admission WHERE id='legacy'").fetchone())
        up(conn)
        up(conn)
        after = tuple(conn.execute("SELECT * FROM belief_admission WHERE id='legacy'").fetchone())
        assert before == after
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    conn.close()
    sql(db, "UPDATE belief_admission SET receipt='legacy-compatible' WHERE id='legacy'")


@pytest.mark.asyncio
async def test_v19_v20_bounds_and_secret_hash_policy(db):
    store = BeliefReviewStore(db)
    unsafe = "Bearer sensitive-token"
    with pytest.raises(ValidationGlitch):
        await store.register(incoming(statement=unsafe, statement_sha256=hashlib.sha256(unsafe.encode()).hexdigest()))
    assert not sql(db, "SELECT id FROM belief_encounters")
    with pytest.raises(ValidationError):
        await store.unfinished("../other")
    for i in range(3):
        await store.register(incoming(id=f"enc:{i}", segment_id=f"tag:{i}"))
    first = await store.unfinished("symbia", limit=0)
    assert len(first) == 1
    assert len(await store.unfinished("symbia", after_id="enc:0", limit=5000)) == 2


@pytest.mark.asyncio
async def test_v20_available_message_binding_requires_owner_hash_and_literal_quote(db):
    store = BeliefReviewStore(db)
    foreign = incoming().source.model_copy(update={"source_id": "43"})
    with pytest.raises(ResourceNotFound):
        await store.register(incoming(source=foreign))
    with pytest.raises(ConstraintViolation):
        await store.register(incoming(source=incoming().source.model_copy(update={"source_sha256": "0" * 64})))
    with pytest.raises(ConstraintViolation):
        await store.register(
            incoming(source=incoming().source.model_copy(update={"quote": "Invented source quotation"}))
        )
    assert not sql(db, "SELECT id FROM belief_encounters")


@pytest.mark.asyncio
async def test_v3_unsupported_external_source_is_visible_ambiguous_not_verified(db):
    external = incoming().source.model_copy(update={"source_type": "web", "source_id": "external-artifact"})
    saved = await BeliefReviewStore(db).register(incoming(source=external))
    assert saved.encounter.source.context_status == "ambiguous"
    assert saved.encounter.source.unavailable_reason
    assert (await BeliefDecisionStore(db).get_state("symbia", saved.record_id)).state == "awaiting_context"


def comparison(db, agent_id="symbia"):
    BeliefRepository(db).create_proposal("comparison", agent_id, STATEMENT, "[]", "", suppress_notification=True)
    return ComparisonSnapshot(
        record_id="comparison",
        agent_id="symbia",
        record_kind="proposal",
        statement=STATEMENT,
        statement_sha256=HASH,
        scope="memory trials",
        temporal_scope="during replay",
    )


def semantic(value):
    return complete(
        value,
        relations=(
            RelationObservation(
                comparison_id="comparison",
                comparison_statement_sha256=HASH,
                relation="contradiction",
                scope="memory trials",
                temporal_scope="during replay",
            ),
        ),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("changed_input", ["source", "comparison"])
async def test_v3_atomic_completion_rechecks_source_and_comparison(db, changed_input):
    store = BeliefReviewStore(db)
    saved = await store.register(incoming())
    pending = assessment(saved, comparison_snapshots=(comparison(db),), referent_status="validated")
    await store.start_assessment(pending)
    if changed_input == "source":
        sql(db, "UPDATE conversation_log SET content='Changed source' WHERE id=42")
    else:
        sql(db, "UPDATE belief_proposals SET provisional_statement='Changed comparison' WHERE id='comparison'")
    result = await store.complete_assessment(semantic(pending))
    assert result.evaluator_status == "stale"
    assert (
        result.relations[0].relation == "insufficient_context" and result.relations[0].raw_relation == "contradiction"
    )
    assert not sql(db, "SELECT id FROM belief_review_decisions")


@pytest.mark.asyncio
async def test_v3_missing_context_cannot_establish_relation_by_evaluator_assertion(db):
    missing = SourceReference(
        source_type="message", context_status="missing", unavailable_reason="Missing source identity"
    )
    store = BeliefReviewStore(db)
    saved = await store.register(incoming(source=missing))
    pending = assessment(saved, comparison_snapshots=(comparison(db),), referent_status="validated")
    await store.start_assessment(pending)
    result = await store.complete_assessment(semantic(pending))
    assert result.evaluator_status == "abstained" and result.referent_status == "missing"
    assert result.relations[0].relation == "insufficient_context"


@pytest.mark.asyncio
async def test_v20_cross_agent_comparison_and_predecessor_links_are_rejected(db):
    store = BeliefReviewStore(db)
    a = await store.register(incoming())
    b = await store.register(incoming(agent_id="other"))
    other = assessment(b)
    await store.start_assessment(other)
    await store.complete_assessment(complete(other))
    with pytest.raises(ResourceNotFound):
        await store.start_assessment(assessment(a, previous_assessment_id=other.id))
    with pytest.raises(ResourceNotFound):
        await store.start_assessment(assessment(a, comparison_snapshots=(comparison(db, agent_id="other"),)))


@pytest.mark.asyncio
async def test_v12_reassessment_must_append_to_current_head(db):
    store = BeliefReviewStore(db)
    saved = await store.register(incoming())
    first = assessment(saved)
    await store.start_assessment(first)
    await store.complete_assessment(complete(first))
    with pytest.raises(ConstraintViolation):
        await store.start_assessment(assessment(saved, id="unlinked", started_at=NOW + timedelta(seconds=2)))
    second = assessment(saved, id="a:second", previous_assessment_id=first.id, started_at=NOW + timedelta(seconds=2))
    await store.start_assessment(second)
    await store.complete_assessment(complete(second, completed_at=NOW + timedelta(seconds=3)))
    with pytest.raises(ConstraintViolation):
        await store.start_assessment(
            assessment(
                saved, id="outdated-head", previous_assessment_id=first.id, started_at=NOW + timedelta(seconds=4)
            )
        )


def test_v21_upgrade_preserves_legacy_bytes_and_does_not_commit_caller_transaction():
    with closing(sqlite3.connect(":memory:")) as conn:
        old_admission_schema(conn)
        conn.execute(
            "INSERT INTO belief_admission (id,event_key,statement_key,status,receipt,created_at) "
            "VALUES ('legacy','legacy-key','key','complete','{legacy bytes}','timestamp')"
        )
        conn.commit()
        conn.execute("BEGIN")
        up(conn)
        assert conn.in_transaction
        assert conn.execute("SELECT receipt,agent_id FROM belief_admission").fetchone() == ("{legacy bytes}", None)
        conn.rollback()
        assert len(conn.execute("PRAGMA table_info(belief_admission)").fetchall()) == 8
        assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='belief_encounters'").fetchone()


@pytest.mark.asyncio
async def test_v2_scope_and_time_partition_identity_but_normalized_repeat_keeps_one_candidate(db):
    store = BeliefReviewStore(db)
    first = await store.register(incoming())
    normalized = " " + STATEMENT + " "
    second = await store.register(
        incoming(
            id="spacing",
            segment_id="tag:spacing",
            statement=normalized,
            statement_sha256=hashlib.sha256(normalized.encode()).hexdigest(),
        )
    )
    scoped = await store.register(incoming(id="scope", segment_id="tag:scope", scope="Other trials"))
    timed = await store.register(incoming(id="time", segment_id="tag:time", temporal_scope="After replay"))
    assert first.record_id == second.record_id
    assert len({r.record_id for r in (first, scoped, timed)}) == 3
    assert sql(db, "SELECT nucleation_mass,confidence FROM belief_proposals WHERE id=?", (first.record_id,))[0][0:] == (
        0.1,
        0.15,
    )


@pytest.mark.asyncio
async def test_v21_explicit_legacy_link_does_not_reclassify_legacy_status(db):
    BeliefRepository(db).create_proposal(
        "legacy", "symbia", STATEMENT, "[]", "", status="adopted", suppress_notification=True
    )
    saved = await BeliefReviewStore(db).register(incoming(candidate_id="legacy"))
    assert saved.record_id == "legacy"
    assert await BeliefDecisionStore(db).get_state("symbia", "legacy") is None
    assert sql(db, "SELECT status FROM belief_proposals WHERE id='legacy'")[0][0] == "adopted"


@pytest.mark.asyncio
async def test_v20_decision_rejects_incomplete_or_other_record_assessment(db):
    intake = BeliefReviewStore(db)
    saved = await intake.register(incoming())
    other = await intake.register(incoming(id="other-claim", segment_id="other-emission", scope="Other trials"))
    first = assessment(saved)
    second = assessment(other, id="assessment:other")
    await intake.start_assessment(first)
    await intake.start_assessment(second)
    await intake.complete_assessment(complete(second))
    for ids in ((first.id,), (second.id,)):
        with pytest.raises(ConstraintViolation):
            await BeliefDecisionStore(db).commit(decision(saved, assessment_ids=ids), authenticated_actor=OPERATOR)
    assert not sql(db, "SELECT id FROM belief_review_decisions")


@pytest.mark.asyncio
async def test_v7_self_comparison_cannot_manufacture_a_receipt(db):
    store = BeliefReviewStore(db)
    saved = await store.register(incoming())
    self_snapshot = ComparisonSnapshot(
        record_id=saved.record_id,
        agent_id="symbia",
        record_kind="proposal",
        statement=STATEMENT,
        statement_sha256=HASH,
        scope="memory trials",
        temporal_scope="during replay",
    )
    with pytest.raises(ConstraintViolation):
        await store.start_assessment(assessment(saved, comparison_snapshots=(self_snapshot,)))
    assert not sql(db, "SELECT id FROM belief_review_assessments")


@pytest.mark.asyncio
async def test_v19_validation_and_sql_share_one_offloaded_use_case(db, monkeypatch):
    import backend.services.belief_review_store as module

    original = module._validated
    caller_thread = threading.get_ident()
    validation_threads = []

    def checked(value):
        validation_threads.append(threading.get_ident())
        return original(value)

    monkeypatch.setattr(module, "_validated", checked)
    intake = BeliefReviewStore(db)
    saved = await intake.register(incoming())
    pending = assessment(saved)
    await intake.start_assessment(pending)
    await intake.complete_assessment(complete(pending))
    await BeliefDecisionStore(db).commit(decision(saved), authenticated_actor=OPERATOR)
    assert len(validation_threads) == 5 and all(t != caller_thread for t in validation_threads)


@pytest.mark.asyncio
async def test_v2_explicit_unknown_record_link_is_not_implicit_claim_grouping(db):
    store = BeliefReviewStore(db)
    saved = await store.register(incoming(scope=""))
    repeated = await store.register(
        incoming(id="explicit", segment_id="another", scope="", candidate_id=saved.record_id)
    )
    assert repeated.record_id == saved.record_id
    assert sql(db, "SELECT claim_key FROM belief_review_claims")[0][0] is None
    with pytest.raises(ConstraintViolation):
        await store.register(incoming(id="conflicting-scope", segment_id="scopechange", candidate_id=saved.record_id))


@pytest.mark.asyncio
async def test_v20_configured_native_key_cannot_enter_statement_snapshot(db, monkeypatch):
    secret = "fake-native-key-for-offline-test"
    monkeypatch.setenv("AAA_NVIDIA_API_KEY", secret)
    statement = "An unsafe claim includes " + secret
    with pytest.raises(ValidationGlitch):
        await BeliefReviewStore(db).register(
            incoming(statement=statement, statement_sha256=hashlib.sha256(statement.encode()).hexdigest())
        )
    assert not sql(db, "SELECT id FROM belief_encounters")
