"""Run offline payload/projection comparisons; temporary synthetic DB, aggregate output."""

import json
import platform
import resource
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmarks.fixtures.message_history_v1 import MessageHistoryRepository as ReferenceHistory
from benchmarks.fixtures.navigation_queries import history, skills


def measure(call):
    call()  # warmup excluded
    times = []
    for _ in range(20):
        start = time.perf_counter()
        value = call()
        times.append(time.perf_counter() - start)
    return value, {"median_seconds": statistics.median(times), "p95_seconds": sorted(times)[18]}


def volume(rows):
    return sum(len(v) for row in rows for v in row.values() if isinstance(v, str))


service = skills()
full, ft = measure(lambda: service._get_skills())
compact, ct = measure(lambda: service._get_skills(False))
result = {
    "python": platform.python_version(),
    "samples": 20,
    "warmup": 1,
    "skills": {
        "count": 89,
        "full_bytes": len(json.dumps(full).encode()),
        "compact_bytes": len(json.dumps(compact).encode()),
        "full": ft,
        "compact": ct,
    },
}
with tempfile.TemporaryDirectory(prefix="aaa-navigation-") as directory:
    path = Path(directory) / "fixture.db"
    repo = history(path)
    reference = ReferenceHistory(str(path))
    old, ot = measure(lambda: reference.get_recent_with_metrics(limit=50, conversation_id="fixture"))
    new, nt = measure(lambda: repo.get_recent_with_metrics(limit=50, conversation_id="fixture"))
    result["history"] = {
        "count": 50,
        "full_string_chars": volume(old),
        "compact_string_chars": volume(new),
        "full": ot,
        "compact": nt,
    }
result["peak_process_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
print(json.dumps(result, indent=2))
