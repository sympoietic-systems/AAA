"""LLM provider contract and shared rate-limit error."""

from abc import ABC, abstractmethod
from typing import Any

LLMMessage = dict[str, Any]
LLMResult = dict[str, Any]


class RateLimitError(Exception):
    def __init__(self, message: str, retry_after: int = 0, remaining: int = 0, limit: int = 0):
        super().__init__(message)
        self.retry_after = retry_after
        self.remaining = remaining
        self.limit = limit


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(self, messages: list[LLMMessage], **params: Any) -> LLMResult: ...

    @abstractmethod
    async def validate_connection(self) -> bool: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    async def generate_unified(
        self,
        system_prompt: str | None = None,
        user_prompt: str | None = None,
        messages: list[LLMMessage] | None = None,
        expect_json: bool = False,
        fallback_value: LLMResult | None = None,
        **params: Any,
    ) -> LLMResult:
        """Standardized interface for LLM calls with robust message compilation, cleaning, and JSON parsing."""
        from backend.modules.llm_parsing import generate_unified

        return await generate_unified(
            self,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            messages=messages,
            expect_json=expect_json,
            fallback_value=fallback_value,
            **params,
        )
