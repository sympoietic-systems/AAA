import hashlib
import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.modules.sensory.belief_context import ClaimContext
from backend.modules.sensory.evidence_triage import EvidenceTriage
from backend.services.belief_triage import BeliefEvidence as RawBeliefEvidence
from backend.services.belief_triage import BeliefTriage, nominate_pairs, replay
from backend.storage.database import init_db
from backend.storage.repositories.cognitive.belief import BeliefRepository
from benchmarks.suites.belief_triage import VECTOR, digest_file, matrix_copy, read_snapshot


def BeliefEvidence(identifier, statement, mass, vector):
    return RawBeliefEvidence(
        identifier,
        statement,
        mass,
        vector,
        ClaimContext(
            statement_sha256=hashlib.sha256(statement.encode()).hexdigest(),
            scope="explicit fixture",
            temporal_scope="same fixture time",
            provenance="test fixture",
            resolution="resolved",
        ),
    )


def service(relation="contradiction", confidence=0.99, strength=0.9, absorbable=0.1):
    client = SimpleNamespace(
        model="fixture",
        is_configured=True,
        evaluate=AsyncMock(
            return_value={
                "success": True,
                "answers": {
                    "relation": {"choice": relation, "confidence": confidence},
                    "contradicts": {"score": strength, "confidence": confidence},
                    "absorbable": {"score": absorbable, "confidence": confidence},
                },
            }
        ),
    )
    return BeliefTriage(EvidenceTriage(client)), client


@pytest.mark.asyncio
async def test_identical_vectors_are_only_nomination_not_contradiction():
    triage, _ = service("endorsement", strength=0.05, absorbable=0.95)
    a, b = BeliefEvidence("a", "Same claim", 0.9, VECTOR), BeliefEvidence("b", "Same claim", 0.9, VECTOR)
    receipt = await triage.evaluate_pair(a, b)
    assert receipt["cosine_similarity"] == 1
    assert receipt["route"] == "review_absorption" and receipt["tension_magnitude"] is None
    assert replay(receipt) == receipt
    assert not hasattr(triage, "repository")


@pytest.mark.asyncio
async def test_mass_changes_priority_and_gate_not_measured_contradiction():
    triage, evaluator = service(confidence=0.8)
    young = await triage.evaluate_pair(BeliefEvidence("a", "A", 0.2, VECTOR), BeliefEvidence("b", "B", 0.2, VECTOR))
    mature = await triage.evaluate_pair(
        BeliefEvidence("a", "A", 0.9, VECTOR),
        BeliefEvidence("b", "B", 0.9, VECTOR),
        prior_evidence={"tension_magnitude": 0.3},
    )
    assert young["route"] == "review_contradiction" and young["tension_magnitude"] == 0.9
    assert mature["route"] == "watchlist" and mature["tension_magnitude"] is None
    assert young["p_contradicts"] == mature["p_contradicts"] == 0.9
    assert mature["priority"] > young["priority"]
    assert "prior_evidence" not in evaluator.evaluate.call_args.args[0]
    assert "masses" not in evaluator.evaluate.call_args.args[0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "relation,strength,confidence",
    [
        ("invented", 0.9, 0.99),
        ("contradiction", float("nan"), 0.99),
        ("contradiction", 0.2, 0.99),
        ("endorsement", 0.9, 0.99),
        ("contradiction", 0.9, 0.6),
        ("abstain", 0.2, 0.99),
    ],
)
async def test_invalid_uncertain_and_disagreeing_answers_do_not_commit(relation, strength, confidence):
    triage, _ = service(relation, confidence, strength)
    receipt = await triage.evaluate_pair(BeliefEvidence("a", "A", 0.9, VECTOR), BeliefEvidence("b", "B", 0.9, VECTOR))
    assert receipt["route"] == "abstain" and receipt["tension_magnitude"] is None


@pytest.mark.asyncio
async def test_candidate_routing_has_no_belief_edge_or_drop_path():
    triage, _ = service()
    proposal = BeliefEvidence("proposal", "A", 0.1, VECTOR)
    belief = BeliefEvidence("belief", "B", 0.9, VECTOR)
    receipts = await triage.route_candidate(proposal, [belief])
    assert receipts[0]["route"] == "review_contradiction"
    assert receipts[0]["kind"] == "proposal_review" and receipts[0]["tension_magnitude"] is None
    assert receipts[0]["mode"] == "dry_run"
    with pytest.raises(ValueError):
        await triage.route_candidate(proposal, [belief], limit=11)


@pytest.mark.asyncio
async def test_absorption_uncertainty_does_not_hide_contradiction():
    triage, evaluator = service()
    evaluator.evaluate.return_value["answers"]["absorbable"]["confidence"] = 0.2
    receipt = await triage.evaluate_pair(BeliefEvidence("a", "A", 0.9, VECTOR), BeliefEvidence("b", "B", 0.9, VECTOR))
    assert receipt["route"] == "review_contradiction" and receipt["tension_magnitude"] == 0.9


def test_nomination_budget_malformed_vectors_and_identity():
    beliefs = [BeliefEvidence(str(i), "A", 0.1, VECTOR) for i in range(70)]
    assert len(nominate_pairs(beliefs)) == 20
    assert nominate_pairs(list(reversed(beliefs))) == nominate_pairs(beliefs)
    with pytest.raises(ValueError):
        nominate_pairs([beliefs[0], beliefs[0]])
    for vector in (tuple([0.0] * 16), tuple([float("nan")] * 16), (1.0,), tuple([1e200] * 16), tuple([True] * 16)):
        with pytest.raises(ValueError):
            BeliefEvidence("invalid", "A", 0.2, vector)


@pytest.mark.asyncio
async def test_snapshot_copy_populates_only_tension_with_atomic_stale_rejection(tmp_path):
    source = tmp_path / "source_test.db"
    conn = init_db(str(source))
    conn.close()
    repo = BeliefRepository(source)
    for identifier, statement in (("a", "All samples red"), ("b", "Some samples not red"), ("c", "A third claim")):
        repo.create_belief(
            identifier, "symbia", identifier, statement, "authored", 0.9, 0.9, "none", json.dumps(VECTOR)
        )
    before = digest_file(source)
    beliefs, _, skipped, prior = read_snapshot(source, "symbia")
    assert not skipped and not prior
    beliefs = [BeliefEvidence(b.id, b.statement, b.mass, b.vector) for b in beliefs]
    triage, _ = service()
    receipt = await triage.evaluate_pair(beliefs[0], beliefs[1])
    destination = tmp_path / "matrix_test.db"
    rows = matrix_copy(source, destination, [receipt])
    assert len(rows) == 1 and rows[0]["tension_magnitude"] == 0.9
    assert digest_file(source) == before
    with sqlite3.connect(source) as a, sqlite3.connect(destination) as b:
        assert (
            a.execute("SELECT * FROM belief_nodes ORDER BY id").fetchall()
            == b.execute("SELECT * FROM belief_nodes ORDER BY id").fetchall()
        )
        assert a.execute("SELECT COUNT(*) FROM belief_tensions").fetchone()[0] == 0
    stale = await triage.evaluate_pair(beliefs[0], beliefs[2])
    stale["statement_hashes"][1] = "tampered"
    rejected = tmp_path / "rejected_test.db"
    with pytest.raises(ValueError, match="stale"):
        matrix_copy(source, rejected, [receipt, stale])
    with sqlite3.connect(rejected) as conn:
        assert conn.execute("SELECT COUNT(*) FROM belief_tensions").fetchone()[0] == 0
    with pytest.raises(ValueError, match="fresh"):
        matrix_copy(source, source, [receipt])
    with pytest.raises(ValueError, match="fresh"):
        matrix_copy(source, destination, [receipt])
