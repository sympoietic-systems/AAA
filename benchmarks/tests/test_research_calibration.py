import copy
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from benchmarks.suites.research_calibration import acquire, evaluate, freeze, prepare, score, sentinels, validate_gold
from benchmarks.suites.research_selection import RecordingProvider, compare_selection


def annotated():
    packet = sentinels()
    for case in packet["cases"]:
        case["annotations"] = [
            {
                "annotator_id": "reviewer",
                "method": "human",
                "independent": True,
                "rationale": "fixture review",
                "label": case.pop("fixture_gold"),
            }
        ]
    return packet


def test_v108_prepare_reads_queries_without_survivor_sources(tmp_path):
    db = tmp_path / "history.sqlite"
    with sqlite3.connect(db) as conn:
        conn.executescript(
            "CREATE TABLE research_tasks(id TEXT,objective TEXT); CREATE TABLE research_steps(task_id TEXT,query_text TEXT);"
        )
        conn.execute("INSERT INTO research_tasks VALUES('task','objective')")
        conn.executemany("INSERT INTO research_steps VALUES('task',?)", [(f"query{i}",) for i in range(5)])
    before = db.read_bytes()
    result = prepare(db, 2)
    assert result["available_distinct_queries"] == 5
    assert len(result["cases"]) == 2
    assert all(not c["sources"] and not c["source_pool_complete"] for c in result["cases"])
    assert db.read_bytes() == before


@pytest.mark.asyncio
async def test_v108_acquire_raw_sources_before_selection_and_bound_pool():
    packet = sentinels()
    search = AsyncMock(
        return_value=[{"url": f"https://example.org/{i}", "title": "raw", "snippet": "text"} for i in range(12)]
    )
    result = await acquire(packet, search, 1)
    case = result["cases"][0]
    assert len(case["sources"]) == 10
    assert case["acquisition"]["observed_count"] == 12
    assert case["acquisition"]["raw_before_selection"]
    assert case["annotations"] == [] and not result["frozen"]
    assert search.await_count == 1


@pytest.mark.asyncio
async def test_v108_unlabeled_packets_never_call_models():
    triage = SimpleNamespace(evaluate=AsyncMock(), screen=AsyncMock())
    provider = SimpleNamespace(generate=AsyncMock())
    result = await evaluate(sentinels(), triage, provider)
    assert not result["rows"] and len(result["pending"]) == 4
    triage.screen.assert_not_called()
    provider.generate.assert_not_called()


def test_v108_freeze_requires_pool_labels_and_detects_invalid_gold():
    packet = annotated()
    frozen = freeze(packet)
    assert frozen["frozen"]
    packet["cases"][0]["source_pool_complete"] = False
    with pytest.raises(ValueError, match="raw candidate"):
        freeze(packet)
    malformed = copy.deepcopy(frozen["cases"][0])
    gold = malformed["annotations"][0]["label"]
    next(iter(gold.values()))["quality"] = {}
    with pytest.raises(ValueError, match="invalid"):
        validate_gold(malformed, gold)


@pytest.mark.asyncio
async def test_v108_frozen_mutation_rejected():
    packet = freeze(annotated())
    packet["cases"][0]["query"] = "changed"
    with pytest.raises(ValueError, match="changed"):
        await evaluate(packet, None, None)


@pytest.mark.asyncio
@pytest.mark.parametrize("indices", [[-1], [2], [0, 0], []])
async def test_v108_legacy_invalid_indices_are_fallback(indices):
    import json

    provider = SimpleNamespace(generate=AsyncMock(return_value={"content": json.dumps({"selected_indices": indices})}))
    recorder = RecordingProvider(provider, 2, 1)
    await recorder.generate([])
    assert recorder.receipt["status"] == "fallback"


@pytest.mark.asyncio
async def test_v108_axes_keep_identity_and_excluded_candidates():
    case = sentinels()["cases"][0]
    triage = SimpleNamespace(
        evaluate=AsyncMock(
            return_value={
                "status": "evaluated",
                "answers": {
                    "relevance_0": {"score": 0.1, "confidence": 0.95},
                    "quality_0": {"score": 1, "confidence": 0.95},
                    "relevance_1": {"score": 0.9, "confidence": 0.95},
                    "quality_1": {"score": 0.9, "confidence": 0.95},
                },
            }
        )
    )
    result = await compare_selection(case, triage, None, "separate_axes")
    assert result["selected_ids"] == [case["sources"][1]["id"]]
    assert result["excluded_ids"] == [case["sources"][0]["id"]]


def test_v108_repeats_do_not_increase_unique_query_count():
    case = sentinels()["cases"][0]
    row = {
        "id": case["id"],
        "gold": case["fixture_gold"],
        "selection": {"selected_ids": [case["sources"][0]["id"]], "latency_ms": 1, "receipt": {"status": "fallback"}},
    }
    result = score([row] * 3)
    assert result["unique_queries"] == 1 and result["valid_trials"] == 0
    assert result["mean_precision"] is None and result["promotion"] == "BLOCKED"
