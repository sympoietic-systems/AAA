"""Core compatibility exports without eager cross-package imports."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.core.registry import ModuleRegistry
    from backend.metabolisation.context import PipelineResult

__all__ = ["ModuleRegistry", "PipelineResult"]


def __getattr__(name: str) -> Any:
    if name == "ModuleRegistry":
        from backend.core.registry import ModuleRegistry

        return ModuleRegistry
    if name == "PipelineResult":
        from backend.metabolisation.context import PipelineResult

        return PipelineResult
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
