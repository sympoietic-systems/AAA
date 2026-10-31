"""Offline scalar/candidate search benchmark; emits aggregate JSON only."""

import argparse
import asyncio
import json
import platform
import resource
import statistics
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from benchmarks.fixtures.navigation import archive
from benchmarks.fixtures.navigation_search_v1 import search_archive as reference


async def measure(call, request, samples):
    kwargs = dict(
        q="memory", conversation_id=None, mode="semantic", w_text=0.0, w_semantic=1.0, w_structural=0.0, w_glitch=0.0
    )
    await call(request, **kwargs)
    elapsed, delays = [], []
    for _ in range(samples):
        running = True
        lags = []

        async def heartbeat():
            while running:
                start = time.perf_counter()
                await asyncio.sleep(0.002)
                lags.append(max(0, time.perf_counter() - start - 0.002))

        task = asyncio.create_task(heartbeat())
        await asyncio.sleep(0.005)
        start = time.perf_counter()
        await call(request, **kwargs)
        elapsed.append(time.perf_counter() - start)
        await asyncio.sleep(0.005)
        running = False
        await task
        delays.append(max(lags))
    return {
        "event_loop_max_seconds": delays,
        "seconds": elapsed,
        "median_seconds": statistics.median(elapsed),
        "mean_seconds": statistics.mean(elapsed),
        "stdev_seconds": statistics.stdev(elapsed) if len(elapsed) > 1 else 0.0,
        "p95_seconds": float(np.percentile(elapsed, 95)),
        "event_loop_p95_seconds": float(np.percentile(delays, 95)),
    }


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=20, choices=range(1, 101))
    parser.add_argument("--size", type=int, default=4000)
    parser.add_argument("--candidate", action="store_true")
    args = parser.parse_args()
    request, _ = archive(args.size)
    result = {
        "scope": "synthetic seeded archive; cached query embedding; no network/models",
        "python": platform.python_version(),
        "numpy": np.__version__,
        "messages": args.size,
        "samples": args.samples,
        "baseline": await measure(reference, request, args.samples),
    }
    if args.candidate:
        from backend.api.routes.search import search_archive

        result["candidate"] = await measure(search_archive, request, args.samples)
        result["speedup"] = result["baseline"]["median_seconds"] / result["candidate"]["median_seconds"]
    result["peak_process_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
