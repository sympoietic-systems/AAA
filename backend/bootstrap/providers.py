"""LLM provider factory functions.

Extracted from backend/main.py. Creates provider instances for:
- Primary LLM (chat/responses)
- Structural LLM (16D signatures)
- Vision LLM (image analysis)
- Background LLM (async tasks)
"""

import logging

logger = logging.getLogger(__name__)

PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "openrouter": {"model": "deepseek/deepseek-chat", "api_base": "https://openrouter.ai/api/v1"},
    "deepseek": {"model": "deepseek-v4-pro", "api_base": "https://api.deepseek.com"},
    "openai_compatible": {"model": "deepseek-v4-pro", "api_base": "https://api.deepseek.com"},
}


# ── Core provider factory ──────────────────────────────────────────────

def _create_provider(cfg: dict, *, use_default_params: bool = True, label: str = ""):
    """Create an LLM provider instance from a configuration dict.

    Supports:
    - Single-model providers (OpenRouter, DeepSeek, OpenAI-compatible)
    - Model pools with fallback, per-provider API keys, and cool-down
    - Router-prefix models (google_router/, deepseek_router/, openrouter_router/)
    - Thinking mode and reasoning effort parameters
    """
    provider_name = cfg.get("provider", "openrouter")
    defaults = PROVIDER_DEFAULTS.get(provider_name, {})
    api_key = cfg.get("api_key", "")
    api_base = cfg.get("api_base") or defaults.get("api_base", "")
    model = cfg.get("model") or defaults.get("model", "deepseek-chat")
    models = cfg.get("models", [])
    thinking_cfg = cfg.get("thinking", {})
    thinking = thinking_cfg.get("enabled", False)
    reasoning_effort = thinking_cfg.get("effort", "high")
    default_params = cfg.get("default_params") if use_default_params else None

    if models:
        fallback = cfg.get("fallback_model", "openrouter/free")
        google_keys = cfg.get("google_keys", [])
        deepseek_keys = cfg.get("deepseek_keys", [])
        openrouter_keys = cfg.get("openrouter_keys", [])
        google_api_base = cfg.get(
            "google_api_base",
            "https://generativelanguage.googleapis.com/v1beta/openai",
        )
        deepseek_api_base = cfg.get("deepseek_api_base", "https://api.deepseek.com")
        cooldown_seconds = cfg.get("cooldown_seconds", 300)
        if label:
            logger.info("%s model pool: %s (fallback: %s)", label, models, fallback)

        from backend.modules.llm_client import ModelPoolProvider

        return ModelPoolProvider(
            api_key=api_key,
            models=models,
            fallback_model=fallback,
            api_base=api_base,
            google_keys=google_keys,
            deepseek_keys=deepseek_keys,
            openrouter_keys=openrouter_keys,
            google_api_base=google_api_base,
            deepseek_api_base=deepseek_api_base,
            cooldown_seconds=cooldown_seconds,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
            default_params=default_params,
        )

    effective_model = model

    # ── Router-prefix dispatch ────────────────────────────────────────
    if model.startswith("google_router/"):
        effective_model = model.split("google_router/", 1)[1]
        key = (cfg.get("google_keys", []) or [api_key])[0]
        return _create_openai_compatible(
            key, effective_model,
            cfg.get("google_api_base", "https://generativelanguage.googleapis.com/v1beta/openai"),
            "google", default_params,
        )

    if model.startswith("deepseek_router/"):
        effective_model = model.split("deepseek_router/", 1)[1]
        key = (cfg.get("deepseek_keys", []) or [api_key])[0]
        return _create_openai_compatible(
            key, effective_model,
            cfg.get("deepseek_api_base", "https://api.deepseek.com"),
            "deepseek", default_params,
            thinking=thinking, reasoning_effort=reasoning_effort,
        )

    if model.startswith("openrouter_router/"):
        effective_model = model.split("openrouter_router/", 1)[1]
        key = (cfg.get("openrouter_keys", []) or [api_key])[0]
        return _create_openrouter(
            key, effective_model,
            api_base or "https://openrouter.ai/api/v1",
            default_params=default_params,
            thinking=thinking, reasoning_effort=reasoning_effort,
        )

    # ── Standard provider dispatch ────────────────────────────────────
    if provider_name == "openrouter" or model:
        return _create_openrouter(
            api_key, model,
            api_base or "https://openrouter.ai/api/v1",
            default_params=default_params,
            thinking=thinking, reasoning_effort=reasoning_effort,
        )

    return _create_openai_compatible(
        api_key, model, api_base, provider_name, default_params,
        thinking=thinking, reasoning_effort=reasoning_effort,
    )


# ── Provider constructors ──────────────────────────────────────────────

def _create_openai_compatible(
    api_key: str,
    model: str,
    api_base: str,
    provider_name: str,
    default_params=None,
    thinking: bool = False,
    reasoning_effort: str = "high",
):
    from backend.modules.llm_client import OpenAICompatibleProvider
    return OpenAICompatibleProvider(
        api_key=api_key,
        model=model,
        api_base=api_base,
        provider_name=provider_name,
        default_params=default_params,
        thinking=thinking,
        reasoning_effort=reasoning_effort,
    )


def _create_openrouter(
    api_key: str,
    model: str,
    api_base: str,
    default_params=None,
    thinking: bool = False,
    reasoning_effort: str = "high",
):
    from backend.modules.llm_client import OpenRouterProvider
    return OpenRouterProvider(
        api_key=api_key,
        model=model,
        api_base=api_base,
        default_params=default_params,
        thinking=thinking,
        reasoning_effort=reasoning_effort,
    )


# ── Backward-compatible wrappers ───────────────────────────────────────

def _create_llm_provider(cfg: dict):
    """Create provider with default_params included (legacy)."""
    return _create_provider(cfg, use_default_params=True, label="Main")


def _create_provider_from_config(cfg: dict):
    """Create provider without default_params (from config block)."""
    return _create_provider(cfg, use_default_params=False)


# ── Multi-provider initializer ─────────────────────────────────────────

def _init_providers(config: dict):
    """Create the primary, structural, and (optional) vision LLM providers."""
    llm_cfg = config.get("llm", {})
    llm_provider = _create_provider(llm_cfg, use_default_params=True, label="Main")

    # Structural provider defaults: reuse background config if no explicit structural
    struct_cfg = config.get("structural_llm", {})
    if not struct_cfg.get("model") and not struct_cfg.get("models"):
        bg_cfg = config.get("background_llm", {})
        struct_cfg = {**bg_cfg, "thinking": {"enabled": False, "effort": "low"}}
    else:
        struct_cfg.setdefault("thinking", {"enabled": False, "effort": "low"})
    structural_provider = _create_provider(struct_cfg, use_default_params=False)

    # Vision provider (optional)
    vision_provider = None
    vision_llm_cfg = config.get("vision_llm", {})
    if vision_llm_cfg.get("models") or vision_llm_cfg.get("model"):
        try:
            vision_provider = _create_provider(vision_llm_cfg, use_default_params=False)
            logger.info(
                "Vision model(s): %s",
                vision_llm_cfg.get("models") or vision_llm_cfg.get("model"),
            )
        except Exception:
            logger.warning("Failed to initialize vision provider")

    return llm_provider, structural_provider, vision_provider
