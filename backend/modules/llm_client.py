from abc import ABC, abstractmethod
from typing import Optional

import httpx

from .base import ProcessingModule


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

    @property
    def provider_name(self) -> str:
        return self._name

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

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]
            return {
                "content": message.get("content", ""),
                "thinking": message.get("reasoning_content"),
            }

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
    ):
        super().__init__(
            api_key=api_key,
            model=model,
            api_base=api_base,
            provider_name="openrouter",
            default_params=default_params,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
        )


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
