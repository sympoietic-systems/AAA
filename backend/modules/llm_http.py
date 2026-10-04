"""HTTP-backed LLM providers."""

import asyncio
import contextlib
import logging
from collections.abc import Mapping
from typing import Any

import httpx

from backend.modules.llm_protocol import (
    BaseLLMProvider,
    EmptyTruncatedCompletionError,
    LLMMessage,
    LLMResult,
    ProviderResponseError,
    RateLimitError,
)
from backend.modules.providers.anthropic_utils import (
    build_anthropic_body,
    get_anthropic_endpoint,
    get_anthropic_headers,
    get_openai_endpoint,
    get_openai_headers,
    parse_anthropic_response,
)
from backend.modules.providers.google_utils import (
    build_google_thinking_disabled,
    sanitize_google_params,
)
from backend.modules.providers.openrouter_utils import (
    build_openrouter_provider_config,
    build_openrouter_thinking_disabled,
    clean_thinking_params,
    resolve_openrouter_provider_config,
    sanitize_openrouter_params,
)

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(BaseLLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        api_base: str,
        provider_name: str = "openai_compatible",
        default_params: LLMResult | None = None,
        thinking: bool = False,
        reasoning_effort: str = "high",
        max_retries: int = 3,
        timeout: float = 60.0,
        openrouter_provider: LLMResult | None = None,
        openrouter_providers_map: LLMResult | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._api_base = api_base.rstrip("/")
        self._name = provider_name
        self._default_params = default_params or {
            "temperature": 0.7,
            "max_tokens": 16384,
        }
        self._thinking = thinking
        self._reasoning_effort = reasoning_effort
        self._max_retries = max_retries
        self._timeout = timeout
        self._openrouter_provider = openrouter_provider
        self._openrouter_providers_map = openrouter_providers_map

    @property
    def provider_name(self) -> str:
        return self._name

    def _parse_rate_limit_headers(self, headers: Mapping[str, str]) -> LLMResult:
        return {
            "remaining": int(headers.get("x-ratelimit-remaining-requests", 0)),
            "limit": int(headers.get("x-ratelimit-limit-requests", 0)),
            "reset": headers.get("x-ratelimit-reset-requests", ""),
        }

    def _parse_message(
        self,
        message: LLMResult,
        data: LLMResult,
        *,
        request_id: str,
        http_status: int,
        generation_controls: dict[str, Any],
    ) -> LLMResult:
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
                reasoning = " ".join(d.get("text", "") for d in details if isinstance(d, dict))

        # If content is null/empty but we have reasoning, use reasoning as content
        # This happens with reasoning models that output thinking but no final answer
        if not content and reasoning:
            content = reasoning

        # Detect truncation from finish_reason
        finish_reason = None
        if "choices" in data and data["choices"]:
            finish_reason = data["choices"][0].get("finish_reason")
        elif data.get("stop_reason"):
            finish_reason = data.get("stop_reason")  # Anthropic format

        truncated = finish_reason in ("length", "max_tokens")
        if truncated:
            logger.warning(
                "LLM completion truncated: provider=%s model=%s request_id=%s finish_reason=%s content_chars=%s",
                self.provider_name,
                data.get("model", self._model),
                request_id or "unavailable",
                finish_reason,
                len(content) if isinstance(content, str) else "unknown",
            )
            if not content:
                raise EmptyTruncatedCompletionError(
                    "Provider exhausted its completion budget without returning final content"
                )

        content_type = type(content).__name__ if content is not None else "NoneType"
        content_chars = len(content) if isinstance(content, str) else None
        reasoning_chars = len(reasoning) if isinstance(reasoning, str) else None
        raw_usage = data.get("usage")
        usage: dict[str, Any] = raw_usage if isinstance(raw_usage, dict) else {}
        usage_summary = {
            key: usage.get(key)
            for key in ("prompt_tokens", "completion_tokens", "total_tokens")
            if usage.get(key) is not None
        }
        if not isinstance(content, (str, type(None))):
            logger.warning(
                "LLM completion has non-text content: provider=%s model=%s request_id=%s "
                "content_type=%s finish_reason=%s",
                self.provider_name,
                data.get("model", self._model),
                request_id or "unavailable",
                content_type,
                finish_reason or "unavailable",
            )
        if not isinstance(content, str) or not content.strip():
            logger.warning(
                "LLM completion has no visible text: provider=%s model=%s request_id=%s "
                "http_status=%d content_type=%s reasoning_chars=%s finish_reason=%s usage=%s",
                self.provider_name,
                data.get("model", self._model),
                request_id or "unavailable",
                http_status,
                content_type,
                reasoning_chars,
                finish_reason or "unavailable",
                usage_summary,
            )
        logger.info(
            "LLM completion received: provider=%s requested_model=%s response_model=%s "
            "request_id=%s http_status=%d finish_reason=%s truncated=%s "
            "content_chars=%s reasoning_chars=%s usage=%s controls=%s",
            self.provider_name,
            self._model,
            data.get("model", self._model),
            request_id or "unavailable",
            http_status,
            finish_reason or "unavailable",
            truncated,
            content_chars if content_chars is not None else "unknown",
            reasoning_chars if reasoning_chars is not None else "unknown",
            usage_summary,
            generation_controls,
        )

        return {
            "content": content or "",
            "reasoning": reasoning,
            "thinking": reasoning if reasoning else None,
            "model": data.get("model", self._model),
            "provider_used": self.provider_name,
            "raw_message": message,
            "truncated": truncated,
            "finish_reason": finish_reason,
        }

    async def _request_with_retry(self, body: LLMResult) -> LLMResult:
        is_anthropic = "anthropic" in self._api_base
        url = get_anthropic_endpoint(self._api_base) if is_anthropic else get_openai_endpoint(self._api_base)
        headers = get_anthropic_headers(self._api_key) if is_anthropic else get_openai_headers(self._api_key)

        last_error = None
        for attempt in range(self._max_retries + 1):
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                try:
                    response = await client.post(
                        url,
                        headers=headers,
                        json=body,
                    )
                except httpx.RequestError as e:
                    last_error = e
                    if attempt < self._max_retries:
                        await asyncio.sleep(min(2**attempt, 30))
                        continue
                    raise

                if response.status_code == 429:
                    rate_info = self._parse_rate_limit_headers(response.headers)
                    retry_after = int(response.headers.get("retry-after", 0))
                    if retry_after == 0:
                        retry_after = min(2**attempt, 30)

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
                try:
                    data = response.json()
                except ValueError as exc:
                    request_id = (
                        response.headers.get("x-request-id") or response.headers.get("request-id") or "unavailable"
                    )
                    logger.error(
                        "LLM provider returned invalid JSON: provider=%s model=%s request_id=%s "
                        "http_status=%d content_type=%s response_bytes=%d",
                        self.provider_name,
                        self._model,
                        request_id,
                        response.status_code,
                        response.headers.get("content-type", "unavailable"),
                        len(response.content),
                    )
                    raise ProviderResponseError("Provider returned invalid JSON") from exc

                request_id = (
                    response.headers.get("x-request-id")
                    or response.headers.get("request-id")
                    or (data.get("id") if isinstance(data, dict) else None)
                    or "unavailable"
                )

                if is_anthropic:
                    message = parse_anthropic_response(data)
                else:
                    choices = data.get("choices") if isinstance(data, dict) else None
                    if not isinstance(choices, list) or not choices:
                        response_keys = sorted(data) if isinstance(data, dict) else []
                        logger.error(
                            "LLM provider response missing choices: provider=%s model=%s "
                            "request_id=%s http_status=%d response_keys=%s",
                            self.provider_name,
                            self._model,
                            request_id,
                            response.status_code,
                            response_keys,
                        )
                        raise ProviderResponseError(
                            "Provider response missing completion choices "
                            f"(keys={response_keys}, request_id={request_id})"
                        )
                    first_choice = choices[0]
                    if not isinstance(first_choice, dict) or not isinstance(first_choice.get("message"), dict):
                        logger.error(
                            "LLM provider response has invalid first choice: provider=%s model=%s "
                            "request_id=%s http_status=%d choice_type=%s",
                            self.provider_name,
                            self._model,
                            request_id,
                            response.status_code,
                            type(first_choice).__name__,
                        )
                        raise ProviderResponseError("Provider response has an invalid completion choice")
                    message = first_choice["message"]

                return self._parse_message(
                    message,
                    data,
                    request_id=request_id,
                    http_status=response.status_code,
                    generation_controls={
                        key: body[key]
                        for key in (
                            "temperature",
                            "top_p",
                            "presence_penalty",
                            "frequency_penalty",
                            "max_tokens",
                            "reasoning_effort",
                        )
                        if key in body
                    },
                )

        raise last_error or RuntimeError("All retries exhausted")

    async def generate(self, messages: list[LLMMessage], **params: Any) -> LLMResult:
        requested_controls = {
            key: value
            for key, value in params.items()
            if key
            in {
                "temperature",
                "top_p",
                "presence_penalty",
                "frequency_penalty",
                "max_tokens",
                "reasoning_effort",
                "thinking_override",
            }
        }
        merged_params = {**self._default_params, **params}

        is_anthropic = "anthropic" in self._api_base
        is_google = "google" in self.provider_name.lower() or "googleapis.com" in self._api_base
        is_openrouter = "openrouter" in self.provider_name.lower() or "openrouter.ai" in self._api_base
        is_nvidia = "nvidia" in self.provider_name.lower() or "integrate.api.nvidia.com" in self._api_base

        # ── Thinking / reasoning configuration ────────────────────────
        thinking_override = merged_params.pop("thinking_override", None)
        use_thinking = self._thinking if thinking_override is None else bool(thinking_override)

        # ── Outbound safety clamping: prevent thesaurus-vomit logit degeneration ─
        if "presence_penalty" in merged_params and merged_params["presence_penalty"] is not None:
            with contextlib.suppress(ValueError, TypeError):
                merged_params["presence_penalty"] = max(-2.0, min(0.6, float(merged_params["presence_penalty"])))
        if "frequency_penalty" in merged_params and merged_params["frequency_penalty"] is not None:
            with contextlib.suppress(ValueError, TypeError):
                merged_params["frequency_penalty"] = max(-2.0, min(0.4, float(merged_params["frequency_penalty"])))

        # ── Provider-specific parameter sanitization ──────────────────
        if is_google:
            merged_params = sanitize_google_params(merged_params)
        elif is_openrouter:
            merged_params = sanitize_openrouter_params(merged_params, use_thinking=use_thinking)
        elif is_anthropic:
            merged_params.pop("presence_penalty", None)
            merged_params.pop("frequency_penalty", None)
            merged_params.pop("response_format", None)

        # ── Build request body ────────────────────────────────────────
        body: dict[str, Any]
        if is_anthropic:
            system_prompt = ""
            for m in messages:
                if m.get("role") == "system":
                    system_prompt += m.get("content", "") + "\n"
            body = build_anthropic_body(
                self._model,
                messages,
                system_prompt.strip(),
                merged_params.get("max_tokens", 4096),
            )
        else:
            body = {"model": self._model, "messages": messages}
            if merged_params.get("max_tokens"):
                body["max_tokens"] = merged_params["max_tokens"]

        if use_thinking:
            if is_anthropic:
                body["thinking"] = {"type": "enabled", "budget_tokens": 1024}
            elif is_nvidia:
                body["chat_template_kwargs"] = {"enable_thinking": True}
            else:
                body["thinking"] = {"type": "enabled"}
                body["reasoning_effort"] = merged_params.pop("reasoning_effort", self._reasoning_effort)
            body.update(merged_params)
        else:
            if is_openrouter:
                build_openrouter_thinking_disabled(body)
            elif is_google:
                build_google_thinking_disabled(body)
            elif is_anthropic:
                body["thinking"] = {"type": "disabled"}
            elif is_nvidia:
                body["chat_template_kwargs"] = {"enable_thinking": False}
            else:
                body["thinking"] = {"type": "disabled"}

            clean_thinking_params(merged_params)
            body.update(merged_params)

        # ── OpenRouter provider routing preferences ────────────────────
        or_provider = (
            body.pop("openrouter_provider", None)
            or merged_params.pop("openrouter_provider", None)
            or self._openrouter_provider
        )
        or_map = (
            body.pop("openrouter_providers_map", None)
            or merged_params.pop("openrouter_providers_map", None)
            or self._openrouter_providers_map
        )
        if is_openrouter:
            resolved_or_provider = resolve_openrouter_provider_config(
                self._model, openrouter_provider=or_provider, providers_map=or_map
            )
            if resolved_or_provider:
                build_openrouter_provider_config(body, resolved_or_provider)

        result = await self._request_with_retry(body)
        forwarded: dict[str, Any] = {}
        unsupported: list[str] = []
        for key in requested_controls:
            body_key = "thinking" if key == "thinking_override" else key
            if body_key in body:
                forwarded[key] = body[body_key]
            else:
                unsupported.append(key)
        result["generation_controls"] = {
            "requested": requested_controls,
            "forwarded": forwarded,
            "unsupported": unsupported,
            "status": "forwarded" if forwarded else "unsupported",
        }
        return result

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
        default_params: LLMResult | None = None,
        thinking: bool = False,
        reasoning_effort: str = "high",
        max_retries: int = 3,
        timeout: float = 60.0,
        openrouter_provider: LLMResult | None = None,
        openrouter_providers_map: LLMResult | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            api_base=api_base,
            provider_name="openrouter",
            default_params=default_params,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
            max_retries=max_retries,
            timeout=timeout,
            openrouter_provider=openrouter_provider,
            openrouter_providers_map=openrouter_providers_map,
        )
