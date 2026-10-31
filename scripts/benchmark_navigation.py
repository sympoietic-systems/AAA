"""Measure navigation reads on a disposable snapshot; never alter the source database.

Run: python -m scripts.benchmark_navigation --database /path/to/aaa.db --samples 5
Only aggregate timings, counts and response sizes are emitted.
"""

import argparse
import asyncio
import json
import sqlite3
import statistics
import tempfile
import time
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

from backend.modules.belief_engine import BeliefDynamicsEngine
from backend.services.belief_query import BeliefQueryUseCases
from backend.storage.migrations.m070_belief_event_history_index import up
from backend.storage.repositories import BeliefRepository


def timings(call, samples):
    values = []
    for _ in range(samples):
        start = time.perf_counter()
        call()
        values.append(time.perf_counter() - start)
    return {"seconds": values, "median_seconds": statistics.median(values)}


async def payload_timings(query, samples):
    result = {}
    for name, call in (("full_beliefs", query.get_beliefs), ("health", query.get_health)):
        values = []
        size = 0
        for _ in range(samples):
            start = time.perf_counter()
            payload = await call()
            encoded = json.dumps(payload, default=str).encode()
            values.append(time.perf_counter() - start)
            size = len(encoded)
        result[name] = {"seconds": values, "median_seconds": statistics.median(values), "json_bytes": size}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--samples", type=int, choices=range(1, 21), default=5)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="aaa-navigation-") as directory:
        snapshot = Path(directory) / "snapshot.db"
        with (
            closing(sqlite3.connect(args.database.resolve().as_uri() + "?mode=ro", uri=True)) as source,
            closing(sqlite3.connect(snapshot)) as conn,
        ):
            source.backup(conn)
            repo = BeliefRepository(str(snapshot))
            beliefs = repo.list_beliefs("symbia")
            ids = [belief.id for belief in beliefs if belief.lifecycle_stage in ("crystallized", "senescence")]

            def histories():
                for belief_id in ids:
                    repo.get_events_for_belief(belief_id)

            conn.execute("DROP INDEX IF EXISTS idx_belief_events_belief_timestamp")
            conn.commit()
            baseline = timings(histories, args.samples)
            up(conn)
            conn.commit()
            indexed = timings(histories, args.samples)
            engine = BeliefDynamicsEngine.__new__(BeliefDynamicsEngine)
            engine._belief_repo = repo
            engine._beta = 0.05
            engine._source_weights = {}
            query = BeliefQueryUseCases()
            query._state = SimpleNamespace(belief_repo=repo, belief_metabolism=engine)
            result = {
                "scope": "local disposable database snapshot; not production latency",
                "samples": args.samples,
                "beliefs_with_histories": len(ids),
                "event_count": conn.execute("SELECT COUNT(*) FROM belief_events").fetchone()[0],
                "histories_without_index": baseline,
                "histories_with_index": indexed,
                "history_speedup": baseline["median_seconds"] / indexed["median_seconds"],
                "responses": asyncio.run(payload_timings(query, args.samples)),
            }
            print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
