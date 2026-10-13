"""T11 authenticated workshop oracles against isolated real WAL storage."""

import asyncio
import hashlib
import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.api.deps import get_belief_service
from backend.api.exceptions import register_error_handlers
from backend.api.routes.belief_workshop import router
from backend.api.routes.beliefs import router as legacy_router
from backend.core.sessions import SessionStore
from backend.errors import ConstraintViolation, ResourceNotFound, SecurityViolation
from backend.services.belief_review_contracts import Actor, WorkshopCommand
from backend.services.belief_review_store import BeliefReviewStore
from backend.services.belief_workshop import BeliefWorkshop
from backend.storage.migrations.m067_belief_workshop import up
from backend.storage.migrations.m069_belief_revision_links import up as revision_links_up
from backend.storage.repositories.cognitive.belief import BeliefRepository
from backend.tests.test_belief_review_contracts import HASH, STATEMENT
from backend.tests.test_belief_review_persistence import db as review_db
from backend.tests.test_belief_review_persistence import incoming, sql

OPERATOR = Actor(kind="operator", principal_id="shared-operator", auth_context_id="server:operator-review")


@pytest.fixture
def db(tmp_path):
    return review_db.__wrapped__(tmp_path)


@pytest.fixture
def candidate(db):
    saved = asyncio.run(BeliefReviewStore(db).register(incoming()))
    return saved.record_id


def command(**changes):
    return WorkshopCommand.model_validate(
        dict(
            action="adopt",
            expected_review_version=0,
            expected_statement_sha256=HASH,
            expected_state="candidate",
            scope="memory trials",
            temporal_scope="during replay",
            rationale="Operator chooses this scoped commitment",
            consequence="Change replay selection",
            challenge="A contrary replay requires reconsideration",
        )
        | changes
    )


def execute(db, record, key="first", **changes):
    return asyncio.run(BeliefWorkshop(db).command("symbia", record, key, command(**changes), actor=OPERATOR))


def family(db, record):
    return asyncio.run(BeliefWorkshop(db).family("symbia", record))


def peer(db, **changes):
    statement = "A distinction changes a later replay decision."
    digest = hashlib.sha256(statement.encode()).hexdigest()
    saved = asyncio.run(
        BeliefReviewStore(db).register(
            incoming(
                id="encounter:peer",
                segment_id="tag:peer",
                statement=statement,
                statement_sha256=digest,
                **changes,
            )
        )
    )
    return saved.record_id, digest


def client(db, monkeypatch):
    monkeypatch.setenv("AAA_PASSWORD", "fixture-password")
    app = FastAPI()
    app.state.belief_repo = BeliefRepository(db)
    register_error_handlers(app)
    app.include_router(router, prefix="/api")
    app.include_router(legacy_router, prefix="/api")
    fake = AsyncMock()
    app.dependency_overrides[get_belief_service] = lambda: fake
    return TestClient(app), fake


def url(record):
    return f"/api/beliefs/v2/agents/symbia/records/{record}"


def test_adoption_stable_identity_no_new_warrant(db, candidate, monkeypatch):
    # No model or scorer is required by this command path.
    monkeypatch.setattr(
        "backend.services.belief_proposal._score_statement_16d", AsyncMock(side_effect=AssertionError("scorer"))
    )
    before = BeliefRepository(db).get_proposal(candidate)
    result = execute(db, candidate)
    node = BeliefRepository(db).get_belief("symbia", candidate)
    assert node.id == candidate == node.evolved_from_proposal
    assert node.statement == STATEMENT
    assert node.confidence == before.confidence and node.ontological_mass == before.nucleation_mass
    assert result["decision"]["authority"] == "operator_review"
    assert result["tool_authority"] == "none" and result["shared_agreement"] == "not_inferred"
    assert family(db, candidate)["record"]["state"]["state"] == "adopted"
    assert family(db, candidate)["record"]["statement_sha256"] == HASH
    assert len(sql(db, "SELECT * FROM belief_statement_versions WHERE belief_id=?", (candidate,))) == 1


def test_decline_retained_after_adoption(db, candidate):
    declined = execute(db, candidate, action="decline", dissent=("Scope remains disputed",))
    assert BeliefRepository(db).get_proposal(candidate).status == "pending"
    assert BeliefRepository(db).get_belief("symbia", candidate) is None
    assert declined["counter_trace"]["disposition"] == "retained_scoped_dissent"
    execute(db, candidate, key="adopt-later", expected_state="declined", expected_review_version=1)
    view = family(db, candidate)
    assert view["counter_trace_count"] == 1 and view["counter_traces"][0] == declined["counter_trace"]
    assert len(sql(db, "SELECT * FROM notifications WHERE source='belief_workshop_v2'")) == 2
    with pytest.raises(ConstraintViolation):
        execute(
            db, candidate, key="decline-adopted", action="decline", expected_state="adopted", expected_review_version=2
        )


def test_idempotent_retry_and_changed_input(db, candidate):
    first = execute(db, candidate, action="defer")
    execute(db, candidate, key="later", action="request_review", expected_state="deferred", expected_review_version=1)
    assert execute(db, candidate, action="defer") == first  # Historical receipt, not current state.
    with pytest.raises(ConstraintViolation):
        execute(db, candidate, action="decline")
    with pytest.raises(ConstraintViolation):
        execute(db, candidate, key="fresh-stale")
    assert family(db, candidate)["command_count"] == 2


@pytest.mark.parametrize("same_key", [True, False])
def test_concurrent_commands_single_decision(db, candidate, same_key):
    async def race():
        service = BeliefWorkshop(db)
        return await asyncio.gather(
            *(
                service.command("symbia", candidate, "same" if same_key else f"key:{i}", command(), actor=OPERATOR)
                for i in range(6)
            ),
            return_exceptions=True,
        )

    results = asyncio.run(race())
    assert sum(isinstance(r, dict) for r in results) == (6 if same_key else 1)
    assert all(isinstance(r, (dict, ConstraintViolation)) for r in results)
    assert len(sql(db, "SELECT * FROM belief_review_decisions WHERE record_id=?", (candidate,))) == 1
    assert family(db, candidate)["command_count"] == 1


def test_agent_cannot_adopt_and_declared_positions_not_forged(db, candidate):
    with pytest.raises(SecurityViolation):
        asyncio.run(
            BeliefWorkshop(db).command(
                "symbia", candidate, "bad", command(), actor=Actor(kind="agent", principal_id="symbia")
            )
        )
    with pytest.raises(SecurityViolation):
        execute(
            db,
            candidate,
            positions=(
                {
                    "participant_id": "symbia",
                    "position": "assent",
                    "attribution": "declared",
                    "declaration_source_id": "operator:self",
                    "rationale": "Forged assent",
                },
            ),
        )
    result = execute(
        db,
        candidate,
        positions=(
            {
                "participant_id": "shared-operator",
                "position": "assent",
                "attribution": "declared",
                "declaration_source_id": "operator:self",
                "rationale": "Own declaration",
            },
            {
                "participant_id": "symbia",
                "position": "dissent",
                "attribution": "interpreted",
                "rationale": "Operator interpretation",
            },
        ),
    )
    positions = result["decision"]["positions"]
    assert positions[0]["declaration_source_id"] == result["id"]
    assert positions[1]["attribution"] == "interpreted" and result["shared_agreement"] == "not_inferred"


def test_teachback_is_bounded_artifact_not_eligibility(db, candidate):
    other, digest = peer(db)
    fork = dict(
        alternative_record_id=other,
        expected_alternative_review_version=0,
        expected_alternative_statement_sha256=digest,
        candidate_reconstruction="Decision changes now",
        alternative_reconstruction="Decision changes later",
        scope="memory trials",
        temporal_scope="during replay",
        discriminating_question="Which replay distinguishes the alternatives?",
        unresolved_inquiry="Run a contrary replay",
    )
    result = execute(db, candidate, action="request_review", teachback=fork)
    assert result["alternative_snapshot"]["id"] == other
    assert result["decision"]["next_state"] == "under_review"
    assert BeliefRepository(db).get_belief("symbia", candidate) is None
    assert "eligible" not in json.dumps(result)
    execute(db, candidate, key="adopt", expected_state="under_review", expected_review_version=1)
    with pytest.raises(ValidationError):
        command(teachback=fork | {"tool_command": "adopt"})


def test_scoped_contradiction_preserves_both_records(db, candidate):
    other, digest = peer(db)
    relation = dict(
        record_id=other,
        expected_review_version=0,
        expected_statement_sha256=digest,
        relation="contradiction",
        scope="memory trials",
        temporal_scope="during replay",
        rationale="Different replay consequences",
    )
    result = execute(db, candidate, action="request_review", relations=(relation,))
    assert result["command"]["relations"][0]["relation"] == "contradiction"
    assert BeliefRepository(db).get_proposal(other).status == "pending"
    assert family(db, candidate)["command_relations"].startswith("historical")
    with pytest.raises(ConstraintViolation):
        execute(
            db,
            candidate,
            key="mismatch",
            action="defer",
            expected_state="under_review",
            expected_review_version=1,
            relations=(relation | {"scope": "different conditions"},),
        )


def test_final_peer_source_binding_rechecked(db, candidate, monkeypatch):
    service = BeliefWorkshop(db)
    commit = service.repository.commit

    def changed(*args):
        sql(db, "UPDATE conversation_log SET content='Edited source' WHERE id=42")
        return commit(*args)

    monkeypatch.setattr(service.repository, "commit", changed)
    with pytest.raises(ConstraintViolation):
        asyncio.run(service.command("symbia", candidate, "source-race", command(), actor=OPERATOR))
    assert family(db, candidate)["command_count"] == 0
    assert BeliefRepository(db).get_belief("symbia", candidate) is None


def test_trace_failure_rolls_back_decision_and_materialization(db, candidate):
    sql(
        db,
        "CREATE TRIGGER fail_trace BEFORE INSERT ON notifications WHEN NEW.source='belief_workshop_v2' BEGIN SELECT RAISE(ABORT,'trace failed'); END",
    )
    with pytest.raises(sqlite3.IntegrityError, match="trace failed"):
        execute(db, candidate)
    assert family(db, candidate)["record"]["state"]["state"] == "candidate"
    assert BeliefRepository(db).get_belief("symbia", candidate) is None
    assert BeliefRepository(db).get_proposal(candidate).status == "pending"
    assert not sql(db, "SELECT * FROM belief_review_decisions WHERE record_id=?", (candidate,))


@pytest.mark.parametrize("mutation", ["status", "suggestions", "statement", "delete", "version", "label"])
def test_storage_legacy_bypass_blocked(db, candidate, mutation):
    repo = BeliefRepository(db)
    if mutation in {"statement", "delete", "version", "label"}:
        execute(db, candidate)
    methods = {
        "status": lambda: repo.update_proposal_status(candidate, "rejected"),
        "suggestions": lambda: repo.update_proposal_suggestions(candidate, "changed", "changed"),
        "statement": lambda: repo.update_belief_statement(candidate, "changed", "[]", 2),
        "delete": lambda: repo.delete_belief(candidate),
        "version": lambda: repo.create_statement_version("forged", candidate, 2, "changed", "[]"),
        "label": lambda: repo.delete_belief_by_label(repo.get_belief(candidate).label),
    }
    with pytest.raises(ConstraintViolation):
        methods[mutation]()
    assert BeliefRepository(db).get_proposal(candidate).provisional_statement == STATEMENT


def test_unmanaged_legacy_remains_editable(db):
    repo = BeliefRepository(db)
    repo.create_proposal("old", "symbia", STATEMENT, "old", "[]")
    repo.update_proposal_suggestions("old", "label", "Changed legacy statement")
    assert repo.get_proposal("old").suggested_statement == "Changed legacy statement"
    repo.update_proposal_status("old", "rejected")
    assert repo.get_proposal("old").status == "rejected"


def test_foreign_agent_and_conflicting_alias_rejected(db, candidate):
    with pytest.raises(ResourceNotFound):
        asyncio.run(BeliefWorkshop(db).family("other", candidate))
    # Raw fixture corruption simulates an old conflicting duplicate identity.
    sql(
        db,
        "INSERT INTO belief_nodes(id,agent_id,label,statement,origin,confidence,ontological_mass,somatic_anchor,vector_16d,evolved_from_proposal) VALUES (?,'symbia','bad','Different','emergent',0.1,0.1,'none','[]',?)",
        (candidate, candidate),
    )
    with pytest.raises(ConstraintViolation):
        family(db, candidate)


def test_unsupported_actions_and_immutable_commands(db, candidate):
    with pytest.raises(ConstraintViolation, match="canonical commitment"):
        execute(db, candidate, action="resurface")
    execute(db, candidate, action="defer")
    with pytest.raises(sqlite3.IntegrityError):
        sql(db, "DELETE FROM belief_workshop_commands")
    with pytest.raises(sqlite3.IntegrityError):
        sql(db, "UPDATE belief_workshop_commands SET input_hash='forged'")
    from backend.storage.database import get_connection

    conn = get_connection(db)
    try:
        up(conn)
        up(conn)
        revision_links_up(conn)
        revision_links_up(conn)
        conn.commit()
    finally:
        conn.close()
    assert family(db, candidate)["command_count"] == 1


def test_v31_revision_alias_and_lineage(db, candidate, monkeypatch):
    execute(db, candidate)
    source_before = BeliefRepository(db).get_belief("symbia", candidate)
    revised_statement = "A revised distinction changes a later replay decision."
    revision = execute(
        db,
        candidate,
        key="revise-1",
        action="revise",
        expected_state="adopted",
        expected_review_version=1,
        statement=revised_statement,
    )
    successor = revision["linked_record_id"]
    assert successor and successor != candidate
    assert revision["decision"]["next_state"] == "candidate"
    assert revision["decision"]["record_id"] == successor
    assert BeliefRepository(db).get_belief("symbia", candidate).statement == source_before.statement
    proposal = BeliefRepository(db).get_proposal(successor)
    assert proposal.provisional_statement == revised_statement
    assert proposal.confidence == 0 and proposal.nucleation_mass == 0
    assert BeliefRepository(db).validate_and_format_vector(proposal.initial_signature) == json.dumps([0.0] * 16)
    assert family(db, candidate)["record"]["state"]["state"] == "adopted"
    assert [
        row[0] for row in sql(db, "SELECT action FROM belief_revision_links WHERE source_record_id=?", (candidate,))
    ] == ["revise"]
    assert family(db, successor)["record"]["state"]["state"] == "candidate"
    assert family(db, candidate)["command_count"] == 2
    assert family(db, candidate)["lineage_links"][0]["successor_record_id"] == successor
    assert family(db, successor)["lineage_links"][0]["source_record_id"] == candidate

    # Simulate application rollback/start with migrations disabled on the isolated DB copy.
    from backend.storage.database import init_db

    monkeypatch.setenv("AAA_RUN_MIGRATIONS", "false")
    conn = init_db(db)
    try:
        assert (
            conn.execute(
                "SELECT count(*) FROM belief_revision_links WHERE source_record_id=?", (candidate,)
            ).fetchone()[0]
            == 1
        )
        assert conn.execute("SELECT count(*) FROM belief_nodes WHERE id=?", (candidate,)).fetchone()[0] == 1
    finally:
        conn.close()
    assert family(db, successor)["record"]["state"]["state"] == "candidate"


def test_v16_resurface_preserves_standing_and_adds_no_evidence(db, candidate):
    execute(db, candidate)
    before = BeliefRepository(db).get_belief("symbia", candidate)
    receipt = execute(
        db, candidate, key="resurface", action="resurface", expected_state="adopted", expected_review_version=1
    )
    view = family(db, candidate)
    after = BeliefRepository(db).get_belief("symbia", candidate)
    assert view["record"]["state"]["state"] == "adopted"
    assert view["record"]["state"]["version"] == 2
    assert before.ontological_mass == after.ontological_mass and before.confidence == after.confidence
    assert receipt["decision"]["assessment_ids"] == []
    assert view["command_count"] == 2
    with pytest.raises(ConstraintViolation, match="cannot add assessment"):
        execute(
            db,
            candidate,
            key="resurface-with-assessment",
            action="resurface",
            expected_state="adopted",
            expected_review_version=2,
            assessment_ids=("assessment:invented",),
        )


def test_v16_supersession_requires_adopted_target_and_preserves_both_commitments(db, candidate):
    execute(db, candidate)
    peer_id, peer_hash = peer(db)
    with pytest.raises(ConstraintViolation, match="current adopted commitment"):
        execute(
            db,
            candidate,
            key="premature-supersede",
            action="supersede",
            expected_state="adopted",
            expected_review_version=1,
            target_record_id=peer_id,
            expected_target_review_version=0,
            expected_target_statement_sha256=peer_hash,
        )
    execute(db, peer_id, expected_statement_sha256=peer_hash)
    source_statement = family(db, candidate)["record"]["statement_sha256"]
    target_view = family(db, peer_id)["record"]
    receipt = execute(
        db,
        candidate,
        key="supersede",
        action="supersede",
        expected_state="adopted",
        expected_review_version=1,
        target_record_id=peer_id,
        expected_target_review_version=1,
        expected_target_statement_sha256=target_view["statement_sha256"],
    )
    assert receipt["linked_record_id"] == peer_id
    assert family(db, candidate)["record"]["state"]["state"] == "superseded"
    assert family(db, peer_id)["record"]["state"]["state"] == "adopted"
    assert [
        tuple(row)
        for row in sql(
            db,
            "SELECT action,source_statement_sha256 FROM belief_revision_links WHERE source_record_id=?",
            (candidate,),
        )
    ] == [("supersede", source_statement)]
    decisions = [
        json.loads(row[0])
        for row in sql(
            db,
            "SELECT decision_json FROM belief_review_decisions WHERE agent_id='symbia' AND record_id=? ORDER BY version",
            (candidate,),
        )
    ]
    assert [decision["next_state"] for decision in decisions] == ["adopted", "superseded"]
    assert decisions[0]["id"] != decisions[1]["id"]
    assert BeliefRepository(db).get_belief("symbia", candidate) is not None


def test_v32_duplicate_suggested_label_keeps_adoption_atomic(db, candidate):
    repo = BeliefRepository(db)
    execute(db, candidate)
    second_id, second_hash = peer(db)
    execute(db, second_id, expected_statement_sha256=second_hash)
    beliefs = [repo.get_belief("symbia", item) for item in (candidate, second_id)]
    assert all(belief is not None for belief in beliefs)
    assert len({belief.label for belief in beliefs if belief is not None}) == 2
    assert {belief.id for belief in beliefs if belief is not None} == {candidate, second_id}


def test_api_auth_boundaries_and_server_actor(db, candidate, monkeypatch):
    http, _ = client(db, monkeypatch)
    payload = command().model_dump(mode="json")
    endpoint = url(candidate) + "/decisions"
    assert http.get(url(candidate) + "/review").status_code == 401
    assert http.get(url(candidate) + "/review?token=fixture-password").status_code == 401
    headers = {"Authorization": "Bearer fixture-password", "Idempotency-Key": "api"}
    assert http.post(endpoint, json=payload | {"actor": OPERATOR.model_dump()}, headers=headers).status_code == 422
    assert http.post(endpoint, json=payload, headers={"Authorization": "Bearer fixture-password"}).status_code == 422
    response = http.post(endpoint, json=payload, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["decision"]["actor"] == OPERATOR.model_dump()
    assert "fixture-password" not in response.text
    assert http.post(endpoint, json=payload, headers=headers).json() == response.json()
    monkeypatch.delenv("AAA_PASSWORD")
    assert http.get(url(candidate) + "/review").status_code == 403


@pytest.mark.parametrize("suffix,payload", [("refine", {}), ("vet", {"action": "adopt"})])
def test_legacy_api_provider_not_called(db, candidate, monkeypatch, suffix, payload):
    http, fake = client(db, monkeypatch)
    response = http.post(f"/api/beliefs/proposals/{candidate}/{suffix}", json=payload)
    assert response.status_code == 409, response.text
    assert fake.mock_calls == []


def test_bounded_family_and_historical_decisions(db, candidate):
    # Repeated bookkeeping cannot make the read unbounded or hide the earlier decline.
    execute(db, candidate, action="decline")
    for i in range(1, 52):
        execute(
            db,
            candidate,
            key=f"defer:{i}",
            action="defer",
            expected_state="declined" if i == 1 else "deferred",
            expected_review_version=i,
        )
    view = family(db, candidate)
    assert len(view["commands"]) == 50 and view["history_truncated"]
    assert len(view["counter_traces"]) == 1 and view["counter_trace_count"] == 1
    assert len(view["family"]) <= 10 and view["nomination_only"]


def test_browser_session_origin_csrf_and_password_rotation(db, candidate, monkeypatch):
    http, _ = client(db, monkeypatch)
    sessions = SessionStore()
    monkeypatch.setattr("backend.api.deps.get_session_store", lambda request: sessions)
    http.cookies.set("aaa_session", sessions.issue())
    endpoint = url(candidate) + "/decisions"
    payload = command(action="request_context").model_dump(mode="json")
    assert http.get(url(candidate) + "/review").status_code == 200
    assert http.post(endpoint, json=payload, headers={"Idempotency-Key": "browser"}).status_code == 403
    headers = {"Idempotency-Key": "browser", "Origin": "http://testserver", "x-aaa-csrf": "1"}
    assert http.post(endpoint, json=payload, headers=headers | {"Origin": "https://foreign.test"}).status_code == 403
    assert http.post(endpoint, json=payload, headers=headers).status_code == 200
    monkeypatch.setenv("AAA_PASSWORD", "rotated-password")
    assert http.get(url(candidate) + "/review").status_code == 401


def test_relation_peer_version_race_rolls_back(db, candidate, monkeypatch):
    other, digest = peer(db)
    service = BeliefWorkshop(db)
    commit = service.repository.commit

    def changed(*args):
        execute(db, other, key="peer-review", action="defer", expected_statement_sha256=digest)
        return commit(*args)

    monkeypatch.setattr(service.repository, "commit", changed)
    relation = dict(
        record_id=other,
        expected_review_version=0,
        expected_statement_sha256=digest,
        relation="contradiction",
        scope="memory trials",
        temporal_scope="during replay",
        rationale="Scoped contrast",
    )
    with pytest.raises(ConstraintViolation):
        asyncio.run(service.command("symbia", candidate, "race", command(relations=(relation,)), actor=OPERATOR))
    assert family(db, candidate)["command_count"] == 0


def test_missing_context_cannot_become_equivalence(db, candidate):
    other, digest = peer(db, scope="unknown", temporal_scope="unknown")
    relation = dict(
        record_id=other,
        expected_review_version=0,
        expected_statement_sha256=digest,
        relation="equivalent",
        scope="memory trials",
        temporal_scope="during replay",
        rationale="Same words",
    )
    with pytest.raises(ConstraintViolation):
        execute(db, candidate, action="request_review", relations=(relation,))
    result = execute(
        db, candidate, action="request_context", relations=(relation | {"relation": "insufficient_context"},)
    )
    assert result["decision"]["next_state"] == "awaiting_context"


def test_new_command_does_not_reclassify_legacy_standing(db):
    repo = BeliefRepository(db)
    repo.create_proposal("legacy-review", "symbia", STATEMENT, "old", "[]")
    assert family(db, "legacy-review")["record"]["state"] is None
    result = execute(db, "legacy-review", expected_state=None)
    assert result["decision"]["previous_state"] is None
    assert result["decision"]["next_state"] == "adopted"


def test_payload_secret_and_authority_injection_rejected(db, candidate):
    with pytest.raises(ValidationError):
        command(authority="operator_review")
    with pytest.raises(ValidationError):
        command(relations=tuple({} for _ in range(11)))
    from backend.errors import ValidationGlitch

    with pytest.raises(ValidationGlitch):
        execute(db, candidate, rationale="authorization: Bearer secret-test-token")
    assert family(db, candidate)["command_count"] == 0


def test_legacy_merge_without_statement_cannot_inflate_managed_target(db, candidate):
    from backend.services.belief import BeliefService

    repo = BeliefRepository(db)
    repo.create_proposal("legacy-merge", "symbia", "A separate proposal", "old", "[]")
    execute(db, candidate)
    before = repo.get_belief(candidate)
    service = BeliefService(SimpleNamespace(belief_repo=repo, notification_repo=None))
    with pytest.raises(ConstraintViolation):
        asyncio.run(service.merge_proposal("legacy-merge", candidate))
    after = repo.get_belief(candidate)
    assert (after.confidence, after.ontological_mass) == (before.confidence, before.ontological_mass)
    assert repo.get_proposal("legacy-merge").status == "pending"


def test_legacy_merge_target_managed_during_provider_await_is_rechecked(db, monkeypatch):
    from backend.services.belief import BeliefService

    repo = BeliefRepository(db)
    repo.create_belief("legacy-target", "symbia", "legacy", STATEMENT, "emergent", 0.2, 0.2, "none", "[]")
    repo.create_proposal("legacy-source", "symbia", "Separate proposal", "old", "[]")

    async def scorer(*args, **kwargs):
        await BeliefWorkshop(db).command(
            "symbia", "legacy-target", "became-managed", command(expected_state=None), actor=OPERATOR
        )
        return "[]"

    monkeypatch.setattr("backend.services.belief_proposal._score_statement_16d", scorer)
    service = BeliefService(SimpleNamespace(belief_repo=repo, notification_repo=None))
    with pytest.raises(ConstraintViolation):
        asyncio.run(service.merge_proposal("legacy-source", "legacy-target", "Changed merged statement"))
    assert repo.get_proposal("legacy-source").status == "pending"
    node = repo.get_belief("legacy-target")
    assert node.statement == STATEMENT and node.confidence == node.ontological_mass == 0.2
