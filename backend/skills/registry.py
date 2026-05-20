from typing import Callable, Optional

from backend.core.registry import ModuleRegistry
from backend.modules.base import ProcessingModule

from .metadata import SkillMeta


class SkillRegistry(ModuleRegistry):
    def __init__(self):
        super().__init__()
        self._meta: dict[str, SkillMeta] = {}

    def register_with_meta(
        self,
        name: str,
        factory: Callable[[], ProcessingModule],
        meta: SkillMeta,
    ) -> None:
        self.register(name, factory)
        self._meta[name] = meta

    def get_meta(self, name: str) -> Optional[SkillMeta]:
        return self._meta.get(name)

    def list_always_on(self) -> list[tuple[str, ProcessingModule]]:
        result = []
        for name in self._factories:
            meta = self._meta.get(name)
            if meta and meta.always_run:
                mod = self.get(name)
                if mod:
                    result.append((name, mod))
        return result

    def list_on_demand(self) -> list[tuple[str, ProcessingModule, SkillMeta]]:
        result = []
        for name in self._factories:
            meta = self._meta.get(name)
            if meta and not meta.always_run:
                mod = self.get(name)
                if mod:
                    result.append((name, mod, meta))
        return result

    def find_by_trigger(self, text: str) -> list[str]:
        text_lower = text.lower()
        matched = []
        for name, meta in self._meta.items():
            for trigger in meta.triggers:
                if trigger in text_lower:
                    matched.append(name)
                    break
        return matched

    def describe_skills(self) -> str:
        lines = []
        on_demand = self.list_on_demand()
        if on_demand:
            lines.append("Available capabilities:")
            for name, _, meta in on_demand:
                lines.append(f"  - {name}: {meta.description}")
        return "\n".join(lines)
