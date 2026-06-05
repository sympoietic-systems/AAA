import logging
from typing import Optional

from backend.modules.llm_client import BaseLLMProvider, RateLimitError

from .base import BackgroundAction

logger = logging.getLogger(__name__)


class BackgroundTaskEngine:
    def __init__(
        self,
        provider: BaseLLMProvider,
        vision_provider: Optional[BaseLLMProvider] = None,
    ):
        self._provider = provider
        self._vision_provider = vision_provider
        self._actions: dict[str, BackgroundAction] = {}

    @property
    def provider(self) -> BaseLLMProvider:
        return self._provider

    @property
    def vision_provider(self) -> Optional[BaseLLMProvider]:
        return self._vision_provider

    def register(self, action: BackgroundAction) -> None:
        self._actions[action.action_type] = action

    def get_action(self, action_type: str) -> Optional[BackgroundAction]:
        return self._actions.get(action_type)

    def list_actions(self) -> list[str]:
        return list(self._actions.keys())

    async def run(self, action_type: str, payload: dict) -> dict:
        action = self._actions.get(action_type)
        if not action:
            available = ", ".join(self._actions.keys())
            raise ValueError(f"Unknown action '{action_type}'. Available: {available}")

        provider = self._provider
        if payload.get("use_vision") and self._vision_provider:
            provider = self._vision_provider

        logger.info(f"Running background action: {action_type}")
        try:
            result = await action.execute(provider, payload)
            result["action"] = action_type
            return result
        except RateLimitError as e:
            logger.warning(f"Rate limit hit for action '{action_type}': {e}")
            return {
                "action": action_type,
                "content": "",
                "model": "",
                "error": f"Rate limited: {e}. Remaining: {e.remaining}/{e.limit}. Retry after {e.retry_after}s.",
                "rate_limit": {
                    "remaining": e.remaining,
                    "limit": e.limit,
                    "retry_after": e.retry_after,
                },
            }
