import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.services.research.provider_observation import generate_unified, observe_provider_calls
from backend.storage.research_receipts import ResearchActionReceipt


def receipt(action_id):
    return ResearchActionReceipt(
        action_id=action_id,
        task_id="task",
        kind="planning",
        intent="fixture",
        input_version="input",
        rationale="test",
        budget_reserved=0,
        contract_hash="contract",
        policy_hash="policy",
    ).transition("running", datetime.now(UTC))


@pytest.mark.asyncio
async def test_provider_scopes_are_isolated_under_concurrent_calls():
    async def run(action_id):
        provider = SimpleNamespace(
            provider_name="fixture",
            generate=AsyncMock(
                return_value={
                    "content": action_id,
                    "provider_used": "observed",
                    "model": "fixture",
                    "finish_reason": "stop",
                }
            ),
        )
        with observe_provider_calls(receipt(action_id)) as records:
            await asyncio.sleep(0)
            await generate_unified(provider, user_prompt="fixture")
        assert len(records) == 1 and records[0].action_id == action_id
        assert records[0].provider == "observed"
        return records[0].request_id

    first, second = await asyncio.gather(run("first"), run("second"))
    assert first != second


@pytest.mark.asyncio
async def test_truncation_and_missing_telemetry_preserve_observations():
    provider = SimpleNamespace(
        provider_name="fixture",
        generate=AsyncMock(
            side_effect=[
                {"content": "partial", "finish_reason": "length", "usage": {"completion_tokens": 1}},
                {"content": "unknown"},
            ]
        ),
    )
    with observe_provider_calls(receipt("action")) as records:
        await generate_unified(provider, user_prompt="fixture")
        await generate_unified(provider, user_prompt="fixture")
    assert records[0].truncated is True and records[0].outcome == "partial"
    assert records[1].truncated is None and records[1].usage is None
    assert records[1].finish_reason is None and records[1].known_cost_usd is None


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [ValueError("private error"), asyncio.CancelledError()])
async def test_failed_or_cancelled_provider_is_observed_without_exception_content(error):
    provider = SimpleNamespace(provider_name="fixture", generate=AsyncMock(side_effect=error))
    with observe_provider_calls(receipt("action")) as records, pytest.raises(type(error)):
        await generate_unified(provider, user_prompt="private prompt")
    assert records[0].outcome == ("cancelled" if isinstance(error, asyncio.CancelledError) else "failed")
    assert "private" not in records[0].model_dump_json()


@pytest.mark.asyncio
async def test_disabled_scope_preserves_provider_behavior():
    provider = SimpleNamespace(provider_name="fixture", generate=AsyncMock(return_value={"content": "original"}))
    with observe_provider_calls(None) as records:
        assert (await generate_unified(provider, user_prompt="fixture"))["content"] == "original"
    assert records == []
