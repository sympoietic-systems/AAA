"""V28 observed dimensions stay source-bound and outside accepted relations."""

import json

import pytest
from pydantic import ValidationError

from backend.modules.sensory.evidence_triage import EvidenceTriage
from backend.services.belief_assessment import assess_encounter
from backend.services.belief_export import BeliefExport
from backend.services.belief_review_contracts import EvaluationDiagnostic
from backend.services.belief_review_store import BeliefReviewStore
from backend.storage.repositories import NotificationRepository
from backend.storage.repositories.cognitive.belief_explicit import ExplicitBeliefRepository
from backend.tests.test_belief_admission import admission_db as admission_db
from backend.tests.test_belief_assessment import CONFIG, Client, emit, pair
from backend.tests.test_belief_review_persistence import sql


class WeakClient(Client):
    async def evaluate(self, state, questions):
        result = await super().evaluate(state, questions)
        result["answers"]["factual_grounding"]["confidence"] = 0.28
        return result


@pytest.mark.asyncio
async def test_v28_abstained_dimensions_persist_without_relations(admission_db):
    path = admission_db[0]
    left, right = await pair(admission_db)
    unknown, _ = await emit(admission_db, scope="", temporal_scope="")
    client = WeakClient(relation="equivalent")
    before = sql(path, "SELECT id,confidence,nucleation_mass FROM belief_proposals ORDER BY id")
    result = await assess_encounter(
        path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(client)
    )
    assert result.evaluator_status == "abstained" and not result.relations and not result.warrant_dimensions
    observed = {d.question_id: d for d in result.evaluation_diagnostics}
    assert observed["factual_grounding"].status == "below_threshold"
    assert observed["factual_grounding"].confidence == 0.28
    assert observed["relation_0"].comparison_id == right["proposal_id"]
    assert observed["relation_0"].comparison_id != unknown["proposal_id"]
    assert observed["relation_0"].choice == "equivalent"
    assert all(d.threshold == 0.85 and not d.is_semantic_verdict for d in observed.values())
    assert result.returned_model == "jev-returned"
    stored = await BeliefReviewStore(path).get_assessment("symbia", result.id)
    assert stored == result
    exported = await BeliefExport(path, "fixture-password").detail("symbia", "assessments", result.id)
    assert exported["record"]["evaluation_diagnostics"] == [
        d.model_dump(mode="json") for d in result.evaluation_diagnostics
    ]
    assert (
        exported["reasoning"]["decision_or_uncertainty"]["evaluation_diagnostics"]
        == exported["record"]["evaluation_diagnostics"]
    )
    projection = ExplicitBeliefRepository(path).projection("symbia", left["encounter_id"])
    trace = next(n for n in NotificationRepository(path).list_all() if n["id"] == result.id + ":assessed")
    assert json.loads(trace["snippet"].split("\n\nAdmission receipt:\n")[1]) == projection
    assert projection["evaluation"]["diagnostics"] == [d.model_dump(mode="json") for d in result.evaluation_diagnostics]
    assert before == sql(path, "SELECT id,confidence,nucleation_mass FROM belief_proposals ORDER BY id")
    assert not sql(path, "SELECT id FROM belief_review_decisions")
    again = await assess_encounter(
        path, "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(client)
    )
    assert again == result and len(client.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("choice", ["contradiction " * 100, "not-a-choice", True, None])
async def test_v28_invalid_choice_omitted_without_losing_other_dimensions(admission_db, choice):
    left, _ = await pair(admission_db)
    result = await assess_encounter(
        admission_db[0],
        "symbia",
        left["encounter_id"],
        config=CONFIG,
        evaluator=EvidenceTriage(Client(relation=choice)),
    )
    observed = next(d for d in result.evaluation_diagnostics if d.question_id == "relation_0")
    assert observed.status == "invalid_choice" and observed.choice is None and observed.confidence is None
    assert result.evaluator_status == "abstained" and not result.relations
    assert len(result.evaluation_diagnostics) == 5


@pytest.mark.parametrize("confidence", [float("nan"), float("inf"), True, -0.1, 1.1])
@pytest.mark.asyncio
async def test_v28_invalid_confidence_rejected(admission_db, confidence):
    with pytest.raises(ValidationError):
        EvaluationDiagnostic(
            question_id="consequence", choice="local", confidence=confidence, threshold=0.85, status="below_threshold"
        )

    class InvalidConfidenceClient(Client):
        async def evaluate(self, state, questions):
            result = await super().evaluate(state, questions)
            result["answers"]["factual_grounding"]["confidence"] = confidence
            return result

    left, _ = await pair(admission_db)
    result = await assess_encounter(
        admission_db[0],
        "symbia",
        left["encounter_id"],
        config=CONFIG,
        evaluator=EvidenceTriage(InvalidConfidenceClient()),
    )
    observed = next(d for d in result.evaluation_diagnostics if d.question_id == "factual_grounding")
    assert observed.status == "invalid_confidence" and observed.confidence is None
    assert result.evaluator_status == "abstained" and not result.relations


@pytest.mark.asyncio
async def test_v28_missing_question_and_historical_default(admission_db):
    class MissingClient(Client):
        async def evaluate(self, state, questions):
            result = await super().evaluate(state, questions)
            result["answers"].pop("tension")
            return result

    left, _ = await pair(admission_db)
    result = await assess_encounter(
        admission_db[0], "symbia", left["encounter_id"], config=CONFIG, evaluator=EvidenceTriage(MissingClient())
    )
    missing = next(d for d in result.evaluation_diagnostics if d.question_id == "tension")
    assert missing.status == "missing" and missing.choice is None and missing.confidence is None
    payload = result.model_dump()
    payload.pop("evaluation_diagnostics")
    assert type(result).model_validate(payload).evaluation_diagnostics == ()
