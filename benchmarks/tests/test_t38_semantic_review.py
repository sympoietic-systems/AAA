"""Tests for blinded T38 model-judge input and checkpoint contracts."""

from __future__ import annotations

import json

import pytest

from benchmarks.suites.telemetry.run_t38_semantic_review import (
    _bind_excerpt,
    _build_payload,
    _review_one,
    _validate_response,
)


def _triplet():
    policies = ("current", "sham", "active")
    arms = {}
    key = {"C01": {"Option A": "sham", "Option B": "active", "Option C": "current"}}
    for policy in policies:
        turns = []
        for index in range(8):
            turns.append(
                {
                    "turn": index + 1,
                    "user": f"Participant state {index + 1}",
                    "apparatus": f"Assistant response {index + 1}",
                    "next_participant_completion": {
                        "valid": True,
                        "content": f"Follow-up {index + 1}",
                    },
                }
            )
        arms[policy] = {"turns": turns, "policy": policy, "mean_uptake": 0.9}
    return arms, key


def test_v1_blinded_payload_has_all_21_outcomes_without_arm_or_metric_metadata():
    arms, key = _triplet()
    payload = _build_payload("C01", ("scenario", 1), arms, key)
    encoded = json.dumps(payload)
    assert len(payload["options"]) == 3
    assert sum(len(option["dialogue_outcomes"]) for option in payload["options"].values()) == 21
    assert all(policy not in encoded for policy in ("current", "sham", "active"))
    assert "mean_uptake" not in encoded and "scenario" not in encoded


def test_v1_response_requires_exact_item_set_and_bound_evidence():
    expected = {"C01-A-T1": "Participant proposes a bounded test.", "C01-B-T1": "Needs more evidence."}
    valid = {
        "ratings": [
            {
                "item_id": item,
                "score": 3,
                "confidence": "medium",
                "evidence": text[:20],
                "rationale": "Specific next step.",
            }
            for item, text in expected.items()
        ]
    }
    assert len(_validate_response(json.dumps(valid), expected)) == 2
    valid["ratings"][0]["evidence"] = "fabricated excerpt"
    with pytest.raises(ValueError, match="source-bound"):
        _validate_response(json.dumps(valid), expected)
    valid["ratings"][0]["evidence"] = expected["C01-A-T1"][:20]
    valid["ratings"].append(valid["ratings"][0])
    with pytest.raises(ValueError, match="IDs"):
        _validate_response(json.dumps(valid), expected)


def test_v1_excerpt_binding_normalizes_formatting_and_repairs_only_close_source_spans():
    actual, binding = _bind_excerpt(
        "sustained write availability *during* the partition",
        "Measure sustained write availability during the partition.",
    )
    assert actual == "sustained write availability during the partition"
    assert binding == "normalized_source_span"
    repaired, binding = _bind_excerpt(
        "measure p99 latency to reconstruct",
        "We must also measure the p99 latency to reconstruct a recent state.",
    )
    assert repaired == "measure the p99 latency to reconstruct"
    assert binding == "repaired_near_exact_source_span"
    with pytest.raises(ValueError, match="source-bound"):
        _bind_excerpt("invented unrelated statement", "Participant requested a bounded test.")


def test_v1_long_exact_citation_is_shortened_to_a_verbatim_source_span():
    source = "A " + "specific technical detail " * 15 + "supports the proposed bounded test."
    excerpt, binding = _bind_excerpt(source, source)
    assert excerpt in source
    assert len(excerpt.split()) == 24
    assert binding == "shortened_exact_source_span"


class _FixtureProvider:
    def __init__(self):
        self.calls = 0

    async def generate(self, messages, **_kwargs):
        self.calls += 1
        payload = json.loads(messages[-1]["content"])
        ratings = [
            {
                "item_id": outcome["item_id"],
                "score": 2,
                "confidence": "medium",
                "evidence": outcome["participant_followup"][:12],
                "rationale": "The follow-up shows limited progress.",
            }
            for option in payload["options"].values()
            for outcome in option["dialogue_outcomes"]
        ]
        return {
            "model": "google/gemini-3.8-flash",
            "content": json.dumps({"ratings": ratings}),
            "finish_reason": "stop",
            "model_reported": True,
        }


@pytest.mark.asyncio
async def test_v1_checkpoint_reuses_validated_call_without_replaying(tmp_path):
    arms, key = _triplet()
    payload = _build_payload("C01", ("scenario", 1), arms, key)
    provider = _FixtureProvider()
    kwargs = {
        "provider": provider,
        "model": "google/gemini-3.8-flash",
        "reviewer_position": 0,
        "payload": payload,
        "out_path": tmp_path / "review.json",
        "source_sha256": "source-hash",
        "task_sha256": "task-hash",
    }
    first = await _review_one(**kwargs)
    second = await _review_one(**kwargs)
    assert first["status"] == second["status"] == "complete"
    assert len(first["ratings"]) == 21 and provider.calls == 1
