"""T10 deterministic support/activity/recurrence and forward-only accounting oracles."""

import asyncio
import sqlite3
from datetime import timedelta
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from backend.errors import ResourceNotFound, ValidationGlitch
from backend.modules.sensory.belief_lineage import observation
from backend.services.belief_lineage import BeliefLineageStore
from backend.services.belief_review_contracts import LineageEntry, SourceAccountingEvent
from backend.services.belief_review_store import BeliefReviewStore
from backend.storage.migrations.m066_belief_source_accounting import up
from backend.storage.repositories.cognitive.belief_explicit import ExplicitBeliefRepository
from backend.storage.repositories.cognitive.belief_lineage import BeliefLineageRepository
from backend.tests.test_belief_admission import admission_db as admission_db
from backend.tests.test_belief_assessment import emit
from backend.tests.test_belief_review_contracts import HASH, NOW
from backend.tests.test_belief_review_persistence import db as db
from backend.tests.test_belief_review_persistence import incoming, sql


@pytest.mark.asyncio
async def test_v7_v16_retry_and_internal_recurrence_are_not_support(db):
    store = BeliefReviewStore(db)
    value = incoming(lineage=(LineageEntry(source_id="42", source_sha256=HASH, independence_status="internal"),))
    first = await store.register(value)
    before = sql(db, "SELECT nucleation_mass,confidence,status FROM belief_proposals WHERE id=?", (first.record_id,))
    await asyncio.gather(*(store.register(value) for _ in range(6)))
    reader = BeliefLineageStore(db)
    summary = await reader.summary("symbia", first.record_id)
    assert summary.observed_encounters == summary.internal_activity == 1
    assert summary.recurrence == summary.verified_independent_groups == 0
    second = await store.register(
        incoming(id="second", segment_id="other", received_at=NOW + timedelta(seconds=1), lineage=value.lineage)
    )
    assert second.record_id == first.record_id
    summary = await reader.summary("symbia", first.record_id)
    assert summary.observed_encounters == summary.internal_activity == 2
    assert summary.recurrence == 1 and summary.verified_independent_groups == 0
    assert (
        sql(db, "SELECT nucleation_mass,confidence,status FROM belief_proposals WHERE id=?", (first.record_id,))
        == before
    )
    assert sql(db, "SELECT count(*) FROM belief_review_decisions")[0][0] == 0
    assert summary.observations[0].source_group_keys == summary.observations[1].source_group_keys


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["unknown", "derived", "independent"])
async def test_v7_v8_declared_lineage_and_artistic_labels_do_not_verify_warrant(db, status):
    saved = await BeliefReviewStore(db).register(
        incoming(lineage=(LineageEntry(source_id="42", source_sha256=HASH, independence_status=status),))
    )
    receipt = await BeliefLineageStore(db).observation("symbia", saved.encounter.id)
    assert receipt.verified_independent_groups == 0
    assert receipt.independent_warrant == "unverified"
    assert not receipt.internal_activity
    if status == "independent":
        assert "declared_independence_not_verified" in receipt.uncertainty
    assert receipt.lineage[0].independence_status == status


def test_v7_shared_parent_identity_grouping_and_cycles_are_bounded():
    left = incoming(
        lineage=(LineageEntry(source_id="42", parent_sources=("upstream",), independence_status="derived"),)
    )
    right = incoming(
        id="another",
        source=left.source.model_copy(update={"source_id": "43"}),
        lineage=(LineageEntry(source_id="43", parent_sources=("upstream",), independence_status="derived"),),
    )
    a, b = observation(left.model_dump(mode="json")), observation(right.model_dump(mode="json"))
    assert a["source_group_keys"] == b["source_group_keys"]
    cycle = incoming(
        lineage=(
            LineageEntry(source_id="42", parent_sources=("43",)),
            LineageEntry(source_id="43", parent_sources=("42",)),
        )
    )
    result = observation(cycle.model_dump(mode="json"))
    assert not result["grouping_complete"] and "cyclic_ancestry" in result["uncertainty"]
    excessive = incoming(
        lineage=tuple(
            LineageEntry(source_id=str(i), parent_sources=tuple(str(j) for j in range(50))) for i in range(50)
        )
    )
    result = observation(excessive.model_dump(mode="json"))
    assert not result["grouping_complete"] and "ancestry_graph_exceeds_bound" in result["uncertainty"]


@pytest.mark.asyncio
async def test_v17_forward_events_are_typed_and_do_not_reinterpret_legacy(db):
    existing = sql(db, "SELECT id FROM belief_nodes LIMIT 1")[0][0]
    sql(
        db, "INSERT INTO belief_events(id,belief_id,event_type,impact_score) VALUES ('old',?,'legacy',0.7)", (existing,)
    )
    before = sql(db, "SELECT * FROM belief_events WHERE id='old'")
    store = BeliefReviewStore(db)
    saved = await store.register(incoming(lineage=(LineageEntry(source_id="42", independence_status="internal"),)))
    await store.register(
        incoming(id="next", segment_id="next", lineage=(LineageEntry(source_id="42", independence_status="internal"),))
    )
    events = await BeliefLineageStore(db).events("symbia", saved.record_id)
    assert len(events) == 5
    assert {event.impact_quantity for event in events} == {"source_lineage", "internal_activity", "recurrence"}
    assert all(event.impact_unit == "encounter_observation" and event.impact_value == 1 for event in events)
    assert all(event.delta_mass == event.confidence_delta == 0 for event in events)
    assert all(event.timestamp == NOW and event.encounter_id in {"encounter", "next"} for event in events)
    assert sql(db, "SELECT * FROM belief_events WHERE id='old'") == before
    with pytest.raises(ValidationError):
        SourceAccountingEvent.model_validate(events[0].model_dump() | {"confidence_delta": 0.5})


@pytest.mark.asyncio
async def test_v2_v19_accounting_failure_rolls_back_whole_encounter(db):
    with (
        patch.object(BeliefLineageRepository, "append", side_effect=RuntimeError("fixture persistence failure")),
        pytest.raises(RuntimeError),
    ):
        await BeliefReviewStore(db).register(incoming())
    assert sql(db, "SELECT count(*) FROM belief_encounters")[0][0] == 0
    assert sql(db, "SELECT count(*) FROM belief_source_observations")[0][0] == 0
    assert sql(db, "SELECT count(*) FROM belief_proposals WHERE id LIKE 'candidate:%'")[0][0] == 0


@pytest.mark.asyncio
async def test_v20_agent_isolation_and_secret_boundary(db, monkeypatch):
    saved = await BeliefReviewStore(db).register(incoming())
    reader = BeliefLineageStore(db)
    with pytest.raises(ResourceNotFound):
        await reader.observation("other", saved.encounter.id)
    with pytest.raises(ResourceNotFound):
        await reader.summary("other", saved.record_id)
    with pytest.raises(ResourceNotFound):
        await reader.events("other", saved.record_id)
    monkeypatch.setenv("AAA_PASSWORD", "fixture-secret-accounting")
    unsafe = incoming(id="unsafe", lineage=(LineageEntry(source_id="fixture-secret-accounting"),))
    with pytest.raises(ValidationGlitch):
        await BeliefReviewStore(db).register(unsafe)
    assert sql(db, "SELECT count(*) FROM belief_source_observations")[0][0] == 1


@pytest.mark.asyncio
async def test_v21_migration_and_old_retry_never_backfill_support(db):
    # Emulate an encounter committed before migration 066 by suppressing only its new append hook.
    with patch.object(BeliefLineageRepository, "append", return_value=None):
        saved = await BeliefReviewStore(db).register(incoming())
    with sqlite3.connect(db) as conn:
        before = conn.execute("SELECT encounter_json FROM belief_encounters").fetchall()
        conn.execute("DROP TABLE belief_review_events")
        conn.execute("DROP TABLE belief_source_observations")
        up(conn)
        up(conn)
        assert conn.execute("SELECT encounter_json FROM belief_encounters").fetchall() == before
    await BeliefReviewStore(db).register(incoming())
    reader = BeliefLineageStore(db)
    assert await reader.observation("symbia", saved.encounter.id) is None
    summary = await reader.summary("symbia", saved.record_id)
    assert summary.historical_unrecorded_encounters == 1 and summary.observed_encounters == 0
    new = await BeliefReviewStore(db).register(incoming(id="new", segment_id="new"))
    summary = await reader.summary("symbia", new.record_id)
    assert summary.historical_unrecorded_encounters == 1 and summary.observed_encounters == 1
    assert summary.recurrence == 0  # Recorded recurrence begins at the ledger coverage boundary.


@pytest.mark.asyncio
async def test_v12_v19_immutable_observations_events_and_bounded_reads(db):
    store = BeliefReviewStore(db)
    saved = await store.register(incoming())
    for i in range(52):
        await store.register(incoming(id=f"e:{i}", segment_id=f"occurrence:{i}"))
    summary = await BeliefLineageStore(db).summary("symbia", saved.record_id, 500)
    assert summary.observed_encounters == 53 and len(summary.observations) == 50 and summary.truncated
    assert len(await BeliefLineageStore(db).events("symbia", saved.record_id, 500)) == 50
    with pytest.raises(sqlite3.IntegrityError):
        sql(db, "UPDATE belief_source_observations SET recurrence=1")
    with pytest.raises(sqlite3.IntegrityError):
        sql(db, "DELETE FROM belief_review_events")


@pytest.mark.asyncio
async def test_v13_explicit_page_history_and_traces_share_accounting(admission_db):
    receipt, _ = await emit(admission_db)
    path = admission_db[0]
    native = await BeliefLineageStore(path).observation("symbia", receipt["encounter_id"])
    assert receipt["source_accounting"]["encounter_id"] == native.encounter_id
    assert receipt["source_accounting"]["internal_activity"]
    history = ExplicitBeliefRepository(path).history(receipt["proposal_id"])
    assert history[0]["source_accounting"] == receipt["source_accounting"]
    traces = sql(path, "SELECT snippet FROM notifications WHERE type='trace' AND id LIKE ?", (receipt["id"] + ":%",))
    assert len(traces) == 2
    assert all("source_accounting" in row[0] and native.encounter_id in row[0] for row in traces)


@pytest.mark.asyncio
async def test_v3_v7_scopes_and_unknown_sources_do_not_manufacture_recurrence(db):
    store = BeliefReviewStore(db)
    one = await store.register(incoming())
    two = await store.register(incoming(id="different-scope", segment_id="different", scope="Other trials"))
    reader = BeliefLineageStore(db)
    assert one.record_id != two.record_id
    assert (await reader.summary("symbia", one.record_id)).recurrence == 0
    assert (await reader.summary("symbia", two.record_id)).recurrence == 0
    unavailable = incoming(
        id="missing",
        segment_id="missing",
        scope="",
        temporal_scope="",
        source=incoming().source.model_copy(update={"context_status": "missing", "unavailable_reason": "Unavailable"}),
    )
    three = await store.register(unavailable)
    receipt = await reader.observation("symbia", three.encounter.id)
    assert receipt.verified_independent_groups == 0
    assert "source_context_missing" in receipt.uncertainty
    assert "upstream_independence_unknown" in receipt.uncertainty


@pytest.mark.asyncio
async def test_v7_v8_reassessment_does_not_add_source_activity_or_support(admission_db):
    from backend.modules.sensory.evidence_triage import EvidenceTriage
    from backend.services.belief_assessment import assess_encounter
    from backend.tests.test_belief_assessment import CONFIG, Client

    receipt, _ = await emit(admission_db)
    path = admission_db[0]
    reader = BeliefLineageStore(path)
    before = await reader.summary("symbia", receipt["proposal_id"])
    await assess_encounter(
        path, "symbia", receipt["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(Client(factual="supported"))
    )
    after = await reader.summary("symbia", receipt["proposal_id"])
    assert after == before
    assert after.verified_independent_groups == 0
    assert len(await reader.events("symbia", receipt["proposal_id"])) == 2


@pytest.mark.asyncio
async def test_v17_event_contract_rejects_unknown_quantity_or_invented_delta(db):
    saved = await BeliefReviewStore(db).register(incoming())
    event = (await BeliefLineageStore(db).events("symbia", saved.record_id))[0]
    for change in (
        {"impact_quantity": "recurrence"},
        {"impact_value": True},
        {"delta_mass": 1.0},
        {"confidence_delta": float("nan")},
    ):
        with pytest.raises(ValidationError):
            SourceAccountingEvent.model_validate(event.model_dump() | change)
