from dataclasses import dataclass, field


@dataclass
class SkillMeta:
    name: str
    description: str
    triggers: list[str] = field(default_factory=list)
    category: str = "action"
    always_run: bool = False
    cost: str = "free"
