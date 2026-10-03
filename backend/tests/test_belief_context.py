import hashlib

import pytest

from backend.modules.sensory.belief_context import ClaimContext, ReferenceBinding, context_error
from backend.services.belief_triage import BeliefEvidence, replay
from backend.tests.test_belief_triage import VECTOR, service


def context(statement, **updates):
    return ClaimContext(
        statement_sha256=hashlib.sha256(statement.encode()).hexdigest(),
        scope="device A",
        temporal_scope="2026-10-03",
        provenance="explicit test annotation",
        resolution="resolved",
        **updates,
    )


@pytest.mark.asyncio
async def test_v107_unresolved_references_abstain_before_network():
    triage, client = service()
    a = BeliefEvidence("a", "It is ready.", 0.9, VECTOR, context("It is ready."))
    b = BeliefEvidence("b", "It is not ready.", 0.9, VECTOR, context("It is not ready."))
    result = await triage.evaluate_pair(a, b)
    assert result["route"] == "abstain" and result["reason"] == "unresolved_referent"
    client.evaluate.assert_not_called()
    binding = ReferenceBinding(start=0, end=2, candidates=("device A",), confidence=1)
    a = BeliefEvidence("a", a.statement, a.mass, a.vector, context(a.statement, bindings=(binding,)))
    b = BeliefEvidence("b", b.statement, b.mass, b.vector, context(b.statement, bindings=(binding,)))
    result = await triage.evaluate_pair(a, b)
    assert result["context_validated"] and result["route"] == "review_contradiction"
    state = client.evaluate.call_args.args[0]
    assert state["a_context"]["temporal_scope"] == "2026-10-03"


def test_v107_missing_stale_ambiguous_and_weak_context_fail_closed():
    assert context_error("Claim", None) == "missing_context"
    assert context_error("Changed", context("Claim")) == "stale_context"
    for candidates, confidence in [((), 1), (("A", "B"), 1), (("A",), 0.89)]:
        binding = ReferenceBinding(start=0, end=2, candidates=candidates, confidence=confidence)
        assert context_error("It works", context("It works", bindings=(binding,))) == "unresolved_referent"
    assert replay({"status": "evaluated", "answers": {}})["reason"] == "unvalidated_context"


def test_v107_nonreferential_occurrence_requires_explicit_annotation():
    statement = "I know that sample A is red."
    binding = ReferenceBinding(start=7, end=11, role="nonreferential", candidates=(), confidence=1)
    assert context_error(statement, context(statement, bindings=(binding,))) is None
