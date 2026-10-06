"""Bounded app-owned acquisition; cache access is not a fresh observation."""

import asyncio
import logging
import time
import uuid
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import Any, TypeVar

import httpx
from pydantic import Field

from backend.modules.pdf_extraction import PDFSettings, retained_characters
from backend.modules.retrieval.safe_http import SafeFetchResponse
from backend.services.research.action_journal import input_hash
from backend.storage.research_receipts import ReceiptModel
from backend.utils.security import validate_safe_url

T = TypeVar("T")
logger = logging.getLogger(__name__)


class AcquisitionPolicy(ReceiptModel):
    concurrency: int = Field(default=4, ge=1, le=8)
    provider_concurrency: int = Field(default=2, ge=1, le=4)
    minimum_interval_seconds: float = Field(default=0.1, ge=0, le=60)
    jina_interval_seconds: float = Field(default=3, ge=0, le=60)
    ddg_interval_seconds: float = Field(default=1.5, ge=0, le=60)
    request_timeout_seconds: float = Field(default=30, gt=0, le=120)
    cache_ttl_seconds: float = Field(default=300, ge=0, le=3600)
    cache_entries: int = Field(default=100, ge=1, le=256)
    cache_characters: int = Field(default=10_000_000, ge=1, le=20_000_000)


@dataclass(frozen=True)
class AcquisitionResult:
    content: str
    observed_at: datetime
    valid_until: datetime
    accessed_at: datetime
    cache_hit: bool
    config_hash: str
    providers: tuple[str, ...]
    origin_acquisition_id: str
    access_acquisition_id: str


@dataclass
class AcquisitionContext:
    runtime: "AcquisitionRuntime"
    deadline: datetime
    providers: list[str]


@dataclass
class AcquisitionResources:
    slots: asyncio.Semaphore = field(default_factory=lambda: asyncio.Semaphore(8))
    provider_slots: dict[str, asyncio.Semaphore] = field(default_factory=dict)
    rate_locks: dict[str, asyncio.Lock] = field(default_factory=dict)
    next_start: dict[str, float] = field(default_factory=dict)
    cpu_slots: asyncio.Semaphore = field(default_factory=lambda: asyncio.Semaphore(2))
    cpu_pending: set[asyncio.Task[Any]] = field(default_factory=set)


_context: ContextVar[AcquisitionContext | None] = ContextVar("research_acquisition", default=None)


def current_acquisition() -> AcquisitionContext | None:
    return _context.get()


@contextmanager
def acquisition_scope(context: AcquisitionContext) -> Iterator[None]:
    token = _context.set(context)
    try:
        yield
    finally:
        _context.reset(token)


class AcquisitionRuntime:
    def __init__(
        self,
        policy: AcquisitionPolicy,
        *,
        client: httpx.AsyncClient | None = None,
        validator: Callable[[str], str] = validate_safe_url,
        resources: AcquisitionResources | None = None,
    ):
        self.policy = policy
        self.validator = validator
        self.resources = resources or AcquisitionResources()
        self._client = client
        self._slots = asyncio.BoundedSemaphore(policy.concurrency)
        self._provider_slots: dict[str, asyncio.Semaphore] = {}
        self._cache: OrderedDict[str, AcquisitionResult] = OrderedDict()
        self._stripes = [asyncio.Lock() for _ in range(32)]
        self._pending: set[asyncio.Task[Any]] = set()
        self._closed = False

    def client(self) -> httpx.AsyncClient:
        if self._closed:
            raise RuntimeError("Acquisition runtime is closed")
        if self._client is None:
            self._client = httpx.AsyncClient(
                follow_redirects=False,
                trust_env=False,
                limits=httpx.Limits(max_connections=8, max_keepalive_connections=8),
            )
        return self._client

    async def _bounded(self, call: Callable[[], Awaitable[T]], deadline: datetime) -> T:
        remaining = (deadline - datetime.now(UTC)).total_seconds()
        if remaining <= 0 or self._closed or len(self._pending) >= 32:
            raise TimeoutError("Acquisition boundary exhausted")

        async def run() -> T:
            async with self.resources.slots, self._slots:
                return await call()

        task = asyncio.create_task(run())
        self._pending.add(task)

        def drain(done: asyncio.Task[T]) -> None:
            self._pending.discard(done)
            if not done.cancelled():
                done.exception()

        task.add_done_callback(drain)
        try:
            done, _ = await asyncio.wait({task}, timeout=remaining)
            if not done or datetime.now(UTC) >= deadline:
                task.cancel()
                raise TimeoutError("Acquisition deadline exceeded")
            return task.result()
        except BaseException:
            if not task.cancelling():
                task.cancel()
            raise

    async def fetch(
        self,
        url: str,
        config: dict[str, Any],
        deadline: datetime,
        loader: Callable[[], Awaitable[str]],
        acquisition_id: str | None = None,
        observe: Callable[[AcquisitionResult], Awaitable[None]] | None = None,
        namespace: str = "",
    ) -> AcquisitionResult:
        fingerprint = input_hash(
            {
                "url": url,
                "config": config,
                "parser_contract": "sensory-v2",
                "namespace": namespace,
                "pdf_settings": PDFSettings.from_env().fingerprint(),
            }
        )
        access_id = acquisition_id or str(uuid.uuid4())
        stripe = self._stripes[int(fingerprint[:8], 16) % len(self._stripes)]

        async def load() -> AcquisitionResult:
            async with stripe:
                safe_url = await asyncio.to_thread(self.validator, url)
                if safe_url != url:
                    raise ValueError("Destination identity changed")
                now = datetime.now(UTC)
                cached = self._cache.get(fingerprint)
                if cached is not None and now < cached.valid_until:
                    self._cache.move_to_end(fingerprint)
                    result = replace(cached, cache_hit=True, accessed_at=now, access_acquisition_id=access_id)
                    if observe is not None:
                        await observe(result)
                    return result
                providers: list[str] = []
                with acquisition_scope(AcquisitionContext(self, deadline, providers)):
                    content = await loader()
                if len(content) > 2_000_000:
                    raise ValueError("Acquisition text exceeds source limit")
                now = datetime.now(UTC)
                active = asyncio.current_task()
                if active is not None and active.cancelling():
                    raise asyncio.CancelledError
                if self._closed or now >= deadline:
                    raise TimeoutError("Late acquisition cannot enter cache")
                result = AcquisitionResult(
                    content,
                    now,
                    now + timedelta(seconds=self.policy.cache_ttl_seconds),
                    now,
                    False,
                    fingerprint,
                    tuple(providers),
                    access_id,
                    access_id,
                )
                if observe is not None:
                    await observe(result)
                if active is not None and active.cancelling():
                    raise asyncio.CancelledError
                if self._closed or datetime.now(UTC) >= deadline:
                    raise TimeoutError("Acquisition observation passed its delivery boundary")
                if content and retained_characters(content) <= self.policy.cache_characters:
                    self._cache[fingerprint] = result
                    self._cache.move_to_end(fingerprint)
                    while (
                        len(self._cache) > self.policy.cache_entries
                        or sum(retained_characters(v.content) for v in self._cache.values())
                        > self.policy.cache_characters
                    ):
                        self._cache.popitem(last=False)
                return result

        return await self._bounded(load, deadline)

    async def provider_call(self, provider: str, call: Callable[[], Awaitable[T]]) -> T:
        if provider not in {"jina", "firecrawl", "crawl4ai", "ddg", "pdf"}:
            raise ValueError("Unknown acquisition provider")
        context = current_acquisition()
        if context is None or context.runtime is not self:
            raise RuntimeError("Provider call requires acquisition context")
        gate = self._provider_slots.setdefault(provider, asyncio.Semaphore(self.policy.provider_concurrency))
        lock = self.resources.rate_locks.setdefault(provider, asyncio.Lock())
        shared_gate = self.resources.provider_slots.setdefault(provider, asyncio.Semaphore(4))
        async with shared_gate, gate:
            async with lock:
                delay = max(0, self.resources.next_start.get(provider, 0) - time.monotonic())
                if datetime.now(UTC) + timedelta(seconds=delay) >= context.deadline:
                    raise TimeoutError("Provider rate delay exceeds acquisition deadline")
                await asyncio.sleep(delay)
                interval = (
                    self.policy.jina_interval_seconds
                    if provider == "jina"
                    else self.policy.ddg_interval_seconds
                    if provider == "ddg"
                    else self.policy.minimum_interval_seconds
                )
                self.resources.next_start[provider] = time.monotonic() + interval
            context.providers.append(provider)
            return await call()

    async def cpu_call(self, call: Callable[[], T]) -> T:
        """A cancelled awaiter cannot release a still-running thread's capacity."""
        if self._closed or len(self.resources.cpu_pending) >= 8:
            raise RuntimeError("Acquisition CPU capacity exhausted")

        async def work() -> T:
            async with self.resources.cpu_slots:
                if self._closed:
                    raise asyncio.CancelledError
                return await asyncio.to_thread(call)

        task = asyncio.create_task(work())
        self.resources.cpu_pending.add(task)

        def drain(done: asyncio.Task[T]) -> None:
            self.resources.cpu_pending.discard(done)
            if not done.cancelled():
                error = done.exception()
                if error is not None:
                    logger.warning("Acquisition CPU failure category=%s", type(error).__name__)

        task.add_done_callback(drain)
        return await asyncio.shield(task)

    async def aclose(self) -> None:
        self._closed = True
        pending = set(self._pending)
        for task in pending:
            if not task.cancelling():
                task.cancel()
        if pending:
            await asyncio.wait(pending, timeout=1)
        if self._client is not None:
            await self._client.aclose()
        self._cache.clear()


async def acquisition_http(
    provider: str,
    url: str,
    *,
    timeout: float,
    headers: dict[str, str] | None = None,
    method: str = "GET",
    data: dict[str, str] | None = None,
    json: dict[str, Any] | None = None,
    max_bytes: int = 4 * 1024 * 1024,
) -> SafeFetchResponse:
    from backend.modules.retrieval.safe_http import safe_fetch

    context = current_acquisition()
    if context is None:
        return await safe_fetch(
            url, timeout=timeout, headers=headers, method=method, data=data, json=json, max_bytes=max_bytes
        )
    remaining = (context.deadline - datetime.now(UTC)).total_seconds()
    timeout = min(timeout, remaining, context.runtime.policy.request_timeout_seconds)
    if timeout <= 0:
        raise TimeoutError("Acquisition request deadline exceeded")
    return await context.runtime.provider_call(
        provider,
        lambda: safe_fetch(
            url,
            client=context.runtime.client(),
            validator=context.runtime.validator,
            timeout=timeout,
            headers=headers,
            method=method,
            data=data,
            json=json,
            max_bytes=max_bytes,
        ),
    )
