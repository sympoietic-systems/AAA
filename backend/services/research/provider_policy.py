"""Validate limits once and freeze them with the task's journal policy."""

from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProviderPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    task_timeout_seconds: float = Field(default=1800, gt=0, le=3600)
    attempt_timeout_seconds: float = Field(default=60, gt=0, le=300)
    max_request_attempts: int = Field(default=4, ge=1, le=16)
    max_task_attempts: int = Field(default=128, ge=1, le=256)

    def freeze(self) -> dict[str, Any]:
        return {
            **self.model_dump(),
            "deadline": (datetime.now(UTC) + timedelta(seconds=self.task_timeout_seconds)).isoformat(),
        }


def query_limit(config: dict[str, Any], state: dict[str, Any]) -> int:
    policy = state.get("action_journal_policy") or {}
    value = policy.get("max_queries_per_cycle", config.get("max_queries", 6))
    return min(6, max(1, value)) if type(value) is int else 6
