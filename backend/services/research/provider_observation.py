"""Observe legacy public calls or enforce frozen durable leaf-attempt policy."""

import asyncio
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from backend.modules.llm_client import generate_unified as _generate_unified
from backend.modules.provider_attempts import AttemptScope, attempt_scope, invoke_attempt, request_scope_factory
from backend.services.research.attempt_sink import DurableAttemptSink
from backend.storage.repositories.research.provider_attempt import ResearchProviderAttemptRepository
from backend.storage.research_receipts import ProviderAttemptReceipt, ResearchActionReceipt


class ProviderObservations(list[ProviderAttemptReceipt]):
    delivery_failed: bool = False


_scope: ContextVar[tuple[ResearchActionReceipt, ProviderObservations] | None] = ContextVar(
    "research_provider_observations", default=None
)
_durable: ContextVar[tuple[ResearchProviderAttemptRepository, dict[str, Any]] | None] = ContextVar(
    "research_durable_attempts", default=None
)


@contextmanager
def observe_provider_calls(
    receipt: ResearchActionReceipt | None,
    repo: ResearchProviderAttemptRepository | None = None,
    policy: dict[str, Any] | None = None,
) -> Iterator[ProviderObservations]:
    records = ProviderObservations()
    token = _scope.set((receipt, records) if receipt else None)
    durable_token = _durable.set((repo, policy) if repo is not None and policy is not None else None)

    def factory() -> AttemptScope:
        assert receipt is not None and repo is not None and policy is not None
        return AttemptScope(
            DurableAttemptSink(repo, receipt, records, policy["max_task_attempts"]),
            datetime.fromisoformat(policy["deadline"]),
            policy["attempt_timeout_seconds"],
            policy["max_request_attempts"],
            on_failure=lambda: setattr(records, "delivery_failed", True),
        )

    try:
        with request_scope_factory(
            factory if receipt is not None and repo is not None and policy is not None else None
        ):
            yield records
    finally:
        _scope.reset(token)
        _durable.reset(durable_token)


class _ObservedProvider:
    def __init__(self, provider: Any, receipt: ResearchActionReceipt, records: ProviderObservations):
        self._provider = provider
        self._receipt = receipt
        self._records = records

    def __getattr__(self, name: str) -> Any:
        return getattr(self._provider, name)

    async def generate(self, *args: Any, **kwargs: Any) -> Any:
        durable = _durable.get()
        if durable is not None:
            repo, policy = durable
            sink = DurableAttemptSink(repo, self._receipt, self._records, policy["max_task_attempts"])
            scope = AttemptScope(
                sink,
                datetime.fromisoformat(policy["deadline"]),
                policy["attempt_timeout_seconds"],
                policy["max_request_attempts"],
            )
            try:
                with attempt_scope(scope):
                    if getattr(self._provider, "supports_attempt_observation", False):
                        return await self._provider.generate(*args, **kwargs)
                    return await invoke_attempt(self._provider, *args, **kwargs)
            except BaseException:
                self._records.delivery_failed = True
                raise
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
