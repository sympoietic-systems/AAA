"""Beliefs v2 V16/V17/V18: measured telemetry and durable decay accounting."""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from backend.modules.belief.decay import DecayManager
from backend.modules.belief_engine import BeliefDynamicsEngine
from backend.services.belief_serializer import serialize_belief_event
from backend.storage.database import init_db
from backend.storage.repositories import BeliefRepository

NOW = datetime(2026, 10, 8, 12, tzinfo=UTC)


@pytest.fixture
def repo(tmp_path):
    path = str(tmp_path / "belief-t2.db")
    init_db(path).close()
    result = BeliefRepository(path)
    result.create_belief(
        id="clock",
        agent_id="t2",
        label="clock",
        statement="Measured intervals remain attributable.",
        origin="authored",
        confidence=0.8,
        ontological_mass=1.0,
        somatic_anchor="conceptual",
        vector_16d=json.dumps([1.0] + [0.0] * 15),
    )
    with sqlite3.connect(path) as conn:
        conn.execute(
            "UPDATE belief_nodes SET last_reinforced_at=?, atrophy_accounted_at=? WHERE id='clock'",
            ((NOW - timedelta(hours=10)).isoformat(), (NOW - timedelta(hours=2)).isoformat()),
        )
    return result


def state(repo):
    belief = repo.get_belief("t2", "clock")
    assert belief is not None
    with sqlite3.connect(repo._db_path) as conn:
        checkpoint = conn.execute("SELECT atrophy_accounted_at FROM belief_nodes WHERE id='clock'").fetchone()[0]
    return belief.ontological_mass, checkpoint, len(repo.get_events_for_belief("clock"))


def test_v18_repeat_clock_and_restart_charges_no_second_interval(repo):
    assert DecayManager.atrophy_beliefs(repo, "t2", now=NOW)["atrophied"] == 1
    first = state(repo)
    assert first[0] == pytest.approx(0.998)
    restarted = BeliefRepository(repo._db_path)
    assert DecayManager.atrophy_beliefs(restarted, "t2", now=NOW)["atrophied"] == 0
    assert state(repo) == first
    DecayManager.atrophy_beliefs(restarted, "t2", now=NOW + timedelta(hours=1))
    assert state(repo)[0] == pytest.approx(0.998 * 0.999)
    assert repo.get_belief("t2", "clock").last_reinforced_at == NOW - timedelta(hours=10)


def test_v18_reinforcement_resets_unaccounted_interval(repo):
    with sqlite3.connect(repo._db_path) as conn:
        conn.execute(
            "UPDATE belief_nodes SET last_reinforced_at=? WHERE id='clock'", ((NOW - timedelta(hours=1)).isoformat(),)
        )
    DecayManager.atrophy_beliefs(repo, "t2", now=NOW)
    assert state(repo)[0] == pytest.approx(0.999)


def test_v18_atomic_failure_keeps_checkpoint_mass_and_event(repo):
    before = state(repo)
    with sqlite3.connect(repo._db_path) as conn:
        conn.execute(
            "CREATE TRIGGER reject_atrophy BEFORE INSERT ON belief_events WHEN NEW.source_type='atrophy' BEGIN SELECT RAISE(ABORT, 'test receipt failure'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="test receipt failure"):
        DecayManager.atrophy_beliefs(repo, "t2", now=NOW)
    assert state(repo) == before


def test_v18_concurrent_same_clock_charges_once(repo):
    def sweep(_):
        return DecayManager.atrophy_beliefs(BeliefRepository(repo._db_path), "t2", now=NOW)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(sweep, range(2)))
    assert sum(r["atrophied"] for r in results) == 1
    assert state(repo)[0] == pytest.approx(0.998)
    assert state(repo)[2] == 1


def test_v18_backward_clock_and_wrong_agent_do_not_charge(repo):
    before = state(repo)
    DecayManager.atrophy_beliefs(repo, "t2", now=NOW - timedelta(hours=3))
    DecayManager.atrophy_beliefs(repo, "other", now=NOW)
    assert state(repo) == before


def test_v18_missing_checkpoint_starts_now_without_recharging_history(repo):
    with sqlite3.connect(repo._db_path) as conn:
        conn.execute("UPDATE belief_nodes SET atrophy_accounted_at=NULL WHERE id='clock'")
    DecayManager.atrophy_beliefs(repo, "t2", now=NOW)
    assert state(repo) == (1.0, NOW.isoformat(), 0)


def test_v17_legacy_event_impact_is_not_inferred_confidence(repo):
    repo.insert_belief_event(
        "legacy", "clock", "scar_fold_monologue", None, 0.8, 0.0, "scar_monologue", 0.15, "mass=1.000 conf=0.800"
    )
    event = serialize_belief_event(repo.get_events_for_belief("clock")[0])
    assert event["delta_confidence"] == 0.15  # Deprecated alias preserved for older clients.
    assert event["impact_value"] == 0.15
    assert event["confidence_delta"] is None
    assert event["delta_mass"] is None
    assert event["impact_quantity"] is None


def test_v17_atrophy_persists_actual_typed_deltas(repo):
    DecayManager.atrophy_beliefs(repo, "t2", now=NOW)
    event = serialize_belief_event(repo.get_events_for_belief("clock")[0])
    assert event["confidence_delta"] == 0.0
    assert event["delta_mass"] == pytest.approx(-0.002)
    assert event["impact_quantity"] == "ontological_mass"
    assert event["impact_unit"] == "mass"


def test_v17_clamped_accretion_persists_actual_typed_deltas(repo):
    with sqlite3.connect(repo._db_path) as conn:
        conn.execute("UPDATE belief_nodes SET ontological_mass=3.0, confidence=0.99 WHERE id='clock'")
    engine = object.__new__(BeliefDynamicsEngine)
    engine._belief_repo = repo
    belief = repo.get_belief("t2", "clock")
    engine._accrete_belief(belief, np.array([1.0] + [0.0] * 15), 1.0, 1.0, 0.0)
    updated = repo.get_belief("t2", "clock")
    event = serialize_belief_event(repo.get_events_for_belief("clock")[0])
    assert event["delta_mass"] == pytest.approx(updated.ontological_mass - belief.ontological_mass)
    assert event["confidence_delta"] == pytest.approx(updated.confidence - belief.confidence)
    assert event["delta_mass"] == 0.0


def test_v21_warm_migration_preserves_legacy_values_and_null_deltas():
    from backend.storage.migrations.m063_belief_event_quantities_and_atrophy_clock import up

    with sqlite3.connect(":memory:") as conn:
        conn.execute("CREATE TABLE belief_nodes (id TEXT, ontological_mass REAL, confidence REAL)")
        conn.execute("INSERT INTO belief_nodes VALUES ('legacy', 0.45, 0.62)")
        conn.execute("CREATE TABLE belief_events (id TEXT, impact_score REAL)")
        conn.execute("INSERT INTO belief_events VALUES ('event', 0.15)")
        up(conn)
        row = conn.execute("SELECT ontological_mass, confidence, atrophy_accounted_at FROM belief_nodes").fetchone()
        assert row[:2] == (0.45, 0.62)
        assert datetime.fromisoformat(row[2]).tzinfo is not None
        assert conn.execute(
            "SELECT impact_score, delta_mass, confidence_delta, impact_quantity, impact_unit FROM belief_events"
        ).fetchone() == (0.15, None, None, None, None)


def test_v18_recent_reinforcement_and_cap_preserve_confidence(repo):
    with sqlite3.connect(repo._db_path) as conn:
        conn.execute(
            "UPDATE belief_nodes SET last_reinforced_at=? WHERE id='clock'",
            ((NOW - timedelta(minutes=20)).isoformat(),),
        )
    before = state(repo)
    DecayManager.atrophy_beliefs(repo, "t2", now=NOW)
    assert state(repo) == before
    with sqlite3.connect(repo._db_path) as conn:
        old = (NOW - timedelta(hours=1000)).isoformat()
        conn.execute(
            "UPDATE belief_nodes SET last_reinforced_at=?, atrophy_accounted_at=? WHERE id='clock'", (old, old)
        )
    DecayManager.atrophy_beliefs(repo, "t2", now=NOW)
    assert state(repo)[0] == pytest.approx(0.8)
    assert repo.get_belief("t2", "clock").confidence == 0.8
    DecayManager.atrophy_beliefs(repo, "t2", now=NOW)
    assert state(repo)[0] == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_v18_legacy_helper_and_active_sweep_share_checkpoint(repo, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from backend.metabolisation.mass_decay import MassDecayMixin

    original = DecayManager.atrophy_beliefs
    monkeypatch.setattr(DecayManager, "atrophy_beliefs", lambda r, a: original(r, "t2", now=NOW))
    helper = SimpleNamespace(
        belief_repo=repo,
        config={"belief_ecosystem": {"wall_clock_decay": {"enabled": True}}},
        _apply_skill_ecology=AsyncMock(),
        last_decay_time=0,
    )
    await MassDecayMixin._apply_mass_decay(helper, 100)
    first = state(repo)
    original(repo, "t2", now=NOW)
    assert state(repo) == first
    assert first[0] == pytest.approx(0.998)


def test_v17_failed_accretion_retains_no_measured_event(repo, monkeypatch):
    engine = object.__new__(BeliefDynamicsEngine)
    engine._belief_repo = repo
    belief = repo.get_belief("t2", "clock")
    before = state(repo)

    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("test mass update failure")

    monkeypatch.setattr(repo, "update_belief_mass", fail)
    with pytest.raises(sqlite3.OperationalError, match="test mass update failure"):
        engine._accrete_belief(belief, np.array([1.0] + [0.0] * 15), 1.0, 1.0, 0.0)
    assert state(repo) == before
    assert repo.get_belief("t2", "clock").confidence == belief.confidence


def test_v17_accretion_measures_latest_mass_under_writer_lock(repo):
    engine = object.__new__(BeliefDynamicsEngine)
    engine._belief_repo = repo
    stale = repo.get_belief("t2", "clock")
    repo.update_belief_mass("clock", 0.7, touch_reinforced=False)
    engine._accrete_belief(stale, np.array([1.0] + [0.0] * 15), 1.0, 1.0, 0.0)
    current = repo.get_belief("t2", "clock")
    event = repo.get_events_for_belief("clock")[0]
    assert event.delta_mass == pytest.approx(current.ontological_mass - 0.7)


@pytest.mark.parametrize("mass,expected", [(0.5, 0.5), (0.55, 0.55), (0.5502, 0.55), (0.8, 0.7995)])
def test_v18_turn_floor_does_not_lift_lower_mass(repo, monkeypatch, mass, expected):
    monkeypatch.setattr("backend.config.load_config", lambda: {"belief_ecosystem": {"turn_decay": {"enabled": True}}})
    repo.update_belief_mass("clock", mass, touch_reinforced=False)
    DecayManager.apply_turn_decay(repo, "t2")
    assert state(repo)[0] == pytest.approx(expected)
