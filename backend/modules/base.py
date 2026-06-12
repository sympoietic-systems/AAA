from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.pipeline.metadata import ModuleMeta


@dataclass
class ModuleResult:
    status: str = "ok"  # ok | error
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class ProcessingModule(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def validate(self) -> bool: ...

    @abstractmethod
    async def process(self, payload: dict) -> dict: ...

    @property
    def module_meta(self) -> "ModuleMeta | None":
        return None
