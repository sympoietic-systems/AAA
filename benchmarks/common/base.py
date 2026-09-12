"""
Base abstractions and protocol definitions for modular benchmark suites.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BENCHMARKS_ROOT = PROJECT_ROOT / "benchmarks"


@dataclass
class RunMetadata:
    run_id: str
    suite_name: str
    run_type: str  # "eval", "compare", "live", "synthetic"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    git_commit: str = "unknown"
    custom_name: str = ""
    command_executed: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "suite_name": self.suite_name,
            "run_type": self.run_type,
            "timestamp": self.timestamp,
            "git_commit": self.git_commit,
            "custom_name": self.custom_name,
            "command_executed": self.command_executed,
            "parameters": self.parameters,
            "duration_seconds": self.duration_seconds,
            "tags": self.tags,
        }


class BaseBenchmarkSuite(ABC):
    """Abstract interface for a modular benchmark suite."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier of the benchmark suite (e.g. 'telemetry', 'memory')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Short human- and agent-readable summary of what this suite evaluates."""
        pass
