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
