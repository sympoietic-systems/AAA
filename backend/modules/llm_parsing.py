"""Unified LLM message formatting and tolerant JSON parsing."""

import json
import logging
import re
from typing import Any, cast
from unittest.mock import NonCallableMock

from backend.modules.llm_protocol import BaseLLMProvider, LLMMessage, LLMResult

logger = logging.getLogger(__name__)


def _format_context(messages: list[LLMMessage]) -> str:
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


def _parse_json_safely(text: str) -> LLMResult:

    # 1. Clean think tags
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # 2. Extract between first { and last }
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace == -1:
        if not cleaned:
            return {}
        return cast(LLMResult, json.loads(cleaned))

    json_part = cleaned[first_brace : last_brace + 1] if last_brace > first_brace else cleaned[first_brace:]

    # 3. Helper to clean control characters and commas inside string
    def sanitize(s: str) -> str:
        s = re.sub(r",\s*([\]\}])", r"\1", s)
        chars = []
        in_string = False
        escape = False
        for char in s:
            if char == '"' and not escape:
                in_string = not in_string
                chars.append(char)
            elif in_string:
                if char == "\n":
                    chars.append("\\n")
                elif char == "\t":
                    chars.append("\\t")
                elif char == "\r":
                    chars.append("\\r")
                else:
                    chars.append(char)
            else:
                chars.append(char)

            escape = not escape if (char == "\\" and in_string) else False
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
                escape = not escape if char == "\\" else False
            else:
                if char in ("{", "["):
                    stack.append(char)
                elif char in ("}", "]") and stack:
                    top = stack[-1]
                    if (char == "}" and top == "{") or (char == "]" and top == "["):
                        stack.pop()

        repaired = s
        if in_string:
            repaired += '"'
        for item in reversed(stack):
            if item == "{":
                repaired += "}"
            elif item == "[":
                repaired += "]"
        return repaired

    # Try standard sanitize and parse
    sanitized = sanitize(json_part)
    try:
        return cast(LLMResult, json.loads(sanitized))
    except json.JSONDecodeError:
        pass

    # Try auto-closing and parsing
    try:
        closed = auto_close(sanitized)
        return cast(LLMResult, json.loads(closed))
    except json.JSONDecodeError:
        pass

    # Try finding last brace if any and slice/parse
    last_brace = sanitized.rfind("}")
    if last_brace != -1:
        try:
            return cast(LLMResult, json.loads(sanitized[: last_brace + 1]))
        except json.JSONDecodeError:
            pass

    return cast(LLMResult, json.loads(cleaned))


async def generate_unified(
    provider: BaseLLMProvider,
    system_prompt: str | None = None,
    user_prompt: str | None = None,
    messages: list[LLMMessage] | None = None,
    expect_json: bool = False,
    fallback_value: LLMResult | None = None,
    thinking_override: bool | None = None,
    **params: Any,
) -> LLMResult:
    """Standardized wrapper for LLM calls with automatic message list construction, cleaning, and JSON parsing."""

    # 1. Compile messages list
    formatted_messages: list[LLMMessage] = []
    if messages:
        formatted_messages = list(messages)
        if system_prompt and not (formatted_messages and formatted_messages[0].get("role") == "system"):
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
                "error": str(e),
            }
        raise e

    # 3. Clean and parse JSON if expected
    json_data = None
    if expect_json:
        # Clean <think>...</think> reasoning tags
        cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

        # Strip markdown code fences if any
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        # Parse JSON
        try:
            json_data = _parse_json_safely(cleaned)
        except (json.JSONDecodeError, TypeError, ValueError) as je:
            logger.warning("Failed standard JSON parse in generate_unified: %s.", je)
            json_data = fallback_value if fallback_value is not None else None

    return {
        "content": content,
        "json_data": json_data,
        "model": model,
        "provider_used": provider_used,
        "thinking": thinking,
        "truncated": truncated,
        "finish_reason": finish_reason,
        "error": None,
    }
