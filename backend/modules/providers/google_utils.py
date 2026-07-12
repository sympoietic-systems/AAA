"""Google Gemini API utilities — parameter stripping and body building."""


def sanitize_google_params(merged_params: dict) -> dict:
    """Strip unsupported parameters from a merged params dict for Gemini.

    - Removes presence_penalty, frequency_penalty (not supported by Gemini)
    - Elevates max_tokens if <= 4096 (Gemini thinking tokens count against limit)
    """
    merged_params.pop("presence_penalty", None)
    merged_params.pop("frequency_penalty", None)
    if "max_tokens" in merged_params and merged_params["max_tokens"] <= 4096:
        merged_params["max_tokens"] = 8192
    return merged_params


def build_google_thinking_enabled(body: dict, reasoning_effort: str = "high") -> None:
    """Set thinking=enabled on a request body for Gemini."""
    body["thinking"] = {"type": "enabled"}
    body["reasoning_effort"] = reasoning_effort


def build_google_thinking_disabled(body: dict) -> None:
    """Set thinking_config to 0 budget for Gemini, disabling reasoning."""
    body["thinking_config"] = {"thinking_budget": 0}
