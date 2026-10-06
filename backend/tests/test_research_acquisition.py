import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import ValidationError

from backend.services.research.acquisition import AcquisitionPolicy, AcquisitionRuntime, acquisition_http


def runtime(**limits):
    return AcquisitionRuntime(
        AcquisitionPolicy(minimum_interval_seconds=0, jina_interval_seconds=0, ddg_interval_seconds=0, **limits),
        validator=lambda url: url,
    )


def deadline(seconds=5):
    return datetime.now(UTC) + timedelta(seconds=seconds)


@pytest.mark.asyncio
async def test_cache_hit_keeps_observation_time_and_revalidates_destination():
    app = runtime()
    calls = 0

    async def loader():
        nonlocal calls
        calls += 1
        return "Evidence"

    first = await app.fetch("https://example.test/a", {}, deadline(), loader)
    second = await app.fetch("https://example.test/a", {}, deadline(), loader)
    assert calls == 1 and second.cache_hit
    assert second.observed_at == first.observed_at and second.valid_until == first.valid_until
    assert second.origin_acquisition_id == first.origin_acquisition_id
    assert second.accessed_at >= first.accessed_at

    def deny(url):
        raise ValueError("restricted destination")

    app.validator = deny
    with pytest.raises(ValueError, match="restricted"):
        await app.fetch("https://example.test/a", {}, deadline(), loader)
    await app.aclose()


@pytest.mark.asyncio
async def test_cache_expiry_config_change_and_failure_do_not_hide_historical_data():
    app = runtime(cache_ttl_seconds=0)
    calls = 0

    async def load():
        nonlocal calls
        calls += 1
        return "Old" if calls == 1 else "Changed"

    first = await app.fetch("https://example.test/a", {}, deadline(), load)
    second = await app.fetch("https://example.test/a", {}, deadline(), load)
    assert not second.cache_hit and second.observed_at > first.observed_at
    assert first.content == "Old" and second.content == "Changed"

    async def fail():
        raise httpx.ConnectError("offline")

    with pytest.raises(httpx.ConnectError):
        await app.fetch("https://example.test/a", {}, deadline(), fail)
    assert next(iter(app._cache.values())).content == "Changed"
    assert first.valid_until <= second.accessed_at
    app2 = runtime()
    await app2.fetch("https://example.test/a", {"parser": 1}, deadline(), load)
    changed = await app2.fetch("https://example.test/a", {"parser": 2}, deadline(), load)
    assert not changed.cache_hit
    await app.aclose()
    await app2.aclose()


@pytest.mark.asyncio
async def test_provider_concurrency_and_rate_gate_are_bounded():
    app = AcquisitionRuntime(
        AcquisitionPolicy(
            concurrency=4,
            provider_concurrency=2,
            minimum_interval_seconds=0.015,
            ddg_interval_seconds=0.015,
            jina_interval_seconds=0,
        ),
        validator=lambda url: url,
    )
    active = 0
    peak = 0
    starts = []

    async def call():
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        starts.append(asyncio.get_running_loop().time())
        await asyncio.sleep(0.025)
        active -= 1
        return "Evidence"

    async def load():
        return await app.provider_call("ddg", call)

    results = await asyncio.gather(*(app.fetch(f"https://example.test/{i}", {}, deadline(), load) for i in range(6)))
    assert len(results) == 6 and peak <= 2
    assert all(b - a >= 0.013 for a, b in zip(starts, starts[1:], strict=False))
    await app.aclose()


@pytest.mark.asyncio
async def test_timeout_does_not_wait_for_resistant_loader_or_accept_late_cache():
    app = runtime(concurrency=1)
    finished = asyncio.Event()

    async def stubborn():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            await asyncio.sleep(0.04)
        finally:
            finished.set()
        return "Late"

    with pytest.raises(TimeoutError):
        await app.fetch("https://example.test/a", {}, deadline(0.02), stubborn)
    assert not finished.is_set() and app._slots.locked()
    await asyncio.wait_for(finished.wait(), 1)
    await asyncio.sleep(0)
    assert not app._cache
    await app.aclose()


@pytest.mark.asyncio
async def test_shared_http_client_reuses_transport_and_closes():
    calls = []

    async def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, text="Evidence")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    app = AcquisitionRuntime(AcquisitionPolicy(jina_interval_seconds=0), client=client, validator=lambda url: url)

    async def load():
        return (await acquisition_http("jina", "https://proxy.test/page", timeout=1)).text

    await app.fetch("https://example.test/a", {}, deadline(), load)
    await app.fetch("https://example.test/b", {}, deadline(), load)
    assert len(calls) == 2 and app.client() is client
    await app.aclose()
    assert client.is_closed


@pytest.mark.asyncio
async def test_cancelled_acquisition_cannot_populate_cache():
    app = runtime()
    started = asyncio.Event()

    async def load():
        started.set()
        await asyncio.sleep(10)
        return "Evidence"

    task = asyncio.create_task(app.fetch("https://example.test/a", {}, deadline(), load))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await app.aclose()
    assert not app._pending and not app._cache


@pytest.mark.asyncio
async def test_cache_limits_and_single_flight():
    app = runtime(cache_entries=2, cache_characters=6)
    calls = 0

    async def load():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.005)
        return "abc"

    await asyncio.gather(*(app.fetch("https://example.test/a", {}, deadline(), load) for _ in range(5)))
    assert calls == 1
    for suffix in ("b", "c"):
        await app.fetch("https://example.test/" + suffix, {}, deadline(), load)
    assert len(app._cache) == 2 and sum(len(v.content) for v in app._cache.values()) == 6
    await app.aclose()


@pytest.mark.parametrize(
    "limits", [{"concurrency": 9}, {"cache_entries": 0}, {"minimum_interval_seconds": float("nan")}]
)
def test_policy_rejects_unbounded_limits(limits):
    with pytest.raises(ValidationError):
        AcquisitionPolicy(**limits)


@pytest.mark.asyncio
async def test_failed_observation_is_not_published_to_cache():
    app = runtime()

    async def load():
        return "Evidence"

    async def record(result):
        raise RuntimeError("Durable observation failed")

    with pytest.raises(RuntimeError, match="Durable"):
        await app.fetch("https://example.test/a", {}, deadline(), load, observe=record)
    assert not app._cache
    await app.aclose()


@pytest.mark.asyncio
async def test_cancel_resistance_cannot_publish_before_future_deadline():
    app = runtime()
    started, finished = asyncio.Event(), asyncio.Event()

    async def stubborn():
        started.set()
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            await asyncio.sleep(0.03)
        finished.set()
        return "Late"

    task = asyncio.create_task(app.fetch("https://example.test/a", {}, deadline(), stubborn))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await finished.wait()
    await asyncio.sleep(0)
    assert not app._cache
    await app.aclose()


@pytest.mark.asyncio
async def test_rate_wait_past_deadline_never_invokes_provider():
    app = AcquisitionRuntime(AcquisitionPolicy(minimum_interval_seconds=1), validator=lambda url: url)

    async def call():
        return "Evidence"

    async def load():
        return await app.provider_call("ddg", call)

    await app.fetch("https://example.test/a", {}, deadline(), load)
    with pytest.raises(TimeoutError, match="rate delay"):
        await app.fetch("https://example.test/b", {}, deadline(0.05), load)
    assert len(app._cache) == 1
    await app.aclose()


@pytest.mark.asyncio
async def test_distinct_policies_share_provider_rate_limit():
    from backend.services.research.acquisition import AcquisitionResources

    resources = AcquisitionResources()
    policy = AcquisitionPolicy(minimum_interval_seconds=0.025, ddg_interval_seconds=0.025)
    first, second = (AcquisitionRuntime(policy, resources=resources, validator=lambda url: url) for _ in range(2))
    starts = []

    async def call():
        starts.append(asyncio.get_running_loop().time())
        return "Evidence"

    async def load(app):
        return await app.provider_call("ddg", call)

    await first.fetch("https://example.test/a", {}, deadline(), lambda: load(first))
    await second.fetch("https://example.test/b", {}, deadline(), lambda: load(second))
    assert starts[1] - starts[0] >= 0.023
    await first.aclose()
    await second.aclose()


@pytest.mark.asyncio
async def test_cancelled_cpu_awaiter_retains_physical_thread_capacity():
    import threading

    app = runtime()
    started, release = threading.Event(), threading.Event()

    def work():
        started.set()
        release.wait(2)
        return "Discarded late extraction"

    task = asyncio.create_task(app.cpu_call(work))
    try:
        await asyncio.to_thread(started.wait, 1)
        assert started.is_set()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert len(app.resources.cpu_pending) == 1
    finally:
        release.set()
        if app.resources.cpu_pending:
            await asyncio.wait(set(app.resources.cpu_pending), timeout=2)
        await app.aclose()
    assert not app.resources.cpu_pending
