from abc import ABC, abstractmethod

from backend.modules.llm_client import BaseLLMProvider


class BackgroundAction(ABC):
    @property
    @abstractmethod
    def action_type(self) -> str: ...

    @abstractmethod
    def system_prompt(self) -> str: ...

    @abstractmethod
    async def execute(self, provider: BaseLLMProvider, payload: dict) -> dict: ...
