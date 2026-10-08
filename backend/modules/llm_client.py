"""Compatibility facade for LLM providers, pooling, parsing, and pipeline integration."""

import asyncio
from typing import Any, cast

from backend.modules.base import ProcessingModule
from backend.modules.llm_http import OpenAICompatibleProvider, OpenRouterProvider
from backend.modules.llm_parsing import _format_context, _parse_json_safely, generate_unified
from backend.modules.llm_pool import KeyManager, ModelPoolProvider
from backend.modules.llm_protocol import (
    BaseLLMProvider,
    EmptyTruncatedCompletionError,
    LLMMessage,
    LLMResult,
    ProviderResponseError,
    RateLimitError,
)
from backend.utils.belief_candidate import inert_belief_history

__all__ = [
    "BaseLLMProvider",
    "EmptyTruncatedCompletionError",
    "KeyManager",
    "LLMClientModule",
    "ModelPoolProvider",
    "OpenAICompatibleProvider",
    "OpenRouterProvider",
    "ProviderResponseError",
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
        messages = [
            {**message, "content": inert_belief_history(message["content"])}
            if message["role"] == "assistant"
            or (
                message["role"] == "system"
                and any(
                    marker in message["content"]
                    for marker in (
                        "[Memory from",
                        "[Source: Nomadic Fragment",
                        "<diffractive_interference_zone>",
                    )
                )
            )
            else message
            for message in messages
        ]
        payload["messages"] = messages
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
            reasoning = recs.get("reasoning")
            if isinstance(reasoning, dict) and reasoning.get("thinking_override"):
                params["thinking_override"] = True
                params["reasoning_effort"] = reasoning.get("reasoning_effort", "high")
                recommended_max = reasoning.get("max_completion_tokens")
                if isinstance(recommended_max, int):
                    params["max_tokens"] = max(int(params.get("max_tokens", 0)), recommended_max)

        result = await self._provider.generate(messages, **params)
        payload["response"] = result["content"]
        if result.get("thinking"):
            payload["thinking"] = result["thinking"]
        if result.get("model"):
            payload["model_used"] = result["model"]
        if result.get("provider_used"):
            payload["provider_used"] = result["provider_used"]
        generation_receipt = {
            key: result[key] for key in ("request_id", "finish_reason", "truncated") if result.get(key) is not None
        }
        usage = result.get("usage")
        if isinstance(usage, dict):
            generation_receipt["usage"] = {
                key: usage[key]
                for key in ("prompt_tokens", "completion_tokens", "total_tokens")
                if isinstance(usage.get(key), int)
            }
        if isinstance(result.get("generation_controls"), dict):
            generation_receipt["generation_controls"] = result["generation_controls"]
        payload["generation_receipt"] = generation_receipt
        if result.get("truncated"):
            payload["truncated"] = result["truncated"]
        if result.get("finish_reason"):
            payload["finish_reason"] = result["finish_reason"]
        if result.get("generation_controls"):
            generation_controls = dict(result["generation_controls"])
            if recs:
                controller_requested = recs.get("requested_controls")
                if isinstance(controller_requested, dict):
                    forwarded = generation_controls.get("forwarded")
                    unsupported = generation_controls.get("unsupported")
                    accounted = set(forwarded) if isinstance(forwarded, dict) else set()
                    if isinstance(unsupported, list):
                        accounted.update(str(item) for item in unsupported)
                    generation_controls["controller_requested"] = dict(controller_requested)
                    generation_controls["not_forwarded"] = sorted(set(controller_requested) - accounted)
                recs["applied_controls"] = generation_controls
            payload["applied_controls"] = generation_controls
        return payload

    @property
    def provider(self) -> BaseLLMProvider:
        return self._provider
