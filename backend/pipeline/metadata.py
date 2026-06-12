from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ModuleMeta:
    name: str
    description: str
    triggers: list[str] = field(default_factory=list)
    category: str = "action"
    always_run: bool = False
    cost: str = "free"
    children: list[ModuleMeta] = field(default_factory=list)
