"""Model-pool routing, API-key rotation, and cooldown policy."""

import asyncio
import logging
import time
from typing import Any, cast

import httpx

from backend.modules.llm_http import OpenAICompatibleProvider
from backend.modules.llm_protocol import BaseLLMProvider, LLMMessage, LLMResult, RateLimitError

logger = logging.getLogger(__name__)


class KeyManager:
    """Manages rotation and cooldowns for a list of API keys."""

    def __init__(self, keys: list[str], cooldown_seconds: int = 300) -> None:
        self.keys = keys
        self.cooldown_seconds = cooldown_seconds
        self._exhausted: dict[str, float] = {}

    def get_available_key(self) -> str | None:
        now = time.time()
        for key in self.keys:
            until = self._exhausted.get(key, 0)
            if until and now < until:
                continue
            if key in self._exhausted:
                del self._exhausted[key]
            return key
        return None

    def mark_key_exhausted(self, key: str) -> None:
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
        google_keys: list[str] | None = None,
        deepseek_keys: list[str] | None = None,
        openrouter_keys: list[str] | None = None,
        google_api_base: str = "https://generativelanguage.googleapis.com/v1beta/openai",
        deepseek_api_base: str = "https://api.deepseek.com",
        openrouter_api_base: str = "https://openrouter.ai/api/v1",
        cooldown_seconds: int = 300,
        max_retries_per_model: int = 0,
        thinking: bool = False,
        reasoning_effort: str = "high",
        default_params: LLMResult | None = None,
        timeout: float = 60.0,
        openrouter_provider: LLMResult | None = None,
        openrouter_providers_map: LLMResult | None = None,
    ) -> None:
        self._api_key = api_key
        self._models = models
        self._fallback_model = fallback_model
        self._api_base = api_base
        self._google_api_base = google_api_base
        self._deepseek_api_base = deepseek_api_base
        self._openrouter_api_base = (
            openrouter_api_base
            if openrouter_api_base
            else ("https://openrouter.ai/api/v1" if "openrouter.ai" not in api_base else api_base)
        )
        self._cooldown_seconds = cooldown_seconds
        self._max_retries_per_model = max_retries_per_model
        self._thinking = thinking
        self._reasoning_effort = reasoning_effort
        self._default_params = default_params
        self._exhausted: dict[str, float] = {}
        self._last_model_used: str = ""
        self._last_model_time: float = 0.0
        self._timeout = timeout
        self._openrouter_provider = openrouter_provider
        self._openrouter_providers_map = openrouter_providers_map

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

    def _mark_exhausted(self, model: str) -> None:
        self._exhausted[model] = time.time() + self._cooldown_seconds

    def reset_exhaustion(self) -> None:
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

    async def generate(self, messages: list[LLMMessage], **params: Any) -> LLMResult:
        errors = []

        now = time.time()
        model_override = params.pop("model", None)
        if model_override:
            models_to_try = [model_override]
        else:
            models_to_try = self._all_models()
            if self._last_model_used and self._last_model_used in models_to_try:
                preferred_model = models_to_try[0]
                if self._last_model_used != preferred_model:
                    if now - self._last_model_time >= self._cooldown_seconds:
                        logger.info(
                            "Fallback period expired. Resetting priority to try preferred model %s again.",
                            preferred_model,
                        )
                        self._last_model_used = ""
                        self._last_model_time = 0.0
                    else:
                        # Prioritize last working model
                        models_to_try = [self._last_model_used] + [
                            m for m in models_to_try if m != self._last_model_used
                        ]

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
                api_base = self._openrouter_api_base
                key_mgr = self._openrouter_key_mgr
                provider_type = "openrouter"
            else:
                actual_model = model
                api_base = self._openrouter_api_base
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

                logger.info(
                    "Attempting model %s using provider %s with key %s", actual_model, provider_type, masked_key
                )

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
                    openrouter_provider=self._openrouter_provider,
                    openrouter_providers_map=self._openrouter_providers_map,
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
                    logger.warning(
                        "Key %s HTTP error %s for model %s. Rotating key...", masked_key, e.response.status_code, model
                    )
                except (httpx.RequestError, TimeoutError) as e:
                    # Network timeouts are transient — retry a few times before giving up
                    timeout_retries = 2
                    for retry_num in range(timeout_retries):
                        logger.warning(
                            "Connection error '%s' on model %s with key %s. Waiting 10s to retry (attempt %d/%d)...",
                            type(e).__name__,
                            model,
                            masked_key,
                            retry_num + 1,
                            timeout_retries,
                        )
                        await asyncio.sleep(10)
                        try:
                            result = await provider.generate(messages, **params)
                            if self._last_model_used != model:
                                self._last_model_used = model
                                self._last_model_time = time.time()
                            success = True
                            break
                        except (httpx.RequestError, TimeoutError):
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
                        errors.append(
                            f"{model} (key: {masked_key}): connection timeout after {timeout_retries} retries - {e}"
                        )
                        logger.warning(
                            "All timeout retries failed for model %s with key %s. Rotating key...", model, masked_key
                        )
                except Exception as e:
                    key_mgr.mark_key_exhausted(key)
                    errors.append(f"{model} (key: {masked_key}): {e}")
                    logger.warning(
                        "Key %s encountered error %s for model %s. Rotating key...", masked_key, type(e).__name__, model
                    )

            if success:
                return cast(LLMResult, result)

            self._mark_exhausted(model)
            logger.warning("All keys exhausted for model %s. Moving to next in pool.", model)

        if not errors:
            logger.error(
                "Model pool: no models were attempted. models_to_try=%s, exhausted=%s",
                models_to_try,
                list(self._exhausted.keys()),
            )
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
