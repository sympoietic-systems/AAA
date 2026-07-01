from abc import ABC, abstractmethod
from typing import Any, Type

from backend.services.research.task_state import StepEnvelope, StepOutput


class BaseResearchStep(ABC):
    @property
    @abstractmethod
    def step_type(self) -> str:
        """The database step_type identifier (e.g. 'plan', 'search', 'digest')."""
        pass

    @abstractmethod
    async def execute(self, orch, envelope: StepEnvelope) -> StepOutput:
        """Executes the step, reading from envelope and returning StepOutput."""
        pass

    async def preview(self, orch, envelope: StepEnvelope, state: dict) -> dict:
        """Previews step inputs/prompts without executing the step."""
        return {"phase": self.step_type, "note": "Preview not implemented for this step"}


class ResearchStepRegistry:
    _registry: dict[str, Type[BaseResearchStep]] = {}

    @classmethod
    def register(cls, step_type: str, step_class: Type[BaseResearchStep]):
        cls._registry[step_type] = step_class

    @classmethod
    def get_step(cls, step_type: str) -> BaseResearchStep:
        if step_type not in cls._registry:
            raise ValueError(f"Step type '{step_type}' not registered in pipeline.")
        return cls._registry[step_type]()
