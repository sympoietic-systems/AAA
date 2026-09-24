"""OpenRouter API utilities — reasoning exclusion and body cleanup."""


def build_openrouter_thinking_disabled(body: dict) -> None:
    """Disable reasoning/thinking for OpenRouter providers."""
    body["reasoning"] = {"exclude": True}
    body["include_reasoning"] = False


def sanitize_openrouter_params(merged_params: dict, use_thinking: bool = False) -> dict:
    """Elevate max_tokens when reasoning/thinking is enabled on OpenRouter.

    Reasoning tokens count against the max_tokens limit on OpenRouter.
    If max_tokens is missing or <= 4096, elevate to 8192 to prevent reasoning truncation.
    """
    if use_thinking:
        current_max = merged_params.get("max_tokens")
        if current_max is None or current_max <= 4096:
            merged_params["max_tokens"] = 8192
    return merged_params


def clean_thinking_params(merged_params: dict) -> None:
    """Remove thinking-related keys that could conflict with provider-specific settings."""
    for key in ("thinking", "thinking_config", "reasoning", "include_reasoning", "thinking_budget", "max_tokens"):
        merged_params.pop(key, None)


def build_openrouter_provider_config(body: dict, provider_params: dict | None = None) -> None:
    """Add OpenRouter provider routing preferences (order, allow_fallbacks, ignore, only, sort) to request body.

    ponytail: build minimum valid OpenRouter provider routing dict according to OpenRouter API spec.
    """
    if not provider_params or not isinstance(provider_params, dict):
        return

    provider_obj = {}
    if "order" in provider_params:
        order = provider_params["order"]
        if isinstance(order, str):
            order = [p.strip() for p in order.split(",") if p.strip()]
        if isinstance(order, list) and order:
            provider_obj["order"] = order

    if "allow_fallbacks" in provider_params and provider_params["allow_fallbacks"] is not None:
        allow = provider_params["allow_fallbacks"]
        if isinstance(allow, str):
            allow = allow.lower() in ("true", "1", "yes")
        provider_obj["allow_fallbacks"] = bool(allow)

    if "ignore" in provider_params:
        ignore = provider_params["ignore"]
        if isinstance(ignore, str):
            ignore = [p.strip() for p in ignore.split(",") if p.strip()]
        if isinstance(ignore, list) and ignore:
            provider_obj["ignore"] = ignore

    if "only" in provider_params:
        only = provider_params["only"]
        if isinstance(only, str):
            only = [p.strip() for p in only.split(",") if p.strip()]
        if isinstance(only, list) and only:
            provider_obj["only"] = only

    if "sort" in provider_params and provider_params["sort"]:
        provider_obj["sort"] = provider_params["sort"]

    if provider_obj:
        body["provider"] = provider_obj


def resolve_openrouter_provider_config(
    model: str,
    openrouter_provider: dict | None = None,
    providers_map: dict | None = None,
) -> dict | None:
    """Resolve provider routing config for a specific model.

    ponytail: check exact model match, then wildcard (e.g. 'deepseek/*'), fallback to global openrouter_provider.
    """
    if providers_map and isinstance(providers_map, dict):
        matched_cfg = providers_map.get(model)
        if not matched_cfg and "/" in model:
            prefix = model.split("/")[0] + "/*"
            matched_cfg = providers_map.get(prefix)

        if matched_cfg:
            if isinstance(matched_cfg, str):
                return {"order": [p.strip() for p in matched_cfg.split(",") if p.strip()]}
            elif isinstance(matched_cfg, dict):
                return matched_cfg

    if openrouter_provider and isinstance(openrouter_provider, dict):
        return openrouter_provider

    return None
