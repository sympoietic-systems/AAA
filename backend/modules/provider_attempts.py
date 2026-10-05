"""Research-scoped attempt policy. Modules own invocation; services supply storage."""

import asyncio
import logging
import time
import uuid
from collections.abc import Callable, Coroutine, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class AttemptBudgetExceeded(RuntimeError):
    """The recorded execution boundary permits no additional provider work."""


class AttemptSink(Protocol):
    async def start(self, attempt_id: str, request_id: str, number: int, provider: str, model: str) -> None: ...

    async def finish(
        self, attempt_id: str, outcome: str, elapsed: float, result: Any = None, error: str | None = None
    ) -> None: ...


@dataclass
class AttemptScope:
    sink: AttemptSink
    deadline: datetime
    timeout_seconds: float
    max_request_attempts: int
    on_failure: Callable[[], None] = lambda: None
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    number: int = 0


_scope: ContextVar[AttemptScope | None] = ContextVar("provider_attempt_scope", default=None)
_factory: ContextVar[Callable[[], AttemptScope] | None] = ContextVar("provider_attempt_factory", default=None)
# Cancel-resistant calls retain a strong reference and consume a bounded slot
# until they actually exit. Their eventual bytes never re-enter the caller.
_outstanding: set[asyncio.Task[Any]] = set()
MAX_OUTSTANDING = 8
_slots = asyncio.BoundedSemaphore(MAX_OUTSTANDING)


def current_scope() -> AttemptScope | None:
    return _scope.get()


def new_request_scope() -> AttemptScope | None:
    factory = _factory.get()
    return factory() if factory is not None else None


@contextmanager
def request_scope_factory(factory: Callable[[], AttemptScope] | None) -> Iterator[None]:
    token = _factory.set(factory)
    try:
        yield
    finally:
        _factory.reset(token)


@contextmanager
def attempt_scope(scope: AttemptScope) -> Iterator[None]:
    token = _scope.set(scope)
    try:
        yield
    finally:
        _scope.reset(token)


def _drain(task: asyncio.Task[Any]) -> None:
    _outstanding.discard(task)
    _slots.release()
    if not task.cancelled():
        error = task.exception()
        if error is not None:
            logger.debug("Detached provider terminated: %s", type(error).__name__)


async def invoke_attempt(provider: Any, messages: Any, **params: Any) -> Any:
    scope = _scope.get()
    if scope is None:
        return await provider.generate(messages=messages, **params)
    remaining = (scope.deadline - datetime.now(UTC)).total_seconds()
    if remaining <= 0 or scope.number >= scope.max_request_attempts or _slots.locked():
        scope.on_failure()
        raise AttemptBudgetExceeded("Provider deadline, attempt limit, or outstanding-call limit reached")
    scope.number += 1
    attempt_id = str(uuid.uuid4())
    await _slots.acquire()
    try:
        await scope.sink.start(
            attempt_id,
            scope.request_id,
            scope.number,
            str(getattr(provider, "provider_name", "unknown")),
            str(getattr(provider, "_model", "unknown")),
        )
    except BaseException:
        _slots.release()
        scope.on_failure()
        raise
    remaining = (scope.deadline - datetime.now(UTC)).total_seconds()
    clock = time.perf_counter()
    if remaining <= 0:
        _slots.release()
        await scope.sink.finish(attempt_id, "failed", 0, error="deadline_exceeded")
        raise AttemptBudgetExceeded("Deadline expired while recording provider intent")
    task = asyncio.create_task(provider.generate(messages=messages, **params))
    _outstanding.add(task)
    task.add_done_callback(_drain)
    terminal_recorded = False
    try:
        done, _ = await asyncio.wait({task}, timeout=min(scope.timeout_seconds, remaining))
        if not done:
            task.cancel()
            await scope.sink.finish(attempt_id, "failed", time.perf_counter() - clock, error="timeout")
            terminal_recorded = True
            raise TimeoutError("Provider attempt exceeded its execution boundary")
        result = task.result()
        if datetime.now(UTC) >= scope.deadline:
            await scope.sink.finish(attempt_id, "failed", time.perf_counter() - clock, error="deadline_exceeded")
            terminal_recorded = True
            raise AttemptBudgetExceeded("Late provider response cannot satisfy delivery")
    except BaseException as exc:
        scope.on_failure()
        if not terminal_recorded:
            task.cancel()
            await scope.sink.finish(
                attempt_id,
                "cancelled" if isinstance(exc, asyncio.CancelledError) else "failed",
                time.perf_counter() - clock,
                error=type(exc).__name__,
            )
        raise
    raw = result if isinstance(result, dict) else {}
    partial = raw.get("truncated") is True or raw.get("finish_reason") in {"length", "max_tokens"}
    await scope.sink.finish(attempt_id, "partial" if partial else "complete", time.perf_counter() - clock, result)
    return result


async def retry_delay(seconds: float) -> None:
    scope = _scope.get()
    if scope is None:
        await asyncio.sleep(seconds)
        return
    remaining = (scope.deadline - datetime.now(UTC)).total_seconds()
    if scope.number >= scope.max_request_attempts or remaining <= seconds:
        raise AttemptBudgetExceeded("Retry would exceed the provider execution boundary")
    await asyncio.sleep(seconds)


async def bounded_call(call: Callable[[], Coroutine[Any, Any, Any]], timeout: float) -> Any:
    """Bound a phase even when a nested service does not use the provider hook."""
    if timeout <= 0 or _slots.locked():
        raise AttemptBudgetExceeded("Research phase execution boundary exhausted")
    await _slots.acquire()
    task = asyncio.create_task(call())
    _outstanding.add(task)
    task.add_done_callback(_drain)
    try:
        done, _ = await asyncio.wait({task}, timeout=timeout)
        if not done:
            task.cancel()
            raise AttemptBudgetExceeded("Research phase deadline exceeded")
        return task.result()
    except BaseException:
        if not task.cancelling():
            task.cancel()
        raise


async def shutdown_attempts(timeout: float = 1.0) -> None:
    """Bound shutdown waiting; detached futures continue to reject delivery."""
    tasks = set(_outstanding)
    if not tasks:
        return
    for task in tasks:
        task.cancel()
    _, pending = await asyncio.wait(tasks, timeout=timeout)
    if pending:
        logger.warning("Provider shutdown left %d cancellation-resistant calls", len(pending))
