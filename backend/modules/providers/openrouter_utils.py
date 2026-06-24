"""OpenRouter API utilities — reasoning exclusion and body cleanup."""


def build_openrouter_thinking_disabled(body: dict) -> None:
    """Disable reasoning/thinking for OpenRouter providers."""
    body["reasoning"] = {"exclude": True}
    body["include_reasoning"] = False


def clean_thinking_params(merged_params: dict) -> None:
    """Remove thinking-related keys that could conflict with provider-specific settings."""
    for key in ("thinking", "thinking_config", "reasoning", "include_reasoning", "thinking_budget", "max_tokens"):
        merged_params.pop(key, None)
