"""T12 snapshot, reasoning, ownership and secret oracles against isolated WAL storage."""

import asyncio
from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.exceptions import register_error_handlers
from backend.api.routes.belief_export import router
from backend.errors import ConstraintViolation, ResourceNotFound, ValidationGlitch
from backend.services.belief_export import BeliefExport
from backend.services.belief_review_store import BeliefDecisionStore, BeliefReviewStore
from backend.storage.database import get_connection
from backend.storage.migrations.m068_belief_export_order import up
from backend.storage.repositories.cognitive.belief import BeliefRepository
from backend.tests.test_belief_review_contracts import NOW, STATEMENT
from backend.tests.test_belief_review_persistence import OPERATOR, assessment, complete, decision, incoming, sql
from backend.tests.test_belief_review_persistence import db as review_db


@pytest.fixture
def db(tmp_path):
    return review_db.__wrapped__(tmp_path)


def register(db, identity="encounter:1", **changes):
    return asyncio.run(BeliefReviewStore(db).register(incoming(id=identity, segment_id=identity, **changes)))


def page(db, resource="encounters", **changes):
    values = dict(
        agent="symbia", resource=resource, start=NOW - timedelta(days=1), end=NOW + timedelta(days=1), limit=25
    )
    return asyncio.run(BeliefExport(db, "fixture-password").page(**(values | changes)))


def legacy(db, identity="legacy:1", timestamp=None, **changes):
    repo = BeliefRepository(db)
    if not repo.get_belief("legacy-record"):
        repo.create_belief("legacy-record", "symbia", "legacy", STATEMENT, "emergent", 0.2, 0.2, "none", "[]")
    sql(
        db,
        "INSERT INTO belief_events(id,belief_id,timestamp,event_type,impact_score,rationale) VALUES (?,?,?,?,?,?)",
        (
            identity,
            "legacy-record",
            timestamp or NOW.isoformat(),
            "perturbation",
            0.3,
            changes.get("rationale", "Legacy reason"),
        ),
    )


def test_tied_timestamps_keysets_restart_and_backdated_insert(db):
    for identity in ("encounter:c", "encounter:a", "encounter:b"):
        register(db, identity)
    first = page(db, limit=1)
    assert not first["interval_complete"]
    register(db, "encounter:backdated", received_at=NOW - timedelta(hours=1))
    ids = [first["items"][0]["id"]]
    cursor = first["next_cursor"]
    while cursor:
        result = page(db, limit=1, cursor=cursor)  # New service instance, same persisted DB and auth key.
        ids.extend(item["id"] for item in result["items"])
        cursor = result["next_cursor"]
    assert ids == ["encounter:a", "encounter:b", "encounter:c"]
    assert result["interval_complete"]
    assert len(page(db)["items"]) == 4


@pytest.mark.parametrize(
    "change",
    [dict(agent="other"), dict(resource="events"), dict(limit=2), dict(start=NOW), dict(end=NOW + timedelta(days=2))],
)
def test_cursor_bound_to_every_request_dimension(db, change):
    register(db)
    register(db, "encounter:2")
    cursor = page(db, limit=1)["next_cursor"]
    with pytest.raises(ValidationGlitch):
        page(db, **(dict(limit=1, cursor=cursor) | change))


def test_cursor_tamper_and_password_rotation(db):
    register(db)
    register(db, "encounter:2")
    cursor = page(db, limit=1)["next_cursor"]
    with pytest.raises(ValidationGlitch):
        page(db, limit=1, cursor="x" + cursor[1:])
    with pytest.raises(ValidationGlitch):
        asyncio.run(
            BeliefExport(db, "rotated-password").page(
                "symbia", "encounters", NOW - timedelta(days=1), NOW + timedelta(days=1), 1, cursor
            )
        )


def test_half_open_microsecond_interval_and_offset_normalization(db):
    register(db, "encounter:before", received_at=NOW - timedelta(microseconds=1))
    register(db, "encounter:at")
    register(db, "encounter:after", received_at=NOW + timedelta(microseconds=1))
    result = page(db, start=NOW, end=NOW + timedelta(microseconds=1))
    assert [item["id"] for item in result["items"]] == ["encounter:at"]
    from datetime import timezone

    equivalent = page(db, start=NOW.astimezone(timezone(timedelta(hours=8))), end=NOW + timedelta(microseconds=1))
    assert result == equivalent


def test_completion_sequence_excludes_assessment_finishing_between_pages(db):
    saved = register(db)
    store = BeliefReviewStore(db)
    first = assessment(saved)
    asyncio.run(store.start_assessment(first))
    asyncio.run(store.complete_assessment(complete(first)))
    second = assessment(
        saved, id="assessment:2", previous_assessment_id=first.id, started_at=NOW + timedelta(seconds=2)
    )
    asyncio.run(store.start_assessment(second))
    asyncio.run(store.complete_assessment(complete(second, completed_at=NOW + timedelta(seconds=3))))
    pending = assessment(
        saved, id="assessment:3", previous_assessment_id=second.id, started_at=NOW + timedelta(seconds=4)
    )
    asyncio.run(store.start_assessment(pending))
    initial = page(db, "assessments", limit=1)
    asyncio.run(store.complete_assessment(complete(pending, completed_at=NOW + timedelta(seconds=5))))
    final = page(db, "assessments", limit=1, cursor=initial["next_cursor"])
    assert [item["id"] for item in initial["items"] + final["items"]] == [first.id, second.id]
    assert final["interval_complete"]
    assert len(page(db, "assessments")["items"]) == 3


def test_native_event_and_legacy_quantity_reasoning_are_distinct(db):
    register(db)
    legacy(db)
    result = page(db, "events")
    native = next(item for item in result["items"] if item["kind"] == "event")
    historical = next(item for item in result["items"] if item["kind"] == "legacy_event")
    assert native["record"]["impact_unit"] == "encounter_observation"
    assert native["record"]["confidence_delta"] == 0
    assert native["reasoning"]["encounter"]["id"] == "encounter:1"
    observed = native["source_accounting"]["observations"][0]
    assert observed["encounter_id"] == "encounter:1"
    assert observed["verified_independent_groups"] == 0
    assert observed["independent_warrant"] == "unverified"
    assert historical["source_accounting"] is None
    assert historical["record"]["confidence_delta"] is None
    assert historical["record"]["delta_confidence"] == 0.3
    assert historical["record"]["impact_value"] == 0.3
    assert len(historical["unknown_reasoning_fields"]) == 5
    assert all(item["tool_authority"] == "none" for item in result["items"])


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE belief_events SET rationale='changed' WHERE id='legacy:1'",
        "DELETE FROM belief_events WHERE id='legacy:1'",
        "UPDATE belief_nodes SET agent_id='other' WHERE id='legacy-record'",
    ],
)
def test_legacy_history_mutation_invalidates_snapshot(db, mutation):
    legacy(db)
    legacy(db, "legacy:2")
    first = page(db, "events", limit=1)
    sql(db, mutation)
    with pytest.raises(ConstraintViolation):
        page(db, "events", limit=1, cursor=first["next_cursor"])


def test_later_backdated_legacy_event_excluded(db):
    legacy(db)
    legacy(db, "legacy:2")
    initial = page(db, "events", limit=1)
    legacy(db, "legacy:later", timestamp=(NOW - timedelta(seconds=1)).isoformat())
    final = page(db, "events", limit=1, cursor=initial["next_cursor"])
    assert final["items"][0]["id"] == "legacy:2"
    assert final["next_cursor"] is None


def test_reasoning_receipt_and_operator_attribution(db):
    saved = register(db)
    review = decision(saved)
    asyncio.run(BeliefDecisionStore(db).commit(review, authenticated_actor=OPERATOR))
    item = page(db, "decisions")["items"][0]
    assert set(item["reasoning"]) == {
        "encounter",
        "claim_or_tension",
        "comparison",
        "consequence_or_challenge",
        "decision_or_uncertainty",
    }
    assert item["reasoning"]["decision_or_uncertainty"]["actor"] == review.actor.model_dump(mode="json")
    assert item["reasoning"]["decision_or_uncertainty"]["dissent"] == list(review.dissent)
    assert item["reasoning_sources"][0]["id"] == review.id
    assert item["reasoning_sources"][0]["timestamp"] == item["timestamp"]
    assert item["reasoning"]["encounter"] is None  # No fabricated encounter selected for unlinked decision.


def test_pending_detail_and_cross_agent_isolation(db):
    saved = register(db)
    pending = assessment(saved)
    asyncio.run(BeliefReviewStore(db).start_assessment(pending))
    service = BeliefExport(db, "fixture-password")
    detail = asyncio.run(service.detail("symbia", "assessments", pending.id))
    assert detail["record"]["evaluator_status"] == "pending"
    assert page(db, "assessments")["items"] == []
    with pytest.raises(ResourceNotFound):
        asyncio.run(service.detail("other", "encounters", saved.encounter.id))
    assert page(db, agent="other")["items"] == []


def test_missing_legacy_timestamp_is_explicit_incomplete_coverage(db):
    legacy(db, timestamp="invalid")
    result = page(db, "events")
    assert result["undated_rows"] == 1
    assert not result["interval_complete"]
    assert result["next_cursor"] is None


@pytest.mark.parametrize("padding", ["", " "])
def test_legacy_secret_projection_does_not_rewrite_history(db, monkeypatch, padding):
    monkeypatch.setenv("AAA_PASSWORD", padding + "fixture-password" + padding)
    monkeypatch.setenv("FIXTURE_API_KEY", padding + "sensitive-fixture-token" + padding)
    secret = "sensitive-fixture-token fixture-password"
    legacy(db, rationale=secret)
    item = page(db, "events")["items"][0]
    assert "sensitive-fixture-token" not in str(item)
    assert "fixture-password" not in str(item)
    assert item["content_redacted"]
    conn = get_connection(db)
    try:
        assert conn.execute("SELECT rationale FROM belief_events").fetchone()[0] == secret
    finally:
        conn.close()


def test_migration_repeat_preserves_receipts_and_order(db):
    saved = register(db)
    value = assessment(saved)
    store = BeliefReviewStore(db)
    asyncio.run(store.start_assessment(value))
    asyncio.run(store.complete_assessment(complete(value)))
    before = page(db, "assessments")
    conn = get_connection(db)
    try:
        with conn:
            up(conn)
            up(conn)
    finally:
        conn.close()
    assert before == page(db, "assessments")


def api(db, monkeypatch):
    monkeypatch.setenv("AAA_PASSWORD", "fixture-password")
    app = FastAPI()
    app.state.belief_repo = BeliefRepository(db)
    register_error_handlers(app)
    app.include_router(router, prefix="/api")
    return TestClient(app)


def test_api_auth_queries_detail_and_secret_free_glitches(db, monkeypatch):
    register(db)
    client = api(db, monkeypatch)
    url = "/api/beliefs/v2/agents/symbia/encounters"
    query = {"from": (NOW - timedelta(days=1)).isoformat(), "to": (NOW + timedelta(days=1)).isoformat()}
    headers = {"Authorization": "Bearer fixture-password"}
    assert client.get(url, params=query).status_code == 401
    assert client.get(url, params=query | {"password": "fixture-password"}).status_code == 401
    response = client.get(url, params=query, headers=headers)
    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == "encounter:1"
    for change in ({"limit": 0}, {"limit": 51}, {"cursor": "x" * 2049}, {"from": "bad"}):
        assert client.get(url, params=query | change, headers=headers).status_code == 422
    for change in ({"from": NOW.replace(tzinfo=None).isoformat()}, {"to": query["from"]}, {"cursor": "bad"}):
        failure = client.get(url, params=query | change, headers=headers)
        assert failure.status_code == 400
        assert "fixture-password" not in failure.text
    assert client.get(url, params=query | {"actor": "operator"}, headers=headers).status_code == 400
    assert client.get(url + "/encounter:1", headers=headers).status_code == 200
    assert client.get(url.replace("symbia", "other") + "/encounter:1", headers=headers).status_code == 404
    monkeypatch.delenv("AAA_PASSWORD")
    assert client.get(url, params=query).status_code == 403


def test_export_read_budget_failure_is_visible_and_connection_recovers(db, monkeypatch):
    legacy(db)
    sql(
        db,
        "WITH RECURSIVE rows(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM rows WHERE n<200) "
        "INSERT INTO belief_events(id,belief_id,timestamp) SELECT 'budget:'||n,'legacy-record',? FROM rows",
        (NOW.isoformat(),),
    )
    monkeypatch.setattr("backend.storage.repositories.cognitive.belief_export.READ_SECONDS", -1)
    from backend.errors import GlitchError

    with pytest.raises(GlitchError) as failure:
        page(db, "events")
    assert failure.value.status_code == 503
    monkeypatch.setattr("backend.storage.repositories.cognitive.belief_export.READ_SECONDS", 3)
    assert page(db, "events")["items"]


def test_oversized_receipt_failure_does_not_claim_complete(db, monkeypatch):
    register(db)
    monkeypatch.setattr("backend.storage.repositories.cognitive.belief_export.MAX_RECEIPT_BYTES", 100)
    from backend.errors import GlitchError

    with pytest.raises(GlitchError) as failure:
        page(db)
    assert failure.value.status_code == 503


def test_existing_completed_receipts_get_only_bootstrap_index(db):
    saved = register(db)
    store = BeliefReviewStore(db)
    value = assessment(saved)
    asyncio.run(store.start_assessment(value))
    asyncio.run(store.complete_assessment(complete(value)))
    before = page(db, "assessments")["items"][0]["record"]
    conn = get_connection(db)
    try:
        with conn:
            conn.execute("DROP TABLE belief_assessment_completions")
            up(conn)
    finally:
        conn.close()
    after = page(db, "assessments")["items"][0]
    assert before == after["record"]
    assert after["completion_index_origin"] == "existing_receipt"


def test_completion_index_failure_rolls_back_assessment(db):
    saved = register(db)
    store = BeliefReviewStore(db)
    value = assessment(saved)
    asyncio.run(store.start_assessment(value))
    sql(
        db,
        "CREATE TRIGGER deny_export_index BEFORE INSERT ON belief_assessment_completions "
        "BEGIN SELECT RAISE(ABORT,'fixture index failure'); END",
    )
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        asyncio.run(store.complete_assessment(complete(value)))
    assert page(db, "assessments")["items"] == []
    assert (
        asyncio.run(BeliefExport(db, "fixture-password").detail("symbia", "assessments", value.id))["record"][
            "evaluator_status"
        ]
        == "pending"
    )


def test_linked_decision_projects_actual_encounter_comparison_and_receipt_ids(db):
    saved = register(db)
    store = BeliefReviewStore(db)
    value = assessment(saved)
    asyncio.run(store.start_assessment(value))
    asyncio.run(store.complete_assessment(complete(value)))
    review = decision(saved, assessment_ids=(value.id,))
    asyncio.run(BeliefDecisionStore(db).commit(review, authenticated_actor=OPERATOR))
    item = page(db, "decisions")["items"][0]
    assert item["reasoning"]["encounter"]["linked_encounters"][0]["id"] == saved.encounter.id
    assert item["reasoning"]["comparison"][0]["id"] == value.id
    assert [source["id"] for source in item["reasoning_sources"]] == [review.id, value.id]
    assert item["reasoning"]["claim_or_tension"]["statement_sha256"] == review.statement_sha256


def test_api_browser_session(db, monkeypatch):
    from backend.core.sessions import SessionStore

    register(db)
    client = api(db, monkeypatch)
    sessions = SessionStore(db_path=db)
    monkeypatch.setattr("backend.api.deps.get_session_store", lambda request: sessions)
    client.cookies.set("aaa_session", sessions.issue())
    url = "/api/beliefs/v2/agents/symbia/encounters"
    query = {"from": (NOW - timedelta(days=1)).isoformat(), "to": (NOW + timedelta(days=1)).isoformat()}
    assert client.get(url, params=query, headers={"Origin": "http://testserver"}).status_code == 200
    assert client.get(url, params=query, headers={"Origin": "https://untrusted.example"}).status_code == 403


def test_aggregate_projection_budget_is_visible(db, monkeypatch):
    from backend.errors import GlitchError

    register(db)
    monkeypatch.setattr("backend.services.belief_export.PAGE_SECONDS", -1)
    with pytest.raises(GlitchError) as failure:
        page(db)
    assert failure.value.status_code == 503
