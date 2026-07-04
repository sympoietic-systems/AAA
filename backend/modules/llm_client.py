import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from .base import ProcessingModule
from backend.modules.providers.anthropic_utils import (
    parse_anthropic_response, build_anthropic_body,
    get_anthropic_endpoint, get_anthropic_headers,
    get_openai_endpoint, get_openai_headers,
)
from backend.modules.providers.google_utils import sanitize_google_params, build_google_thinking_enabled, build_google_thinking_disabled
from backend.modules.providers.openrouter_utils import build_openrouter_thinking_disabled, clean_thinking_params

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

    async def generate_unified(
        self,
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
        messages: Optional[list[dict]] = None,
        expect_json: bool = False,
        fallback_value: Optional[dict] = None,
        **params
    ) -> dict:
        """Standardized interface for LLM calls with robust message compilation, cleaning, and JSON parsing."""
        return await generate_unified(
            self,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            messages=messages,
            expect_json=expect_json,
            fallback_value=fallback_value,
            **params
        )



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
        timeout: float = 60.0,
    ):
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

        # Detect truncation from finish_reason
        finish_reason = None
        if "choices" in data and data["choices"]:
            finish_reason = data["choices"][0].get("finish_reason")
        elif data.get("stop_reason"):
            finish_reason = data.get("stop_reason")  # Anthropic format

        truncated = finish_reason in ("length", "max_tokens")
        if truncated:
            logger.warning(
                "Response truncated by token limit (finish_reason=%s, model=%s). "
                "Content length: %d chars. Consider increasing max_tokens.",
                finish_reason, self._model, len(content or "")
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

    async def _request_with_retry(self, body: dict) -> dict:
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
                        await asyncio.sleep(min(2 ** attempt, 30))
                        continue
                    raise

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
                
                if is_anthropic:
                    message = parse_anthropic_response(data)
                else:
                    message = data["choices"][0]["message"]
                
                return self._parse_message(message, data)

        raise last_error or RuntimeError("All retries exhausted")

    async def generate(self, messages: list[dict], **params) -> dict:
        merged_params = {**self._default_params, **params}

        is_anthropic = "anthropic" in self._api_base
        is_google = "google" in self.provider_name.lower() or "googleapis.com" in self._api_base
        is_openrouter = "openrouter" in self.provider_name.lower() or "openrouter.ai" in self._api_base

        # ── Provider-specific parameter sanitization ──────────────────
        if is_google:
            merged_params = sanitize_google_params(merged_params)
        elif is_anthropic:
            merged_params.pop("presence_penalty", None)
            merged_params.pop("frequency_penalty", None)
            merged_params.pop("response_format", None)

        # ── Build request body ────────────────────────────────────────
        if is_anthropic:
            system_prompt = ""
            for m in messages:
                if m.get("role") == "system":
                    system_prompt += m.get("content", "") + "\n"
            body = build_anthropic_body(
                self._model, messages, system_prompt.strip(),
                merged_params.get("max_tokens", 4096),
            )
        else:
            body = {"model": self._model, "messages": messages}
            if "max_tokens" in merged_params:
                body["max_tokens"] = merged_params["max_tokens"]

        # ── Thinking / reasoning configuration ────────────────────────
        thinking_override = merged_params.pop("thinking_override", None)
        use_thinking = self._thinking if thinking_override is None else bool(thinking_override)

        if use_thinking:
            if is_anthropic:
                body["thinking"] = {"type": "enabled", "budget_tokens": 1024}
            else:
                body["thinking"] = {"type": "enabled"}
                body["reasoning_effort"] = merged_params.pop("reasoning_effort", self._reasoning_effort)
        else:
            if is_openrouter:
                build_openrouter_thinking_disabled(body)
            elif is_google:
                build_google_thinking_disabled(body)
            elif is_anthropic:
                body["thinking"] = {"type": "disabled"}
            else:
                body["thinking"] = {"type": "disabled"}

            clean_thinking_params(merged_params)
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
        timeout: float = 60.0,
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
            timeout=timeout,
        )


class KeyManager:
    """Manages rotation and cooldowns for a list of API keys."""

    def __init__(self, keys: list[str], cooldown_seconds: int = 300):
        self.keys = keys
        self.cooldown_seconds = cooldown_seconds
        self._exhausted: dict[str, float] = {}

    def get_available_key(self) -> Optional[str]:
        now = time.time()
        for key in self.keys:
            until = self._exhausted.get(key, 0)
            if until and now < until:
                continue
            if key in self._exhausted:
                del self._exhausted[key]
            return key
        return None

    def mark_key_exhausted(self, key: str):
        self._exhausted[key] = time.time() + self.cooldown_seconds

    def has_keys(self) -> bool:
        return len(self.keys) > 0


class ModelPoolProvider(BaseLLMProvider):
    """Provider that tries models from a pool in order, with rate-limit and provider fallback.

    Supports 'google_router/', 'deepseek_router/', and 'openrouter_router/' prefixes to route requests to
    different providers (Google API vs DeepSeek API vs OpenRouter API) with independent API key rotation pools.
    """

    def __init__(
        self,
        api_key: str,
        models: list[str],
        fallback_model: str = "openrouter/free",
        api_base: str = "https://openrouter.ai/api/v1",
        google_keys: Optional[list[str]] = None,
        deepseek_keys: Optional[list[str]] = None,
        openrouter_keys: Optional[list[str]] = None,
        google_api_base: str = "https://generativelanguage.googleapis.com/v1beta/openai",
        deepseek_api_base: str = "https://api.deepseek.com",
        cooldown_seconds: int = 300,
        max_retries_per_model: int = 0,
        thinking: bool = False,
        reasoning_effort: str = "high",
        default_params: Optional[dict] = None,
        timeout: float = 60.0,
    ):
        self._api_key = api_key
        self._models = models
        self._fallback_model = fallback_model
        self._api_base = api_base
        self._google_api_base = google_api_base
        self._deepseek_api_base = deepseek_api_base
        self._cooldown_seconds = cooldown_seconds
        self._max_retries_per_model = max_retries_per_model
        self._thinking = thinking
        self._reasoning_effort = reasoning_effort
        self._default_params = default_params
        self._exhausted: dict[str, float] = {}
        self._last_model_used: str = ""
        self._last_model_time: float = 0.0
        self._timeout = timeout

        # Setup key managers
        self._google_key_mgr = KeyManager(google_keys or [], cooldown_seconds=cooldown_seconds)
        self._deepseek_key_mgr = KeyManager(deepseek_keys or [], cooldown_seconds=cooldown_seconds)
        
        # If openrouter_keys is empty but we have api_key, use it as fallback
        or_keys = list(openrouter_keys) if openrouter_keys else []
        if not or_keys and api_key:
            or_keys = [api_key]
        self._openrouter_key_mgr = KeyManager(or_keys, cooldown_seconds=cooldown_seconds)

    @property
    def provider_name(self) -> str:
        return f"model_pool({len(self._models)} models)"

    def _all_models(self) -> list[str]:
        models = list(self._models)
        if self._fallback_model and self._fallback_model not in models:
            models.append(self._fallback_model)
        return models

    def _is_exhausted(self, model: str) -> bool:
        until = self._exhausted.get(model, 0)
        if until and time.time() < until:
            return True
        if until:
            del self._exhausted[model]
        return False

    def _mark_exhausted(self, model: str):
        self._exhausted[model] = time.time() + self._cooldown_seconds

    def reset_exhaustion(self):
        """Clear all exhaustion timers — call on server startup."""
        self._exhausted.clear()
        self._google_key_mgr._exhausted.clear()
        self._deepseek_key_mgr._exhausted.clear()
        self._openrouter_key_mgr._exhausted.clear()
        self._last_model_used = ""
        self._last_model_time = 0.0
        logger.info("Model pool exhaustion state reset — all models and keys available.")

    def _mask_key(self, key: str) -> str:
        if not key:
            return "None"
        if len(key) <= 8:
            return "***"
        return f"{key[:4]}...{key[-4:]}"

    async def generate(self, messages: list[dict], **params) -> dict:
        errors = []
        
        now = time.time()
        models_to_try = self._all_models()
        if self._last_model_used and self._last_model_used in models_to_try:
            preferred_model = models_to_try[0]
            if self._last_model_used != preferred_model:
                if now - self._last_model_time >= self._cooldown_seconds:
                    logger.info("Fallback period expired. Resetting priority to try preferred model %s again.", preferred_model)
                    self._last_model_used = ""
                    self._last_model_time = 0.0
                else:
                    # Prioritize last working model
                    models_to_try = [self._last_model_used] + [m for m in models_to_try if m != self._last_model_used]

        for model in models_to_try:
            if self._is_exhausted(model):
                continue

            # Route model based on prefix
            if model.startswith("google_router/"):
                actual_model = model.split("google_router/", 1)[1]
                api_base = self._google_api_base
                key_mgr = self._google_key_mgr
                provider_type = "google"
            elif model.startswith("deepseek_router/"):
                actual_model = model.split("deepseek_router/", 1)[1]
                api_base = self._deepseek_api_base
                key_mgr = self._deepseek_key_mgr
                provider_type = "deepseek"
            elif model.startswith("openrouter_router/"):
                actual_model = model.split("openrouter_router/", 1)[1]
                api_base = self._api_base
                key_mgr = self._openrouter_key_mgr
                provider_type = "openrouter"
            else:
                actual_model = model
                api_base = self._api_base
                key_mgr = self._openrouter_key_mgr
                provider_type = "openrouter"

            if provider_type == "google" and not self._google_key_mgr.has_keys():
                logger.warning("Model %s has google_router/ prefix but no google API keys are configured", model)
                continue
            if provider_type == "deepseek" and not self._deepseek_key_mgr.has_keys():
                logger.warning("Model %s has deepseek_router/ prefix but no deepseek API keys are configured", model)
                continue
            if provider_type == "openrouter" and not self._openrouter_key_mgr.has_keys():
                logger.warning("Model %s routes to openrouter but no openrouter API keys are configured", model)
                continue

            success = False
            result = None
            tried_keys = set()

            while True:
                key = key_mgr.get_available_key()
                if not key or key in tried_keys:
                    break

                tried_keys.add(key)
                masked_key = self._mask_key(key)

                logger.info("Attempting model %s using provider %s with key %s", actual_model, provider_type, masked_key)

                provider = OpenAICompatibleProvider(
                    api_key=key,
                    model=actual_model,
                    api_base=api_base,
                    provider_name=f"model_pool_{provider_type}",
                    thinking=self._thinking if provider_type == "deepseek" else False,
                    reasoning_effort=self._reasoning_effort,
                    max_retries=self._max_retries_per_model,
                    default_params=self._default_params,
                    timeout=self._timeout,
                )

                try:
                    result = await provider.generate(messages, **params)
                    if self._last_model_used != model:
                        self._last_model_used = model
                        self._last_model_time = time.time()
                    success = True
                    break
                except RateLimitError as e:
                    key_mgr.mark_key_exhausted(key)
                    errors.append(f"{model} (key: {masked_key}): rate limited - {e}")
                    logger.warning("Key %s rate limited for model %s. Rotating key...", masked_key, model)
                except httpx.HTTPStatusError as e:
                    key_mgr.mark_key_exhausted(key)
                    errors.append(f"{model} (key: {masked_key}): HTTP {e.response.status_code} - {e}")
                    logger.warning("Key %s HTTP error %s for model %s. Rotating key...", masked_key, e.response.status_code, model)
                except (httpx.RequestError, TimeoutError, asyncio.TimeoutError) as e:
                    # Network timeouts are transient — retry a few times before giving up
                    timeout_retries = 2
                    for retry_num in range(timeout_retries):
                        logger.warning("Connection error '%s' on model %s with key %s. "
                                       "Waiting 10s to retry (attempt %d/%d)...",
                                       type(e).__name__, model, masked_key, retry_num + 1, timeout_retries)
                        await asyncio.sleep(10)
                        try:
                            result = await provider.generate(messages, **params)
                            if self._last_model_used != model:
                                self._last_model_used = model
                                self._last_model_time = time.time()
                            success = True
                            break
                        except (httpx.RequestError, TimeoutError, asyncio.TimeoutError):
                            continue
                        except Exception as retry_e:
                            key_mgr.mark_key_exhausted(key)
                            errors.append(f"{model} (key: {masked_key}): error after retry - {retry_e}")
                            logger.warning("Retry failed for model %s with key %s. Rotating key...", model, masked_key)
                            break
                    if success:
                        break
                    if not success:
                        key_mgr.mark_key_exhausted(key)
                        errors.append(f"{model} (key: {masked_key}): connection timeout after {timeout_retries} retries - {e}")
                        logger.warning("All timeout retries failed for model %s with key %s. Rotating key...", model, masked_key)
                except Exception as e:
                    key_mgr.mark_key_exhausted(key)
                    errors.append(f"{model} (key: {masked_key}): {e}")
                    logger.warning("Key %s encountered error %s for model %s. Rotating key...", masked_key, type(e).__name__, model)

            if success:
                return result

            self._mark_exhausted(model)
            logger.warning("All keys exhausted for model %s. Moving to next in pool.", model)

        if not errors:
            logger.error("Model pool: no models were attempted. models_to_try=%s, exhausted=%s",
                         models_to_try, list(self._exhausted.keys()))
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

        params: dict = {}
        for k in ("temperature", "max_tokens", "top_p"):
            v = payload.get(k)
            if v is not None:
                params[k] = v

        recs = payload.get("homeostatic_recommendations")
        if recs:
            for param in ("temperature",):
                rec = recs.get(param)
                if isinstance(rec, dict) and "value" in rec:
                    params[param] = rec["value"]

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


def _parse_json_safely(text: str) -> dict:
    import json
    import re

    # 1. Clean think tags
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

    # 2. Extract starting from first {
    first_brace = cleaned.find("{")
    if first_brace == -1:
        return json.loads(cleaned)
    
    json_part = cleaned[first_brace:]

    # 3. Helper to clean control characters and commas inside string
    def sanitize(s: str) -> str:
        s = re.sub(r',\s*([\]\}])', r'\1', s)
        chars = []
        in_string = False
        escape = False
        for char in s:
            if char == '"' and not escape:
                in_string = not in_string
                chars.append(char)
            elif in_string:
                if char == '\n':
                    chars.append('\\n')
                elif char == '\t':
                    chars.append('\\t')
                elif char == '\r':
                    chars.append('\\r')
                else:
                    chars.append(char)
            else:
                chars.append(char)
                
            if char == '\\' and in_string:
                escape = not escape
            else:
                escape = False
        return "".join(chars)

    # 4. Helper to auto-close open structures in truncated string
    def auto_close(s: str) -> str:
        stack = []
        in_string = False
        escape = False
        for char in s:
            if char == '"' and not escape:
                in_string = not in_string
            elif in_string:
                if char == '\\':
                    escape = not escape
                else:
                    escape = False
            else:
                if char in ('{', '['):
                    stack.append(char)
                elif char in ('}', ']'):
                    if stack:
                         top = stack[-1]
                         if (char == '}' and top == '{') or (char == ']' and top == '['):
                             stack.pop()
        
        repaired = s
        if in_string:
            repaired += '"'
        for item in reversed(stack):
            if item == '{':
                repaired += '}'
            elif item == '[':
                repaired += ']'
        return repaired

    # Try standard sanitize and parse
    sanitized = sanitize(json_part)
    try:
        return json.loads(sanitized)
    except Exception:
        pass

    # Try auto-closing and parsing
    try:
        closed = auto_close(sanitized)
        return json.loads(closed)
    except Exception:
        pass

    # Try finding last brace if any and slice/parse
    last_brace = sanitized.rfind("}")
    if last_brace != -1:
        try:
            return json.loads(sanitized[:last_brace + 1])
        except Exception:
            pass

    return json.loads(cleaned)


async def generate_unified(
    provider,
    system_prompt: Optional[str] = None,
    user_prompt: Optional[str] = None,
    messages: Optional[list[dict]] = None,
    expect_json: bool = False,
    fallback_value: Optional[dict] = None,
    thinking_override: Optional[bool] = None,
    **params
) -> dict:
    """Standardized wrapper for LLM calls with automatic message list construction, cleaning, and JSON parsing."""
    import re

    # 1. Compile messages list
    formatted_messages = []
    if messages:
        formatted_messages = list(messages)
        if system_prompt:
            # Prepend system prompt if not already first message
            if not (formatted_messages and formatted_messages[0].get("role") == "system"):
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})
    else:
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        if user_prompt:
            formatted_messages.append({"role": "user", "content": user_prompt})

    # 2. Invoke the provider
    try:
        if thinking_override is not None:
            params["thinking_override"] = thinking_override
        res = await provider.generate(messages=formatted_messages, **params)
        content = res.get("content", "").strip()
        thinking = res.get("thinking")
        model = res.get("model", "")
        # Handle cases where provider does not have provider_name property/attribute
        p_name = getattr(provider, "provider_name", "unknown")
        from unittest.mock import NonCallableMock
        if callable(p_name) and not isinstance(p_name, NonCallableMock):
            try:
                p_name = p_name()
            except Exception:
                p_name = str(p_name)
        provider_used = res.get("provider_used", p_name)
        truncated = res.get("truncated", False)
        finish_reason = res.get("finish_reason")
    except Exception as e:
        logger.warning("LLM call via generate_unified failed: %s", e)
        if fallback_value is not None:
            return {
                "content": "",
                "json_data": fallback_value,
                "model": "",
                "provider_used": getattr(provider, "provider_name", "unknown"),
                "thinking": None,
                "truncated": False,
                "finish_reason": None,
                "error": str(e)
            }
        raise e

    # 3. Clean and parse JSON if expected
    json_data = None
    if expect_json:
        # Clean <think>...</think> reasoning tags
        cleaned = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        
        # Strip markdown code fences if any
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        try:
            json_data = _parse_json_safely(cleaned)
        except Exception as je:
            logger.warning("Failed standard JSON parse in generate_unified: %s.", je)
            if fallback_value is not None:
                json_data = fallback_value
            else:
                json_data = None

    return {
        "content": content,
        "json_data": json_data,
        "model": model,
        "provider_used": provider_used,
        "thinking": thinking,
        "truncated": truncated,
        "finish_reason": finish_reason,
        "error": None
    }

