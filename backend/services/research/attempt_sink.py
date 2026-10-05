"""Translate module invocation events into task-scoped durable receipts."""

import asyncio
from datetime import UTC, datetime
from typing import Any

from backend.storage.repositories.research.provider_attempt import ResearchProviderAttemptRepository
from backend.storage.research_receipts import ProviderAttemptReceipt, ResearchActionReceipt


class DurableAttemptSink:
    def __init__(
        self,
        repo: ResearchProviderAttemptRepository,
        action: ResearchActionReceipt,
        records: list[ProviderAttemptReceipt],
        max_task_attempts: int,
    ):
        self.repo = repo
        self.action = action
        self.records = records
        self.max_task_attempts = max_task_attempts
        self.pending: dict[str, ProviderAttemptReceipt] = {}

    async def start(self, attempt_id: str, request_id: str, number: int, provider: str, model: str) -> None:
        receipt = ProviderAttemptReceipt(
            attempt_id=attempt_id,
            task_id=self.action.task_id,
            action_id=self.action.action_id,
            request_id=request_id,
            provider=provider,
            model=model,
            attempt_number=number,
            started_at=datetime.now(UTC),
        )
        await asyncio.to_thread(self.repo.reserve, receipt, self.max_task_attempts)
        self.pending[attempt_id] = receipt

    async def finish(
        self, attempt_id: str, outcome: str, elapsed: float, result: Any = None, error: str | None = None
    ) -> None:
        initial = self.pending[attempt_id]
        raw = result if isinstance(result, dict) else {}
        usage = raw.get("usage")
        reason = raw.get("finish_reason")
        provider_request_id = raw.get("request_id")
        truncated = raw.get("truncated")
        if reason in {"length", "max_tokens"}:
            truncated = True
        receipt = ProviderAttemptReceipt.model_validate(
            {
                **initial.model_dump(),
                "completed_at": datetime.now(UTC),
                "outcome": outcome,
                "elapsed_seconds": elapsed,
                "error_category": error,
                "cancelled": outcome == "cancelled",
                "finish_reason": reason if isinstance(reason, str) else None,
                "provider_request_id": provider_request_id if isinstance(provider_request_id, str) else None,
                "truncated": truncated if isinstance(truncated, bool) else None,
                "usage": {k: v for k, v in usage.items() if isinstance(k, str) and type(v) is int and v >= 0}
                if isinstance(usage, dict)
                else None,
            }
        )
        await asyncio.to_thread(self.repo.finish, receipt)
        self.records.append(receipt)
        del self.pending[attempt_id]
