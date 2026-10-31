import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from backend.api.deps import get_belief_repo, get_belief_service, verify_password
from backend.api.routes.beliefs import router
from backend.services.belief_query import BeliefQueryUseCases
from backend.storage.models import BeliefNode


@pytest.mark.asyncio
async def test_belief_reads_leave_event_loop_free():
    loop_thread = threading.get_ident()

    class Repository:
        def list_beliefs(self, agent):
            assert threading.get_ident() != loop_thread
            return []

        def list_proposals(self, agent):
            assert threading.get_ident() != loop_thread
            return []

    query = BeliefQueryUseCases()
    query._state = SimpleNamespace(belief_repo=Repository())
    result = await asyncio.wait_for(query.get_beliefs(), timeout=2)
    assert result["beliefs"] == []
    assert result["proto_beliefs"] == []


@pytest.mark.asyncio
async def test_timeseries_reads_run_in_worker():
    loop_thread = threading.get_ident()

    class Repository:
        def get_belief(self, agent, belief):
            assert threading.get_ident() != loop_thread
            return None

    query = BeliefQueryUseCases()
    query._state = SimpleNamespace(belief_repo=Repository())
    assert (await query.get_belief_timeseries("missing"))["status"] == "error"


@pytest.mark.asyncio
async def test_ecosystem_computation_runs_in_worker(monkeypatch):
    from backend.modules.belief.ecosystem import EcosystemManager
    from backend.modules.belief_engine import BeliefDynamicsEngine

    loop_thread = threading.get_ident()

    def compute(repo, **kwargs):
        assert threading.get_ident() != loop_thread
        return {"active_count": 3}, 0.06

    monkeypatch.setattr(EcosystemManager, "compute_ecosystem_health", compute)
    engine = BeliefDynamicsEngine.__new__(BeliefDynamicsEngine)
    engine._belief_repo = None
    engine._source_weights = {}
    engine._beta = 0.05
    assert await engine.compute_ecosystem_health() == {"active_count": 3}
    assert engine._beta == 0.06


@pytest.mark.asyncio
async def test_health_does_not_load_histories_or_proposals():
    repository = Mock()
    engine = SimpleNamespace(compute_ecosystem_health=AsyncMock(return_value={"active_count": 3}))
    query = BeliefQueryUseCases()
    query._state = SimpleNamespace(belief_repo=repository, belief_metabolism=engine)
    assert await query.get_health("agent") == {"somatic": None, "ecosystem": {"active_count": 3}}
    assert repository.mock_calls == []
    engine.compute_ecosystem_health.assert_awaited_once_with("agent")


def test_health_route_validates_agent_and_requires_auth(monkeypatch):
    app = FastAPI()
    app.include_router(router, prefix="/api", dependencies=[Depends(verify_password)])
    service = SimpleNamespace(get_health=AsyncMock(return_value={"somatic": None, "ecosystem": None}))
    app.dependency_overrides[get_belief_service] = lambda: service
    client = TestClient(app)
    monkeypatch.setenv("AAA_PASSWORD", "fixture-password")
    assert client.get("/api/beliefs/health").status_code == 401
    monkeypatch.setenv("AAA_PASSWORD", "")
    assert client.get("/api/beliefs/health?agent_id=../bad").status_code == 422
    response = client.get("/api/beliefs/health?agent_id=other-agent")
    assert response.status_code == 200
    assert response.json() == {"somatic": None, "ecosystem": None}
    service.get_health.assert_awaited_once_with(agent_id="other-agent")


@pytest.mark.asyncio
async def test_skill_listing_runs_in_worker():
    from backend.services.skill import SkillService

    loop_thread = threading.get_ident()

    class Repository:
        def list_always_active(self):
            assert threading.get_ident() != loop_thread
            return []

        list_on_demand = list_always_active
        list_skills = list_always_active

    service = SkillService(SimpleNamespace(skill_repo=Repository()))
    assert (await service.get_skills())["all"] == []


@pytest.mark.asyncio
async def test_compact_list_skips_histories_and_preserves_full_default():
    repo = Mock()
    repo.list_beliefs.return_value = [BeliefNode("b", "symbia", "B", "Statement", "authored", 0.8, 1, "", "[]")]
    repo.list_proposals.return_value = []
    repo.get_events_for_belief.return_value = []
    repo.get_admission_history.return_value = [{"id": "receipt"}]
    query = BeliefQueryUseCases()
    query._state = SimpleNamespace(belief_repo=repo)
    compact = await query.get_beliefs(include_history=False)
    repo.get_events_for_belief.assert_not_called()
    repo.get_admission_history.assert_not_called()
    assert compact["beliefs"][0]["history_loaded"] is False
    full = await query.get_beliefs()
    assert full["beliefs"][0]["history_loaded"] is True
    assert full["beliefs"][0]["admission_history"] == [{"id": "receipt"}]
    repo.get_events_for_belief.assert_called_once_with("b")


@pytest.mark.asyncio
async def test_history_checks_agent_ownership_before_reading_and_runs_in_worker():
    thread = threading.get_ident()
    repo = Mock()
    repo.get_belief.return_value = None
    query = BeliefQueryUseCases()
    query._state = SimpleNamespace(belief_repo=repo)
    with pytest.raises(LookupError):
        await query.get_belief_history("belief", "other")
    repo.get_belief.assert_called_once_with("other", "belief")
    repo.get_events_for_belief.assert_not_called()
    repo.get_admission_history.assert_not_called()

    def owned(agent, belief):
        assert threading.get_ident() != thread
        return True

    repo.get_belief.side_effect = owned
    repo.get_events_for_belief.return_value = []
    repo.get_admission_history.return_value = []
    assert await query.get_belief_history("belief", "symbia") == {"events": [], "admission_history": []}


def test_history_api_auth_validation_and_not_found(monkeypatch):
    app = FastAPI()
    app.include_router(router, prefix="/api", dependencies=[Depends(verify_password)])
    service = SimpleNamespace(get_belief_history=AsyncMock(side_effect=LookupError("Belief not found")))
    app.dependency_overrides[get_belief_service] = lambda: service
    client = TestClient(app)
    monkeypatch.setenv("AAA_PASSWORD", "fixture")
    assert client.get("/api/beliefs/b/history").status_code == 401
    monkeypatch.setenv("AAA_PASSWORD", "")
    assert client.get("/api/beliefs/b/history?agent_id=../bad").status_code == 422
    assert client.get("/api/beliefs/b/history?agent_id=other").status_code == 404
    service.get_belief_history.assert_awaited_once_with("b", "other")


def test_belief_api_compact_is_opt_in_and_boolean_is_validated():
    app = FastAPI()
    app.include_router(router, prefix="/api")
    service = SimpleNamespace(get_beliefs=AsyncMock(return_value={"beliefs": []}))
    app.dependency_overrides[get_belief_service] = lambda: service
    app.dependency_overrides[get_belief_repo] = lambda: True
    client = TestClient(app)
    assert client.get("/api/beliefs").status_code == 200
    service.get_beliefs.assert_awaited_with(conversation_id=None, agent_id="symbia", include_history=True)
    assert client.get("/api/beliefs?include_history=false").status_code == 200
    service.get_beliefs.assert_awaited_with(conversation_id=None, agent_id="symbia", include_history=False)
    assert client.get("/api/beliefs?include_history=invalid").status_code == 422
