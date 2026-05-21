import logging
from abc import ABC, abstractmethod
from pathlib import Path

import yaml

from backend.modules.llm_client import BaseLLMProvider

PROMPTS_DIR = Path(__file__).parent / "prompts"
logger = logging.getLogger(__name__)


class BackgroundAction(ABC):
    _prompt_data: dict | None = None
    _prompt_file: str | None = None

    @property
    @abstractmethod
    def action_type(self) -> str: ...

    @property
    def prompt_file(self) -> str:
        return self._prompt_file or f"{self.action_type}.yaml"

    def _load_prompt(self) -> dict:
        if self._prompt_data is not None:
            return self._prompt_data

        path = PROMPTS_DIR / self.prompt_file
        if path.exists():
            with open(path) as f:
                self._prompt_data = yaml.safe_load(f) or {}
            logger.info("Loaded prompt from %s", path)
        else:
            logger.warning("Prompt file not found: %s", path)
            self._prompt_data = {}

        return self._prompt_data

    def system_prompt(self) -> str:
        return self._load_prompt().get("system_prompt", "")

    def default_params(self) -> dict:
        return self._load_prompt().get("parameters", {})

    @abstractmethod
    async def execute(self, provider: BaseLLMProvider, payload: dict) -> dict: ...
