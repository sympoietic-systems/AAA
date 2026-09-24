"""Compatibility facade for LLM providers, pooling, parsing, and pipeline integration."""

import asyncio
from typing import Any, cast

from backend.modules.base import ProcessingModule
from backend.modules.llm_http import OpenAICompatibleProvider, OpenRouterProvider
from backend.modules.llm_parsing import _format_context, _parse_json_safely, generate_unified
from backend.modules.llm_pool import KeyManager, ModelPoolProvider
from backend.modules.llm_protocol import BaseLLMProvider, LLMMessage, LLMResult, RateLimitError

__all__ = [
    "BaseLLMProvider",
    "KeyManager",
    "LLMClientModule",
    "ModelPoolProvider",
    "OpenAICompatibleProvider",
    "OpenRouterProvider",
    "RateLimitError",
    "_parse_json_safely",
    "asyncio",
    "generate_unified",
]


class LLMClientModule(ProcessingModule):
    def __init__(self, provider: BaseLLMProvider):
        self._provider = provider

    @property
    def name(self) -> str:
        return "llm_client"

    def validate(self) -> bool:
        return True

    async def process(self, payload: LLMResult) -> LLMResult:
        messages = cast(list[LLMMessage], payload.get("messages", []))
        payload["context_sent"] = _format_context(messages)

        params: dict[str, Any] = {}
        for k in ("temperature", "max_tokens", "top_p"):
            v = payload.get(k)
            if v is not None:
                params[k] = v

        recs = payload.get("homeostatic_recommendations")
        if recs:
            for param in ("temperature", "presence_penalty", "frequency_penalty"):
                rec = recs.get(param)
                if isinstance(rec, dict) and "value" in rec:
                    val = rec["value"]
                    if param == "temperature" or val > 0.0:
                        params[param] = val

        result = await self._provider.generate(messages, **params)
        payload["response"] = result["content"]
        if result.get("thinking"):
            payload["thinking"] = result["thinking"]
        if result.get("model"):
            payload["model_used"] = result["model"]
        if result.get("provider_used"):
            payload["provider_used"] = result["provider_used"]
        if result.get("truncated"):
            payload["truncated"] = result["truncated"]
        if result.get("finish_reason"):
            payload["finish_reason"] = result["finish_reason"]
        return payload

    @property
    def provider(self) -> BaseLLMProvider:
        return self._provider
