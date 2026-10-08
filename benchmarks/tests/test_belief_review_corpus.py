import copy
import json

import httpx
import pytest

from benchmarks.suites.belief_review_corpus import annotate, collect, freeze, passage, prepare, validate
from benchmarks.suites.calibration_contract import digest


def packet():
    proposals = [
        {
            "id": f"p{i}",
            "label": f"claim-{i}",
            "statement": f"Claim {i}",
            "proposal_status": "refined",
            "source_trace": [{"type": "chat_turn", "id": str(i)}],
        }
        for i in range(6)
    ]
    recovery = {
        "sources": {f"chat_turn:{i}": {"status": "unavailable", "reason": "missing", "passages": []} for i in range(6)}
    }
    return prepare(proposals, [], recovery)


def annotation(case, **changes):
    return {
        "annotator_id": "operator-reviewer",
        "method": "human",
        "independent": True,
        "case_sha256": digest(
            {"a": case["a"], "b": case["b"], "source_snapshot_sha256": case["source_snapshot_sha256"]}
        ),
        "relation": "insufficient_context",
        "warrant": "unknown",
        "scope": "Unknown from unavailable passage",
        "temporal_scope": "Unknown",
        "lineage": "Unknown ancestry; no independent corroboration",
        "consequence": "Cannot assess without passage",
        "challenge": "Recover original source",
        "rationale": "Explicitly unavailable",
        "useful_distinction_or_conflict": "Undetermined",
        **changes,
    }


def reviewed_packet():
    result = packet()
    for case in result["cases"]:
        case["annotations"] = [annotation(case)]
    result["manifest_sha256"] = digest(result["cases"])
    return result


def test_v22_shared_source_and_comparison_hub_do_not_leak():
    proposals = [
        {
            "id": f"p{i}",
            "label": "claim",
            "statement": f"Claim {i}",
            "source_trace": [{"type": "chat_turn", "id": "1"}],
            "potential_merge_target": "b",
        }
        for i in range(3)
    ]
    result = prepare(
        proposals,
        [{"id": "b", "label": "hub", "statement": "Broad hub"}],
        {"sources": {"chat_turn:1": {"status": "unavailable", "passages": []}}},
    )
    assert len({c["split"] for c in result["cases"]}) == 1
    assert len({c["family_id"] for c in result["cases"]}) == 1
    with pytest.raises(ValueError, match="partitions"):
        freeze(result)


def test_v22_self_labels_cannot_freeze_unknown_legacy_author():
    result = packet()
    for case in result["cases"]:
        case["annotations"] = [annotation(case, method="independent_model", annotator_id="jev")]
    result["manifest_sha256"] = digest(result["cases"])
    with pytest.raises(ValueError, match="human review"):
        freeze(result)


def test_v22_missing_review_stays_pending_and_failure_does_not_mutate():
    result = reviewed_packet()
    result["cases"][-1]["annotations"] = []
    result["manifest_sha256"] = digest(result["cases"])
    before = copy.deepcopy(result)
    with pytest.raises(ValueError, match="every case"):
        freeze(result)
    assert result == before


def test_v7_v8_unavailable_passage_cannot_establish_relation():
    result = reviewed_packet()
    result["cases"][0]["annotations"][0]["relation"] = "equivalent"
    result["manifest_sha256"] = digest(result["cases"])
    with pytest.raises(ValueError, match="Unavailable"):
        freeze(result)


def test_v22_frozen_bindings_and_disagreement_preserved():
    result = reviewed_packet()
    result["cases"][0]["annotations"].append(
        annotation(result["cases"][0], annotator_id="second-human", warrant="tension")
    )
    result["manifest_sha256"] = digest(result["cases"])
    frozen = freeze(result)
    assert frozen["cases"][0]["review_outcome"] == "disagreement"
    assert frozen["promotion"] == "BLOCKED"
    validate(frozen)
    frozen["cases"][0]["a"]["statement"] = "Different statement"
    with pytest.raises(ValueError, match="changed"):
        validate(frozen)


def test_v20_source_recovery_is_get_only_and_sanitized():
    calls = []

    def handler(request):
        calls.append(request.method)
        return httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "speaker": "symbia",
                    "content": "API_KEY=private-key-value",
                    "timestamp": "2026-10-08T00:00:00",
                }
            ],
        )

    with httpx.Client(base_url="https://example.com/api/", transport=httpx.MockTransport(handler)) as client:
        result = collect([{"source_trace": [{"type": "chat_turn", "id": "1"}]}], client)
    assert calls == ["GET"]
    assert "private-key-value" not in json.dumps(result)
    assert result["sources"]["chat_turn:1"]["passages"][0]["redacted"]


def test_v7_recovery_failure_and_internal_authorship_are_explicit():
    def handler(request):
        return httpx.Response(200, json={"messages": [], "count": 0})

    with httpx.Client(base_url="https://example.com/api/", transport=httpx.MockTransport(handler)) as client:
        result = collect([{"source_trace": [{"type": "intention", "conversation_id": "missing"}]}], client)
    assert result["sources"]["conversation:missing"]["reason"] == "source_not_returned"
    item = passage({"id": 7, "speaker": "apparatus", "content": "Repeated internal assent"})
    assert item["speaker"] == "apparatus"
    assert "independent" not in item


def test_v22_source_changes_invalidate_case_and_annotation_binding():
    result = reviewed_packet()
    result["recovery"]["sources"]["chat_turn:0"]["reason"] = "changed context"
    with pytest.raises(ValueError, match="source snapshot"):
        validate(result)


def test_v22_annotation_bound_to_current_context():
    result = reviewed_packet()
    result["cases"][0]["annotations"][0]["case_sha256"] = "0" * 64
    result["manifest_sha256"] = digest(result["cases"])
    with pytest.raises(ValueError, match="bind current"):
        freeze(result)


def test_v22_partial_review_import_is_bound_and_append_only():
    result = packet()
    first = result["cases"][0]
    submission = {"case_id": first["id"], **annotation(first)}
    updated = annotate(result, [submission])
    validate(updated)
    assert not updated["frozen"] and updated["annotation_status"] == "REVIEW_IN_PROGRESS"
    assert result["cases"][0]["annotations"] == []
    with pytest.raises(ValueError, match="already annotated"):
        annotate(updated, [submission])
    with pytest.raises(ValueError, match="unknown or changed"):
        annotate(result, [{**submission, "case_sha256": "0" * 64}])


def test_v22_candidate_context_does_not_resolve_comparison_context():
    result = packet()
    case = result["cases"][0]
    case["context_status"] = "available"
    case["comparison_context_status"] = "unavailable"
    for c in result["cases"]:
        c["annotations"] = [annotation(c)]
    case["annotations"][0]["relation"] = "equivalent"
    result["manifest_sha256"] = digest(result["cases"])
    with pytest.raises(ValueError, match="Unavailable"):
        freeze(result)


def test_v22_existing_comparison_cannot_be_erased_by_no_comparison_label():
    result = packet()
    case = result["cases"][0]
    case["b"] = copy.deepcopy(case["a"])
    case["review_input_sha256"] = digest(
        {"a": case["a"], "b": case["b"], "source_snapshot_sha256": case["source_snapshot_sha256"]}
    )
    for c in result["cases"]:
        c["annotations"] = [annotation(c)]
    case["annotations"][0]["relation"] = "no_comparison"
    result["manifest_sha256"] = digest(result["cases"])
    with pytest.raises(ValueError, match="Existing comparison"):
        freeze(result)
