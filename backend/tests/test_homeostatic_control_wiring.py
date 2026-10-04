from typing import Any

import pytest

from backend.modules.llm_client import LLMClientModule
from backend.modules.llm_protocol import BaseLLMProvider, LLMMessage, LLMResult


class RecordingProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.params: dict[str, Any] = {}

    @property
    def provider_name(self) -> str:
        return "recording"

    async def validate_connection(self) -> bool:
        return True

    async def generate(self, messages: list[LLMMessage], **params: Any) -> LLMResult:
        self.params = params
        return {
            "content": "response",
            "generation_controls": {
                "requested": params,
                "forwarded": params,
                "unsupported": [],
                "status": "forwarded",
            },
        }


@pytest.mark.asyncio
async def test_v43_llm_client_forwards_critical_reasoning_controls():
    provider = RecordingProvider()
    module = LLMClientModule(provider)
    recommendations = {
        "temperature": {"value": 0.88},
        "presence_penalty": {"value": 0.3},
        "frequency_penalty": {"value": 0.2},
        "reasoning": {
            "thinking_override": True,
            "reasoning_effort": "high",
            "max_completion_tokens": 2400,
        },
        "requested_controls": {
            "temperature": 0.88,
            "presence_penalty": 0.3,
            "frequency_penalty": 0.2,
            "max_tokens": 2400,
            "reasoning_effort": "high",
            "thinking_override": True,
        },
    }

    result = await module.process(
        {
            "messages": [{"role": "user", "content": "break the loop"}],
            "max_tokens": 1200,
            "homeostatic_recommendations": recommendations,
        }
    )

    assert provider.params["thinking_override"] is True
    assert provider.params["reasoning_effort"] == "high"
    assert provider.params["max_tokens"] == 2400
    assert result["applied_controls"]["status"] == "forwarded"
    assert result["applied_controls"]["controller_requested"] == recommendations["requested_controls"]
    assert result["applied_controls"]["not_forwarded"] == []
    assert recommendations["applied_controls"]["status"] == "forwarded"


@pytest.mark.asyncio
async def test_homeostatic_regulator_clamps_presence_and_frequency_penalties():
    from backend.modules.sensory.homeostatic_regulator import HomeostaticRegulatorModule

    regulator = HomeostaticRegulatorModule()
    # Simulate high collapse pressure and low entropy that previously surged to 2.0
    payload = {
        "metrics": {
            "pairwise_similarity": 1.0,
            "conceptual_novelty": 0.0,
            "agent_self_divergence": 0.0,
            "glitch_fidelity": 0.1,
            "conversation_vitality": 0.1,
            "rolling_entropy": 0.01,
            "collapse_pressure": 0.99,
            "collapse_pressure_streak": 5,
        },
        "max_tokens": 1000,
        "messages": [],
    }

    result = await regulator.process(payload)
    recs = result["homeostatic_recommendations"]
    assert recs is not None

    # Presence penalty should be clamped to at most 0.6
    assert recs["presence_penalty"]["value"] <= 0.6
    assert recs["presence_penalty"]["clamped"] is True

    # Frequency penalty should be clamped to at most 0.4
    assert recs["frequency_penalty"]["value"] <= 0.4
    assert recs["frequency_penalty"]["clamped"] is True


@pytest.mark.asyncio
async def test_openai_compatible_provider_safety_clamps_outbound_penalties():
    from backend.modules.llm_http import OpenAICompatibleProvider

    provider = OpenAICompatibleProvider(
        api_key="test-key",
        model="test-model",
        api_base="https://openrouter.ai/api/v1",
    )

    captured_body = {}

    async def mock_request_with_retry(body):
        nonlocal captured_body
        captured_body = body
        return {
            "content": "ok",
            "model": "test-model",
            "finish_reason": "stop",
        }

    provider._request_with_retry = mock_request_with_retry

    # Pass excessive presence and frequency penalties (e.g. 2.0)
    await provider.generate(
        [{"role": "user", "content": "hi"}],
        presence_penalty=2.0,
        frequency_penalty=1.5,
    )

    assert captured_body["presence_penalty"] <= 0.6
    assert captured_body["frequency_penalty"] <= 0.4

