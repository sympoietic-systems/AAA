from abc import ABC, abstractmethod
from typing import Optional

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from .base import ProcessingModule

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    def __init__(self, message: str, retry_after: int = 0, remaining: int = 0, limit: int = 0):
        super().__init__(message)
        self.retry_after = retry_after
        self.remaining = remaining
        self.limit = limit


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(
        self, messages: list[dict], **params
    ) -> dict: ...

    @abstractmethod
    async def validate_connection(self) -> bool: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...


class OpenAICompatibleProvider(BaseLLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        api_base: str,
        provider_name: str = "openai_compatible",
        default_params: Optional[dict] = None,
        thinking: bool = False,
        reasoning_effort: str = "high",
        max_retries: int = 3,
    ):
        self._api_key = api_key
        self._model = model
        self._api_base = api_base.rstrip("/")
        self._name = provider_name
        self._default_params = default_params or {
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        self._thinking = thinking
        self._reasoning_effort = reasoning_effort
        self._max_retries = max_retries

    @property
    def provider_name(self) -> str:
        return self._name

    def _parse_rate_limit_headers(self, headers) -> dict:
        return {
            "remaining": int(headers.get("x-ratelimit-remaining-requests", 0)),
            "limit": int(headers.get("x-ratelimit-limit-requests", 0)),
            "reset": headers.get("x-ratelimit-reset-requests", ""),
        }

    def _parse_message(self, message: dict, data: dict) -> dict:
        """Parse response message into consistent format.

        Handles both thinking and non-thinking models:
        - Non-thinking: content has the response
        - Thinking models: content may be null, reasoning has the trace
        - OpenRouter free models: various formats (reasoning, reasoning_details, etc.)
        """
        content = message.get("content")
        reasoning = message.get("reasoning") or message.get("reasoning_content") or ""

        # Handle OpenRouter reasoning_details array
        if not reasoning and message.get("reasoning_details"):
            details = message["reasoning_details"]
            if isinstance(details, list):
                reasoning = " ".join(
                    d.get("text", "") for d in details if isinstance(d, dict)
                )

        # If content is null/empty but we have reasoning, use reasoning as content
        # This happens with reasoning models that output thinking but no final answer
        if not content and reasoning:
            content = reasoning

        return {
            "content": content or "",
            "reasoning": reasoning,
            "thinking": reasoning if reasoning else None,
            "model": data.get("model", self._model),
            "raw_message": message,
        }

    async def _request_with_retry(self, body: dict) -> dict:
        last_error = None
        for attempt in range(self._max_retries + 1):
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self._api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/aaa",
                        "X-Title": "AAA",
                    },
                    json=body,
                )

                if response.status_code == 429:
                    rate_info = self._parse_rate_limit_headers(response.headers)
                    retry_after = int(response.headers.get("retry-after", 0))
                    if retry_after == 0:
                        retry_after = min(2 ** attempt, 30)

                    logger.warning(
                        f"Rate limited (attempt {attempt + 1}/{self._max_retries + 1}). "
                        f"Remaining: {rate_info['remaining']}/{rate_info['limit']}. "
                        f"Retry after: {retry_after}s"
                    )

                    if attempt < self._max_retries:
                        await asyncio.sleep(retry_after)
                        continue

                    raise RateLimitError(
                        f"Rate limit exceeded. {rate_info['remaining']}/{rate_info['limit']} remaining.",
                        retry_after=retry_after,
                        remaining=rate_info["remaining"],
                        limit=rate_info["limit"],
                    )

                response.raise_for_status()
                data = response.json()
                message = data["choices"][0]["message"]
                return self._parse_message(message, data)

        raise last_error or RuntimeError("All retries exhausted")

    async def generate(self, messages: list[dict], **params) -> dict:
        merged_params = {**self._default_params, **params}
        body: dict = {
            "model": self._model,
            "messages": messages,
        }

        if self._thinking:
            body["thinking"] = {"type": "enabled"}
            body["reasoning_effort"] = self._reasoning_effort
        else:
            body.update(merged_params)

        return await self._request_with_retry(body)

    async def validate_connection(self) -> bool:
        try:
            await self.generate(
                [{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return True
        except Exception:
            return False


class OpenRouterProvider(OpenAICompatibleProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "deepseek/deepseek-chat",
        api_base: str = "https://openrouter.ai/api/v1",
        default_params: Optional[dict] = None,
        thinking: bool = False,
        reasoning_effort: str = "high",
        max_retries: int = 3,
    ):
        super().__init__(
            api_key=api_key,
            model=model,
            api_base=api_base,
            provider_name="openrouter",
            default_params=default_params,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
            max_retries=max_retries,
        )


class ModelPoolProvider(BaseLLMProvider):
    """Provider that tries models from a pool in order, with rate-limit fallback.

    When one model returns a 429 rate limit, the next model is tried.
    Exhausted models are retried after a cooldown period.
    """

    def __init__(
        self,
        api_key: str,
        models: list[str],
        fallback_model: str = "openrouter/free",
        api_base: str = "https://openrouter.ai/api/v1",
        cooldown_seconds: int = 60,
        max_retries_per_model: int = 0,
    ):
        self._api_key = api_key
        self._models = models
        self._fallback_model = fallback_model
        self._api_base = api_base
        self._cooldown_seconds = cooldown_seconds
        self._max_retries_per_model = max_retries_per_model
        self._exhausted: dict[str, float] = {}
        self._last_model_used: str = ""

    @property
    def provider_name(self) -> str:
        return f"model_pool({len(self._models)} models)"

    def _all_models(self) -> list[str]:
        models = list(self._models)
        if self._fallback_model and self._fallback_model not in models:
            models.append(self._fallback_model)
        return models

    def _is_exhausted(self, model: str) -> bool:
        import time
        until = self._exhausted.get(model, 0)
        if until and time.time() < until:
            return True
        if until:
            del self._exhausted[model]
        return False

    def _mark_exhausted(self, model: str):
        import time
        self._exhausted[model] = time.time() + self._cooldown_seconds

    def _create_provider(self, model: str) -> OpenAICompatibleProvider:
        return OpenAICompatibleProvider(
            api_key=self._api_key,
            model=model,
            api_base=self._api_base,
            provider_name="model_pool",
            max_retries=self._max_retries_per_model,
        )

    async def generate(self, messages: list[dict], **params) -> dict:
        errors = []
        for model in self._all_models():
            if self._is_exhausted(model):
                continue

            provider = self._create_provider(model)
            try:
                result = await provider.generate(messages, **params)
                self._last_model_used = model
                return result
            except RateLimitError as e:
                self._mark_exhausted(model)
                errors.append(f"{model}: rate limited")
                logger.warning("Model %s rate limited, moving to next in pool", model)
            except Exception as e:
                errors.append(f"{model}: {e}")
                logger.warning("Model %s failed: %s", model, e)

        error_msg = f"All models in pool exhausted. Errors: {'; '.join(errors)}"
        logger.error(error_msg)
        raise RateLimitError(error_msg)

    async def validate_connection(self) -> bool:
        try:
            await self.generate(
                [{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return True
        except Exception:
            return False


class LLMClientModule(ProcessingModule):
    def __init__(self, provider: BaseLLMProvider):
        self._provider = provider

    @property
    def name(self) -> str:
        return "llm_client"

    def validate(self) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        messages = payload.get("messages", [])
        payload["context_sent"] = _format_context(messages)
        params = {
            k: v
            for k, v in payload.items()
            if k in ("temperature", "max_tokens", "top_p", "presence_penalty")
        }
        result = await self._provider.generate(messages, **params)
        payload["response"] = result["content"]
        if result.get("thinking"):
            payload["thinking"] = result["thinking"]
        return payload

    @property
    def provider(self) -> BaseLLMProvider:
        return self._provider


def _format_context(messages: list[dict]) -> str:
    lines: list[str] = []
    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, list):
            text_parts = [p.get("text", "") for p in content if p.get("type") == "text"]
            content = " ".join(text_parts)
        lines.append(f"[{i}] {role}: {content}")
        lines.append("")
    return "\n".join(lines)
