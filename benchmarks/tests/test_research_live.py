import json

import pytest

from backend.modules.llm_protocol import BaseLLMProvider
from benchmarks.suites.research_live import ObservedProvider, run_arm, summarize


class FixtureProvider(BaseLLMProvider):
    @property
    def provider_name(self):
        return "fixture"

    async def validate_connection(self):
        return True

    async def generate(self, messages, **params):
        return {
            "content": json.dumps(
                {
                    "search_queries": ["fixture question"],
                    "goal": "Compare evidence",
                    "selected_indices": [0, 1],
                    "learnings": ["Source evidence supports a bounded claim [1]."],
                    "completeness_score": 0.9,
                    "confidence": 0.8,
                    "next_action": "synthesize",
                    "report_markdown": "The captured source supports this limited claim [1].",
                }
            ),
            "finish_reason": "stop",
            "truncated": False,
        }


@pytest.mark.asyncio
@pytest.mark.parametrize("arm", ["legacy", "v2"])
async def test_live_harness_runs_pipeline_with_identical_frozen_pool(tmp_path, arm):
    case = {
        "id": "fixture",
        "objective": "Compare evidence",
        "sources": [
            {
                "id": "one",
                "url": "https://example.org/evidence",
                "title": "Source",
                "snippet": "Captured evidence supports a bounded claim with explicitly limited certainty. " * 4,
            },
        ],
    }
    case["sources"].append({**case["sources"][0], "id": "duplicate-query-hit"})
    checkpoints = []
    row = await run_arm(case, arm, FixtureProvider(), tmp_path / "run.db", lambda row: checkpoints.append(dict(row)))
    assert row["operationally_valid"], row
    assert row["steps"][-1]["next_phase"] == "complete"
    assert row["available_source_ids"] == ["one", "duplicate-query-hit"]
    assert row["sources_analyzed"] == 1
    assert row["branches_created"] == 0
    assert checkpoints
    assert row["independent_quality"] is None
    assert row["known_cost_usd"] is None


@pytest.mark.asyncio
async def test_failed_provider_observation_cannot_claim_completion():
    class Failing(FixtureProvider):
        async def generate(self, messages, **params):
            raise RuntimeError("fixture outage")

    observed = ObservedProvider(Failing(), interval=0)
    with pytest.raises(RuntimeError, match="outage"):
        await observed.generate([])
    assert observed.calls[0]["status"] == "failed"
    assert "content" not in observed.calls[0]


def test_incomplete_trials_never_become_quality_or_billing_results():
    summary = summarize([{"arm": "v2", "provider_calls": [{"status": "failed"}]}])
    assert summary["arms"]["v2"]["operationally_valid"] == 0
    assert summary["arms"]["legacy"]["median_pipeline_seconds"] is None
    assert summary["independent_quality"] is None
    assert summary["known_cost_usd"] is None
    assert not summary["quality_ranking_allowed"]


@pytest.mark.asyncio
async def test_cancelled_provider_observation_is_terminal_and_counted():
    import asyncio

    class Cancelled(FixtureProvider):
        async def generate(self, messages, **params):
            raise asyncio.CancelledError()

    observed = ObservedProvider(Cancelled(), interval=0)
    with pytest.raises(asyncio.CancelledError):
        await observed.generate([])
    assert observed.calls[0]["status"] == "cancelled"
    result = summarize([{"arm": "v2", "provider_calls": observed.calls}])
    assert result["arms"]["v2"]["provider_incomplete"] == 1
    assert result["arms"]["v2"]["operationally_valid"] == 0
