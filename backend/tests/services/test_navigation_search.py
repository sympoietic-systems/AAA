import asyncio
import threading

import numpy as np
import pytest

from backend.api.routes.search import search_archive
from backend.services.archive_search import SearchBusy, SearchCapacity
from benchmarks.fixtures.navigation import archive
from benchmarks.fixtures.navigation_search_v1 import search_archive as reference


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode,weights",
    [
        ("text", (1, 0, 0, 0)),
        ("semantic", (0, 1, 0, 0)),
        ("diffractive", (0, 0, 1, 0)),
        ("glitch", (0, 0, 0, 1)),
        ("text", (0.4, 0.3, 0.2, 0.1)),
    ],
)
@pytest.mark.parametrize("scope", [None, "conv-0", "missing"])
async def test_all_search_modes_match_frozen_scalar_reference(mode, weights, scope):
    request, _ = archive(220)
    kwargs = dict(
        q="memory",
        conversation_id=scope,
        mode=mode,
        w_text=weights[0],
        w_semantic=weights[1],
        w_structural=weights[2],
        w_glitch=weights[3],
    )
    expected = await reference(request, **kwargs)
    actual = await search_archive(request, **kwargs)
    assert [m.model_dump(exclude={"relevance_score"}) for m in actual] == [
        m.model_dump(exclude={"relevance_score"}) for m in expected
    ]
    assert np.allclose([m.relevance_score for m in actual], [m.relevance_score for m in expected], atol=1e-6, rtol=0)


@pytest.mark.asyncio
async def test_cancelled_client_keeps_worker_slot_until_thread_exits():
    capacity = SearchCapacity(active_limit=1, waiting_limit=1, wait_seconds=0.03)
    started, release = threading.Event(), threading.Event()

    def work():
        started.set()
        assert release.wait(2)
        return []

    running = asyncio.create_task(capacity.run(work))
    await asyncio.to_thread(started.wait, 1)
    running.cancel()
    with pytest.raises(asyncio.CancelledError):
        await running
    assert capacity.active == 1
    try:
        with pytest.raises(SearchBusy):
            await capacity.run(lambda: [])
        assert capacity.waiting == 0
    finally:
        release.set()
    for _ in range(100):
        if not capacity.active:
            break
        await asyncio.sleep(0.001)
    assert capacity.active == 0


@pytest.mark.asyncio
async def test_queue_full_and_cancel_before_dispatch_do_not_leak_slots():
    capacity = SearchCapacity(active_limit=1, waiting_limit=1)
    release = threading.Event()
    running = asyncio.create_task(capacity.run(lambda: (release.wait(2), [])[1]))
    await asyncio.sleep(0.01)
    waiting = asyncio.create_task(capacity.run(lambda: []))
    await asyncio.sleep(0.01)
    try:
        with pytest.raises(SearchBusy):
            await capacity.run(lambda: [])
        waiting.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiting
        assert capacity.waiting == 0
    finally:
        release.set()
        await running


@pytest.mark.asyncio
async def test_overload_has_structured_response_and_retry_header():
    request, _ = archive(10)
    capacity = SearchCapacity(active_limit=0, waiting_limit=0)
    request.app.state.search_capacity = capacity
    response = await search_archive(
        request,
        q="memory",
        conversation_id=None,
        mode="text",
        w_text=1.0,
        w_semantic=0.0,
        w_structural=0.0,
        w_glitch=0.0,
    )
    assert response.status_code == 503
    assert response.headers["Retry-After"] == "1"
    import json

    assert json.loads(response.body)["kind"] == "constraint_violation"


@pytest.mark.parametrize(
    "mode,weights",
    [("semantic", (0.0, 1.0, 0.0, 0.0)), ("diffractive", (0.0, 0.0, 1.0, 0.0)), ("text", (0.4, 0.3, 0.2, 0.1))],
)
@pytest.mark.asyncio
async def test_near_ties_and_gate_boundaries_keep_scalar_order(mode, weights):
    request, candidates = archive(80)
    for i, value in enumerate([0.0, 1e-7, 0.45 - 1e-7, 0.45 + 1e-7, 0.8 - 1e-7, 0.8 + 1e-7, 0.99, 0.99 + 1e-7]):
        semantic = np.zeros(384, dtype=np.float32)
        structural = np.zeros(16, dtype=np.float32)
        semantic[:2] = structural[:2] = [value, np.sqrt(1 - value * value)]
        row = candidates[i]
        candidates[i] = (*row[:5], semantic.tobytes(), structural.tobytes())
    kwargs = dict(
        q="memory",
        conversation_id=None,
        mode=mode,
        w_text=weights[0],
        w_semantic=weights[1],
        w_structural=weights[2],
        w_glitch=weights[3],
    )
    expected = await reference(request, **kwargs)
    actual = await search_archive(request, **kwargs)
    assert [m.model_dump(exclude={"relevance_score"}) for m in actual] == [
        m.model_dump(exclude={"relevance_score"}) for m in expected
    ]
    assert np.allclose([m.relevance_score for m in actual], [m.relevance_score for m in expected], atol=1e-6, rtol=0)
