import copy
import json

import pytest

from backend.modules.llm_protocol import BaseLLMProvider, RateLimitError
from benchmarks.suites.belief_auto_review import (
    ReviewDraft,
    effective_review,
    freeze_provisional,
    render_review,
    review_input,
    run,
    validate_provisional,
)
from benchmarks.suites.calibration_contract import digest
from benchmarks.tests.test_belief_review_corpus import packet


def draft(**changes):
    return {
        "relation": "equivalent",
        "warrant": "unknown",
        "scope": "Unknown scoped claim",
        "temporal_scope": "Unknown time",
        "lineage": "Unknown ancestry; no corroboration",
        "consequence": "Compare the decision this claim changes",
        "challenge": "Recover source context",
        "rationale": "Context limits relation assessment",
        "useful_distinction_or_conflict": "Unresolved useful question",
        "source_message_ids": [],
        "recommendation": "await_context",
        **changes,
    }


class FakeProvider(BaseLLMProvider):
    def __init__(self, model, content=None):
        self.model = model
        self.content = content or json.dumps(draft())
        self.calls = []

    @property
    def provider_name(self):
        return "fixture"

    async def validate_connection(self):
        return True

    async def generate(self, messages, **params):
        self.calls.append((messages, params))
        return {
            "model": self.model,
            "model_reported": True,
            "provider_used": "fixture",
            "content": self.content,
            "finish_reason": "stop",
            "truncated": False,
        }


def providers():
    return {m: FakeProvider(m) for m in ("qwen/qwen3.8-flash", "google/gemini-3.8-flash")}


@pytest.mark.asyncio
async def test_v26_rate_limit_stops_new_calls_without_replaying_failed_attempt(tmp_path):
    class Limited(FakeProvider):
        async def generate(self, messages, **params):
            self.calls.append(messages)
            raise RateLimitError("fixture", retry_after=1, limit_source="upstream_provider_shared_pool")

    p = packet()
    ps = providers()
    limited = Limited("qwen/qwen3.8-flash")
    ps[limited.model] = limited
    await run(p, ps, tmp_path, workers=1, max_cases=1)
    rows = await run(p, ps, tmp_path, workers=1)
    failures = [r for r in rows if r["model_requested"] == limited.model]
    assert len(limited.calls) == 1
    assert failures[0]["limit_source"] == "upstream_provider_shared_pool"
    assert failures[0]["retry_after"] == 1
    assert all(r["status"] == "provider_unavailable" for r in failures[1:])
    await run(p, ps, tmp_path, workers=1)
    assert len(limited.calls) == 1


@pytest.mark.asyncio
async def test_v19_v26_three_failed_calls_open_and_restore_reviewer_circuit(tmp_path):
    p = packet()
    ps = providers()
    ps["qwen/qwen3.8-flash"].content = "invalid JSON"
    await run(p, ps, tmp_path, workers=1, max_cases=3)
    resumed = providers()
    rows = await run(p, resumed, tmp_path, workers=1)
    assert not resumed["qwen/qwen3.8-flash"].calls
    assert sum(r["status"] == "provider_unavailable" for r in rows) == 3


@pytest.mark.asyncio
async def test_v22_v26_disagreement_is_retained_without_majority_authority(tmp_path):
    p = packet()
    ps = providers()
    ps["google/gemini-3.8-flash"].content = json.dumps(draft(warrant="artistic"))
    frozen = freeze_provisional(p, await run(p, ps, tmp_path))
    assert frozen["coverage"] == {"disagreement": 6}
    assert frozen["promotion"] == "BLOCKED" and frozen["adoption_authority"] == "none"


def test_v20_rendered_review_cannot_execute_model_markup():
    frozen = {
        "coverage": {"unavailable": 1},
        "cases": [
            {
                "family_id": "family",
                "case_id": "case",
                "split": "heldout",
                "review_outcome": "unavailable",
                "reviewers": [
                    {"model_requested": "fixture", "status": "unavailable", "reason": "<script>bad()</script>"}
                ],
            }
        ],
    }
    page = render_review(frozen)
    assert "<script>" not in page and "&lt;script&gt;" in page
    assert "default-src 'none'" in page


def test_v26_blind_input_excludes_status_and_prior_verdicts():
    p = packet()
    case = p["cases"][0]
    case["a"]["legacy_status"] = "adopted"
    case["annotations"] = [{"relation": "equivalent", "rationale": "prior model opinion"}]
    value = json.dumps(review_input(p, case))
    assert "legacy_status" not in value and "adopted" not in value and "prior model opinion" not in value


def test_v3_v26_missing_context_cannot_be_overruled_by_consensus():
    p = packet()
    case = p["cases"][0]
    case["b"] = copy.deepcopy(case["a"])
    case["comparison_context_status"] = "unavailable"
    result = effective_review(case, review_input(p, case), ReviewDraft(**draft()))
    assert result["raw_relation"] == "equivalent" and result["relation"] == "insufficient_context"
    assert not result["independent"] and result["adoption_authority"] == "none"


def test_v26_unbound_citations_and_extra_authority_are_invalid():
    p = packet()
    case = p["cases"][0]
    with pytest.raises(ValueError, match="unbound"):
        effective_review(case, review_input(p, case), ReviewDraft(**draft(source_message_ids=["invented"])))
    with pytest.raises(ValueError):
        ReviewDraft(**draft(adoption_authority="system"))


@pytest.mark.asyncio
async def test_v26_two_reviewers_freeze_as_provisional_not_gold(tmp_path):
    p = packet()
    ps = providers()
    before = copy.deepcopy(p)
    receipts = await run(p, ps, tmp_path)
    frozen = freeze_provisional(p, receipts)
    assert p == before
    assert frozen["coverage"] == {"model_agreement": 6}
    assert frozen["frozen"] and not frozen["independent_gold"]
    assert frozen["promotion"] == "BLOCKED" and frozen["adoption_authority"] == "none"
    assert all(len(provider.calls) == 6 for provider in ps.values())
    assert all(receipt["annotation"]["independence_status"] == "legacy_author_unknown" for receipt in receipts)
    validate_provisional(p, frozen)
    altered = copy.deepcopy(receipts)
    altered[0]["annotation"]["relation"] = "equivalent"
    with pytest.raises(ValueError, match="deterministic"):
        freeze_provisional(p, altered)
    changed = copy.deepcopy(frozen)
    changed["independent_gold"] = True
    changed["frozen_sha256"] = digest({k: v for k, v in changed.items() if k != "frozen_sha256"})
    with pytest.raises(ValueError, match="authority"):
        validate_provisional(p, changed)


@pytest.mark.asyncio
async def test_v26_resume_never_replays_completed_or_uncertain_calls(tmp_path):
    p = packet()
    ps = providers()
    receipts = await run(p, ps, tmp_path)
    first = next(tmp_path.glob("*.json"))
    value = json.loads(first.read_text())
    value["status"] = "outcome_unknown"
    first.write_text(json.dumps(value))
    new = providers()
    reused = await run(p, new, tmp_path)
    assert all(not provider.calls for provider in new.values())
    assert len(reused) == len(receipts) and any(r["status"] == "outcome_unknown" for r in reused)


@pytest.mark.asyncio
async def test_v26_replacement_reviewer_reuses_exact_peer_receipts_without_copy_or_replay(tmp_path):
    p = packet()
    first = tmp_path / "first"
    original = await run(p, providers(), first)
    second = tmp_path / "second"
    ps = {m: FakeProvider(m) for m in ("nvidia_router/nvidia/nemotron-3-ultra-550b-a55b", "google/gemini-3.8-flash")}
    rows = await run(p, ps, second, reuse_from=first)
    assert not ps["google/gemini-3.8-flash"].calls
    assert len(ps["nvidia_router/nvidia/nemotron-3-ultra-550b-a55b"].calls) == 6
    assert len(list(second.glob("*.json"))) == 6
    assert [r for r in rows if r["model_requested"].startswith("google")] == [
        r for r in original if r["model_requested"].startswith("google")
    ]
    validate_provisional(p, freeze_provisional(p, rows))


@pytest.mark.asyncio
async def test_v26_malformed_output_is_unavailable_not_a_vote(tmp_path):
    p = packet()
    ps = providers()
    ps["qwen/qwen3.8-flash"].content = "not JSON"
    receipts = await run(p, ps, tmp_path)
    frozen = freeze_provisional(p, receipts)
    assert frozen["coverage"] == {"unavailable": 6}
    assert all(r["reason"] == "ValidationError" for r in receipts if r["status"] == "unavailable")


@pytest.mark.asyncio
async def test_v26_provider_family_change_is_not_independent_review(tmp_path):
    p = packet()
    ps = providers()
    ps["qwen/qwen3.8-flash"].model = "google/gemini-3.8-flash"
    receipts = await run(p, ps, tmp_path)
    assert freeze_provisional(p, receipts)["coverage"] == {"unavailable": 6}


@pytest.mark.asyncio
async def test_v26_same_family_and_changed_resume_inputs_rejected(tmp_path):
    p = packet()
    with pytest.raises(ValueError, match="distinct"):
        await run(p, {m: FakeProvider(m) for m in ("qwen/a", "qwen/b")}, tmp_path)
    ps = providers()
    await run(p, ps, tmp_path)
    path = next(tmp_path.glob("*.json"))
    receipt = json.loads(path.read_text())
    receipt["prompt_sha256"] = "0" * 64
    path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="different inputs"):
        await run(p, providers(), tmp_path)


def test_v26_frozen_review_requires_every_case_and_retains_disagreement():
    p = packet()
    with pytest.raises(ValueError, match="Every case"):
        freeze_provisional(p, [])
