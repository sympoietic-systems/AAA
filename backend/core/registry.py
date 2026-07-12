from collections.abc import Callable

from backend.modules.base import ProcessingModule


class ModuleRegistry:
    def __init__(self):
        self._factories: dict[str, Callable[[], ProcessingModule]] = {}
        self._modules: dict[str, ProcessingModule] = {}

    def register(self, name: str, factory: Callable[[], ProcessingModule]) -> None:
        self._factories[name] = factory

    def get(self, name: str) -> ProcessingModule | None:
        if name not in self._modules:
            if name not in self._factories:
                return None
            self._modules[name] = self._factories[name]()
        return self._modules[name]

    def resolve_pipeline(self, module_names: list[str]) -> list[ProcessingModule]:
        pipeline = []
        for name in module_names:
            mod = self.get(name)
            if mod is None:
                raise KeyError(f"Module not registered: {name}")
            pipeline.append(mod)
        return pipeline

    def validate_all(self) -> dict[str, bool]:
        results = {}
        for name in self._factories:
            mod = self.get(name)
            results[name] = mod.validate()
        return results
