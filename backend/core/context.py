from dataclasses import dataclass, field
from typing import Any


@dataclass
class PipelineResult:
    status: str = "ok"  # ok | error
    payload: dict[str, Any] = field(default_factory=dict)
    errors: list[dict] = field(default_factory=list)
    module_outputs: dict[str, dict] = field(default_factory=dict)
