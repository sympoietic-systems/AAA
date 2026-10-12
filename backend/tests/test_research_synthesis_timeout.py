"""V138: synthesis has its own frozen attempt budget, not a stale-lock bypass."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from backend.modules.provider_attempts import AttemptBudgetExceeded, current_scope, new_request_scope
from backend.services.research.provider_observation import generate_unified, observe_provider_calls
from backend.services.research.provider_policy import ProviderPolicy
from backend.storage.research_receipts import ResearchActionReceipt


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "phase,legacy,expected", [("synthesizing", False, 300), ("planning", False, 60), ("synthesizing", True, 60)]
)
async def test_v138_timeout_applies_to_direct_calls_and_nested_request_factory(phase, legacy, expected):
    policy = ProviderPolicy().freeze()
    if legacy:
        policy.pop("synthesis_attempt_timeout_seconds")
    receipt = ResearchActionReceipt.model_construct(task_id="task", action_id="action", kind=phase)
    repo = MagicMock()
    repo.cost_ceiling.return_value = None
    observed = []

    class Provider:
        async def generate(self, **kwargs):
            observed.append(current_scope().timeout_seconds)
            return {"content": "ok"}

    with observe_provider_calls(receipt, repo, policy):
        scope = new_request_scope()
        assert scope.timeout_seconds == expected
        assert scope.deadline == datetime.fromisoformat(policy["deadline"])
        await generate_unified(Provider(), user_prompt="test")
    assert observed == [expected]


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["synthesizing", "planning"])
async def test_v138_slow_report_survives_short_general_attempt_budget(phase):
    policy = ProviderPolicy(attempt_timeout_seconds=0.01, synthesis_attempt_timeout_seconds=0.2).freeze()
    receipt = ResearchActionReceipt.model_construct(task_id="task", action_id="action", kind=phase)
    repo = MagicMock()
    repo.cost_ceiling.return_value = None

    class Provider:
        async def generate(self, **kwargs):
            await asyncio.sleep(0.05)
            return {"content": "report"}

    with observe_provider_calls(receipt, repo, policy):
        if phase == "synthesizing":
            assert (await generate_unified(Provider(), user_prompt="test"))["content"] == "report"
        else:
            with pytest.raises(TimeoutError):
                await generate_unified(Provider(), user_prompt="test")


@pytest.mark.asyncio
async def test_v138_parent_deadline_still_caps_long_synthesis_budget():
    policy = ProviderPolicy(synthesis_attempt_timeout_seconds=300).freeze()
    policy["deadline"] = (datetime.now(UTC) + timedelta(seconds=0.01)).isoformat()
    receipt = ResearchActionReceipt.model_construct(task_id="task", action_id="action", kind="synthesizing")
    repo = MagicMock()
    repo.cost_ceiling.return_value = None

    class Provider:
        async def generate(self, **kwargs):
            await asyncio.sleep(0.1)
            return {"content": "late report"}

    with observe_provider_calls(receipt, repo, policy), pytest.raises((TimeoutError, AttemptBudgetExceeded)):
        await generate_unified(Provider(), user_prompt="test")
