import asyncio
import threading
from types import SimpleNamespace

import pytest

from backend.services.belief.query import BeliefQueryUseCases


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
    from backend.modules.belief.engine import BeliefDynamicsEngine

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
