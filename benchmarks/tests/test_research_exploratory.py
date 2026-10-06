from unittest.mock import AsyncMock, patch

import pytest

from benchmarks.suites.research_exploratory import run, summarize


def case(split="heldout"):
    return {
        "id": split,
        "split": split,
        "split_entities": [split],
        "source_pool_complete": True,
        "sources": [{"id": "s1"}],
        "annotations": [
            {
                "method": "model_provisional",
                "label": {"s1": {"relevant": True, "quality": "unknown", "contrary": True, "injection": False}},
            }
        ],
    }


@pytest.mark.asyncio
async def test_repeats_checkpoint_and_exclude_tuning_without_claiming_gold():
    selection = {"selected_ids": ["s1"], "latency_ms": 5, "receipt": {"status": "evaluated"}}
    snapshots = []
    with patch("benchmarks.suites.research_exploratory.compare_selection", AsyncMock(return_value=selection)):
        rows = await run({"cases": [case(), case("tune")]}, None, None, lambda r: snapshots.append(len(r)))
    assert len(rows) == 9 and snapshots == list(range(1, 10))
    assert all(r["id"] == "heldout" for r in rows)
    summary = summarize(rows)
    assert summary["promotion"] == "BLOCKED" and summary["independent_quality"] is None
    assert summary["arms"]["legacy"]["unique_queries"] == 1
    assert summary["arms"]["legacy"]["task_families"] == 1


def test_abstention_fallback_is_not_a_valid_model_trial():
    row = {
        "id": "q",
        "family": ["f"],
        "arm": "combined",
        "reference_labels": {},
        "selection": {"selected_ids": ["s1"], "latency_ms": 5, "receipt": {"status": "abstain"}},
    }
    summary = summarize([row])["arms"]["combined"]
    assert summary["valid_selections"] == 0
    assert summary["provisional_relevance_fraction"] is None


@pytest.mark.asyncio
async def test_missing_labels_reject_before_provider_calls():
    missing = case()
    missing["annotations"] = []
    with (
        patch("benchmarks.suites.research_exploratory.compare_selection", AsyncMock()) as model,
        pytest.raises(ValueError, match="annotation"),
    ):
        await run({"cases": [missing]}, None, None, lambda rows: None)
    model.assert_not_called()
