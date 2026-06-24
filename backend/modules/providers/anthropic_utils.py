"""Anthropic API utilities — request building and response parsing.

Extracted from llm_client.py to separate provider-specific logic
from the generic OpenAI-compatible code path.
"""

from typing import Any


def get_anthropic_endpoint(api_base: str) -> str:
    return f"{api_base.rstrip('/')}/v1/messages"


def get_anthropic_headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/aaa",
        "X-Title": "AAA",
        "anthropic-version": "2023-06-01",
    }


def get_openai_endpoint(api_base: str) -> str:
    return f"{api_base.rstrip('/')}/chat/completions"


def get_openai_headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/aaa",
        "X-Title": "AAA",
    }


def parse_anthropic_response(data: dict) -> dict:
    """Parse an Anthropic Messages API response into the standardized message format.

    Handles Anthropic's content[] array format (text + thinking blocks)
    and converts it to the {role, content, reasoning_content} dict
    expected by _parse_message().
    """
    content_list = data.get("content", [])
    text_content = ""
    reasoning_content = ""
    for block in content_list:
        if block.get("type") == "text":
            text_content += block.get("text", "")
        elif block.get("type") == "thinking":
            reasoning_content += block.get("thinking", "")

    return {
        "role": data.get("role", "assistant"),
        "content": text_content,
        "reasoning_content": reasoning_content,
    }


def build_anthropic_body(
    model: str,
    messages: list[dict],
    system_prompt: str,
    max_tokens: int,
    thinking_enabled: bool = False,
    **extra_params: Any,
) -> dict:
    """Build an Anthropic Messages API request body from standardized parameters.

    - Moves system messages to the top-level 'system' parameter
    - Maps roles to user/assistant only
    - Sets max_tokens (required by Anthropic)
    - Configures thinking budget when enabled
    """
    body: dict = {
        "model": model,
        "messages": _filter_anthropic_messages(messages),
        "max_tokens": max(max_tokens, 4096),
    }

    if system_prompt:
        body["system"] = system_prompt.strip()

    if thinking_enabled:
        body["thinking"] = {"type": "enabled", "budget_tokens": 1024}
    else:
        body["thinking"] = {"type": "disabled"}

    return body


def _filter_anthropic_messages(messages: list[dict]) -> list[dict]:
    """Filter and clean messages for Anthropic compatibility.

    - Strips system-role messages (handled separately as top-level 'system')
    - Maps roles to user/assistant only
    """
    filtered = []
    for m in messages:
        if m.get("role") == "system":
            continue
        role = m.get("role", "user")
        if role not in ("user", "assistant"):
            role = "user"
        filtered.append({"role": role, "content": m.get("content", "")})
    return filtered
