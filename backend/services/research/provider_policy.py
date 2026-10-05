"""Validate limits once and freeze them with the task's journal policy."""

from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProviderPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    task_timeout_seconds: float = Field(default=600, gt=0, le=3600)
    attempt_timeout_seconds: float = Field(default=60, gt=0, le=300)
    max_request_attempts: int = Field(default=4, ge=1, le=16)
    max_task_attempts: int = Field(default=64, ge=1, le=256)

    def freeze(self) -> dict[str, Any]:
        return {
            **self.model_dump(),
            "deadline": (datetime.now(UTC) + timedelta(seconds=self.task_timeout_seconds)).isoformat(),
        }
