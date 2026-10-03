import pytest

from backend.tests.test_belief_context import context
from backend.tests.test_belief_triage import VECTOR, service
from benchmarks.suites.belief_calibration import evaluate, freeze
from benchmarks.suites.calibration_contract import belief_score, digest, reviewed_label, validate_splits, wilson


def case():
    a = {
        "id": "a",
        "statement": "All samples red",
        "mass": 0.9,
        "vector": VECTOR,
        "context": context("All samples red").model_dump(mode="json"),
    }
    b = {
        "id": "b",
        "statement": "Some samples not red",
        "mass": 0.9,
        "vector": VECTOR,
        "context": context("Some samples not red").model_dump(mode="json"),
    }
    return {"id": "pair", "split": "heldout", "split_entities": ["a", "b"], "a": a, "b": b, "annotations": []}


def test_v107_independent_labels_and_disagreement_preserved():
    c = case()
    assert reviewed_label(c)[0] is None
    c["annotations"] = [
        {
            "annotator_id": "human1",
            "method": "human",
            "independent": True,
            "label": "contradiction",
            "rationale": "same scope opposing quantifiers",
        }
    ]
    assert reviewed_label(c) == ("contradiction", None)
    c["annotations"].append({**c["annotations"][0], "annotator_id": "human2", "label": "orthogonal"})
    assert reviewed_label(c) == ("abstain", "annotator_disagreement")


def test_v107_leakage_and_repeat_statistics():
    c = case()
    with pytest.raises(ValueError, match="leakage"):
        validate_splits([c, {**c, "id": "other", "split": "tune"}])
    rows = [{"id": "one", "gold": "orthogonal", "receipt": {"route": "review_contradiction"}}] * 3
    assert belief_score(rows)["labeled_rows"] == 1
    assert belief_score(rows)["false_contradictions"] == 1
    assert wilson(0, 0) is None
    assert 0 < wilson(0, 100)[1] < 0.05


@pytest.mark.asyncio
async def test_v107_unlabeled_packets_do_not_call_model_and_freeze_detects_change():
    triage, client = service()
    packet = {"cases": [case()]}
    result = await evaluate(packet, triage)
    assert result["promotion"] == "BLOCKED" and not result["rows"]
    client.evaluate.assert_not_called()
    with pytest.raises(ValueError, match="independent"):
        freeze(packet)
    packet["cases"][0]["annotations"] = [
        {
            "annotator_id": "human",
            "method": "human",
            "independent": True,
            "rationale": "explicit fixture",
            "label": "contradiction",
        }
    ]
    frozen = freeze(packet)
    assert frozen["frozen_sha256"] == digest(frozen["cases"])
    result = await evaluate(frozen, triage)
    assert len(result["rows"]) == 3 and result["promotion"] == "BLOCKED"
    frozen["cases"][0]["a"]["statement"] = "changed"
    with pytest.raises(ValueError, match="changed"):
        await evaluate(frozen, triage)
