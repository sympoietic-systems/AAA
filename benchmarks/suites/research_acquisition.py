"""Actual SearchStep replay against frozen HTTP responses; no live providers or DB."""

import asyncio
import hashlib
import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs

import httpx

from backend.services.research.acquisition import AcquisitionPolicy, AcquisitionRuntime
from backend.services.research.steps.search import SearchStep
from backend.services.research.task_state import SearchPayload


class FixtureOrchestrator:
    def __init__(self, runtime):
        self.runtime = runtime
        self._state = SimpleNamespace(config={"research_orchestrator": {"search_candidates": 2}}, llm_provider=None)
        self.default_top_n = 2
        self.step_repo = self.step_result_repo = None
        self.state = {}

    def acquisition_enabled(self, task_id):
        return self.runtime is not None

    async def acquire(self, task_id, url, loader, request_config=None):
        return await self.runtime.fetch(url, request_config or {}, datetime.now(UTC) + timedelta(seconds=30), loader)

    def _get_state(self, task_id):
        return self.state

    def _load_cache(self, task_id):
        return {}

    def _save_cache(self, *args):
        return None

    def _create_or_update_step(self, *args, **kwargs):
        return "fixture-step"

    def _log_meta(self, *args, **kwargs):
        return None


async def replay(pool):
    calls = 0
    creations = 0
    original_client = httpx.AsyncClient

    async def handler(request):
        nonlocal calls
        calls += 1
        query = parse_qs(request.content.decode())["q"][0]
        if query not in pool["queries"]:
            raise ValueError("Unfrozen query")
        await asyncio.sleep(pool["response_delay_seconds"])
        html = "".join(f'<a href="{source["url"]}">{source["title"]}</a>' for source in pool["sources"])
        return httpx.Response(200, text=html)

    transport = httpx.MockTransport(handler)

    def make_client(*args, **kwargs):
        nonlocal creations
        creations += 1
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    async def measure(orch):
        before_calls, before_clients = calls, creations
        started = time.perf_counter()
        envelope = SimpleNamespace(
            task_id="fixture",
            objective="Frozen coverage",
            current_depth=0,
            payload=SearchPayload(queries=pool["queries"]),
        )
        output = await SearchStep().execute(orch, envelope)
        elapsed = time.perf_counter() - started
        selected = [
            {"url": item["url"], "title": item["title"], "query_group": item["query_group"]}
            for item in output.payload.search_results
        ]
        expected = [
            {**source, "query_group": group}
            for group in range(1, len(pool["queries"]) + 1)
            for source in pool["sources"]
        ]
        if selected != expected:
            raise AssertionError("Frozen source coverage changed")
        return dict(
            elapsed_seconds=elapsed,
            outbound_calls=calls - before_calls,
            client_creations=creations - before_clients,
            coverage_count=len(selected),
            coverage_unique_sources=len({item["url"] for item in selected}),
            coverage_hash=hashlib.sha256(json.dumps(selected, sort_keys=True).encode()).hexdigest(),
        )

    with patch("httpx.AsyncClient", make_client):
        baseline = await measure(FixtureOrchestrator(None))
        runtime = AcquisitionRuntime(
            AcquisitionPolicy(concurrency=4, provider_concurrency=2, minimum_interval_seconds=0.1),
            validator=lambda url: url,
        )
        try:
            orch = FixtureOrchestrator(runtime)
            cold = await measure(orch)
            warm = await measure(orch)
        finally:
            await runtime.aclose()
    return dict(baseline=baseline, bounded_cold=cold, bounded_warm=warm)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=Path, default=Path("benchmarks/data/research/acquisition_fixture.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=3, choices=range(1, 6))
    args = parser.parse_args()
    raw = args.pool.read_bytes()
    pool = json.loads(raw)
    samples = [asyncio.run(replay(pool)) for _ in range(args.repeats)]
    result = dict(
        schema_version=1,
        observed_at=datetime.now(UTC).isoformat(),
        scope="offline mechanical HTTP fixture",
        independent_quality_calibration=False,
        dataset=str(args.pool),
        dataset_sha256=hashlib.sha256(raw).hexdigest(),
        samples=samples,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
