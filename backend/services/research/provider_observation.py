"""Observe public provider calls; internal pool retries remain outside this scope."""

import asyncio
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from backend.modules.llm_client import generate_unified as _generate_unified
from backend.storage.research_receipts import ProviderAttemptReceipt, ResearchActionReceipt

_scope: ContextVar[tuple[ResearchActionReceipt, list[ProviderAttemptReceipt]] | None] = ContextVar(
    "research_provider_observations", default=None
)


@contextmanager
def observe_provider_calls(receipt: ResearchActionReceipt | None) -> Iterator[list[ProviderAttemptReceipt]]:
    records: list[ProviderAttemptReceipt] = []
    token = _scope.set((receipt, records) if receipt else None)
    try:
        yield records
    finally:
        _scope.reset(token)


class _ObservedProvider:
    def __init__(self, provider: Any, receipt: ResearchActionReceipt, records: list[ProviderAttemptReceipt]):
        self._provider = provider
        self._receipt = receipt
        self._records = records

    def __getattr__(self, name: str) -> Any:
        return getattr(self._provider, name)

    async def generate(self, *args: Any, **kwargs: Any) -> Any:
        started = datetime.now(UTC)
        clock = time.perf_counter()
        base = dict(
            task_id=self._receipt.task_id,
            action_id=self._receipt.action_id,
            request_id=str(uuid.uuid4()),
            provider="unknown",
            model="unknown",
            attempt_number=1,
            started_at=started,
        )
        try:
            result = await self._provider.generate(*args, **kwargs)
        except BaseException as exc:
            cancelled = isinstance(exc, asyncio.CancelledError)
            self._records.append(
                ProviderAttemptReceipt.model_validate(
                    {
                        **base,
                        "completed_at": datetime.now(UTC),
                        "elapsed_seconds": time.perf_counter() - clock,
                        "outcome": "cancelled" if cancelled else "failed",
                        "cancelled": cancelled,
                        "error_category": type(exc).__name__,
                    }
                )
            )
            raise
        raw = result if isinstance(result, dict) else {}
        reason = raw.get("finish_reason")
        reason = reason if isinstance(reason, str) else None
        truncated = True if reason == "length" else raw.get("truncated")
        truncated = truncated if isinstance(truncated, bool) else None
        usage = raw.get("usage")
        usage = (
            {k: v for k, v in usage.items() if isinstance(k, str) and type(v) is int and v >= 0}
            if isinstance(usage, dict)
            else None
        )
        self._records.append(
            ProviderAttemptReceipt.model_validate(
                {
                    **base,
                    "completed_at": datetime.now(UTC),
                    "elapsed_seconds": time.perf_counter() - clock,
                    "outcome": "partial" if truncated else "complete",
                    "finish_reason": reason,
                    "truncated": truncated,
                    "usage": usage,
                    "provider": raw.get("provider_used", raw.get("provider"))
                    if isinstance(raw.get("provider_used", raw.get("provider")), str)
                    else "unknown",
                    "model": raw.get("model") if isinstance(raw.get("model"), str) else "unknown",
                }
            )
        )
        return result


async def generate_unified(provider: Any, *args: Any, **kwargs: Any) -> Any:
    scope = _scope.get()
    if scope is not None:
        receipt, records = scope
        provider = _ObservedProvider(provider, receipt, records)
    return await _generate_unified(provider, *args, **kwargs)
