import json
from unittest.mock import AsyncMock

import httpx
import pytest

from benchmarks.suites.calibration_contract import reviewed_label
from benchmarks.suites.research_labeling import render, run, validate


def packet():
    return {
        "cases": [
            {
                "id": "q1",
                "objective": "Objective",
                "query": "query",
                "annotations": [],
                "sources": [
                    {"id": "s1", "url": "https://example.org", "title": "<script>bad</script>", "snippet": "data"}
                ],
            }
        ]
    }


def labels():
    return {
        "s1": {
            "relevant": True,
            "quality": "unknown",
            "contrary": False,
            "injection": False,
            "rationale": "Snippet cannot establish quality",
            "confidence": 0.5,
        }
    }


@pytest.mark.asyncio
async def test_labels_are_provisional_and_cannot_pass_independent_gate():
    original = packet()
    response = httpx.Response(
        200,
        request=httpx.Request("POST", "https://integrate.api.nvidia.com"),
        json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"labels": labels()})}}]},
    )
    result, receipts = await run(original, AsyncMock(post=AsyncMock(return_value=response)))
    assert original["cases"][0]["annotations"] == []
    assert reviewed_label(result["cases"][0]) == (None, "independent_labels_required")
    assert receipts[0]["status"] == "labeled_provisional"
    assert receipts[0]["known_cost_usd"] is None
    assert result["promotion"] == "BLOCKED" and not result["frozen"]
    assert "<script>" not in render(result)


@pytest.mark.parametrize("change", [{"relevant": 1}, {"confidence": 2}, {"quality": "verified"}, {"rationale": ""}])
def test_invalid_labels_rejected(change):
    values = labels()
    values["s1"].update(change)
    with pytest.raises(ValueError):
        validate(values, packet()["cases"][0]["sources"])


@pytest.mark.asyncio
async def test_truncation_does_not_create_fabricated_labels():
    response = httpx.Response(
        200,
        request=httpx.Request("POST", "https://integrate.api.nvidia.com"),
        json={"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]},
    )
    result, receipts = await run(packet(), AsyncMock(post=AsyncMock(return_value=response)))
    assert not result["cases"][0]["annotations"]
    assert receipts[0]["status"] == "failed"


def test_missing_source_labels_rejected():
    with pytest.raises(ValueError, match="coverage"):
        validate({}, packet()["cases"][0]["sources"])


@pytest.mark.asyncio
async def test_resume_reuses_only_same_model_and_input():
    response = httpx.Response(
        200,
        request=httpx.Request("POST", "https://integrate.api.nvidia.com"),
        json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"labels": labels()})}}]},
    )
    first, _ = await run(packet(), AsyncMock(post=AsyncMock(return_value=response)))
    client = AsyncMock()
    second, receipts = await run(first, client)
    client.post.assert_not_called()
    assert receipts[0]["status"] == "reused_provisional"
    assert len(second["cases"][0]["annotations"]) == 1
    first["cases"][0]["sources"][0]["snippet"] = "changed input"
    client.post.return_value = response
    await run(first, client)
    client.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_http_failure_checkpoint_records_status_without_body_or_fake_labels():
    response = httpx.Response(
        429,
        request=httpx.Request("POST", "https://integrate.api.nvidia.com"),
        text="secret response must not enter receipts",
    )
    checkpoints = []
    result, receipts = await run(
        packet(), AsyncMock(post=AsyncMock(return_value=response)), checkpoint=lambda p, r: checkpoints.append((p, r))
    )
    assert receipts[0]["http_status"] == 429
    assert "secret" not in json.dumps(receipts)
    assert checkpoints and not result["cases"][0]["annotations"]
