"""Benchmark script for measuring AAA backend resource usage.

Measures:
1. Config load speed & repeated parse overhead
2. Database connection churn under repeated queries
3. PyTorch thread saturation & embedding latency / CPU utilization
4. Event loop responsiveness / jitter during queries
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import psutil
import torch
from backend.config import load_config
from backend.modules.embedder import EmbeddingService
from backend.storage.database import get_db_path, init_db
from backend.storage.repositories.notification import NotificationRepository
from backend.storage.repositories.message import MessageRepository


def benchmark_config(iterations=100) -> dict:
    start = time.perf_counter()
    for _ in range(iterations):
        cfg = load_config()
    elapsed = time.perf_counter() - start
    return {
        "iterations": iterations,
        "total_seconds": round(elapsed, 4),
        "avg_ms_per_call": round((elapsed / iterations) * 1000, 3),
    }


def benchmark_database(iterations=200) -> dict:
    cfg = load_config()
    db_path = str(get_db_path(cfg.get("database", {}).get("path", "data/aaa.db")))
    init_db(db_path)
    repo = NotificationRepository(db_path)

    start = time.perf_counter()
    for _ in range(iterations):
        repo.list_all(limit=50, dismissed=False)
    elapsed = time.perf_counter() - start
    return {
        "iterations": iterations,
        "total_seconds": round(elapsed, 4),
        "ops_per_sec": round(iterations / elapsed, 1),
        "avg_ms_per_call": round((elapsed / iterations) * 1000, 3),
    }


def benchmark_embeddings(num_sentences=30) -> dict:
    service = EmbeddingService(offline=True)
    service.load()

    active_torch_threads = torch.get_num_threads()
    interop_threads = torch.get_num_interop_threads()

    texts = [
        f"Cybernetic autopoiesis iteration {i} examining recursive feedback loops, homeostasis, and variety filtering."
        for i in range(num_sentences)
    ]

    process = psutil.Process()
    # Baseline CPU
    _ = process.cpu_percent(interval=None)

    start_cpu_time = process.cpu_times()
    start_wall = time.perf_counter()

    for text in texts:
        _ = service.encode(text)

    end_wall = time.perf_counter()
    end_cpu_time = process.cpu_times()

    wall_duration = end_wall - start_wall
    user_cpu_consumed = end_cpu_time.user - start_cpu_time.user
    system_cpu_consumed = end_cpu_time.system - start_cpu_time.system
    total_cpu_time = user_cpu_consumed + system_cpu_consumed
    # CPU Core multiplier = total CPU time / wall duration (e.g., 8.0 = 8 full cores pegged at 100%)
    core_saturation = round(total_cpu_time / max(wall_duration, 0.001), 2)

    return {
        "sentences_encoded": num_sentences,
        "wall_time_seconds": round(wall_duration, 4),
        "avg_ms_per_sentence": round((wall_duration / num_sentences) * 1000, 2),
        "cpu_user_seconds": round(user_cpu_consumed, 3),
        "cpu_system_seconds": round(system_cpu_consumed, 3),
        "core_saturation_multiplier": core_saturation,
        "torch_intraop_threads": active_torch_threads,
        "torch_interop_threads": interop_threads,
    }


async def benchmark_event_loop_jitter(iterations=50) -> dict:
    """Measures event loop delay/jitter while running queries."""
    cfg = load_config()
    db_path = str(get_db_path(cfg.get("database", {}).get("path", "data/aaa.db")))
    repo = NotificationRepository(db_path)

    jitter_delays = []

    async def heartbeat():
        for _ in range(iterations):
            t0 = time.perf_counter()
            await asyncio.sleep(0.01)  # 10ms expected
            t1 = time.perf_counter()
            delay = (t1 - t0) - 0.01
            jitter_delays.append(max(0.0, delay))

    async def work():
        # Simulated route calls that do synchronous DB work
        for _ in range(iterations):
            repo.list_all(limit=50, dismissed=False)
            await asyncio.sleep(0.001)

    t_start = time.perf_counter()
    await asyncio.gather(heartbeat(), work())
    t_total = time.perf_counter() - t_start

    avg_jitter_ms = (sum(jitter_delays) / len(jitter_delays)) * 1000 if jitter_delays else 0
    max_jitter_ms = max(jitter_delays) * 1000 if jitter_delays else 0

    return {
        "iterations": iterations,
        "total_seconds": round(t_total, 4),
        "avg_loop_delay_ms": round(avg_jitter_ms, 3),
        "max_loop_freeze_ms": round(max_jitter_ms, 3),
    }


def main():
    print("=" * 60)
    print("  AAA BACKEND RESOURCE BENCHMARK")
    print("=" * 60)

    print("\n1. Benchmarking Config Loading...")
    cfg_res = benchmark_config()
    print(f"   Config (100 loads): {cfg_res['total_seconds']}s total, {cfg_res['avg_ms_per_call']} ms/call")

    print("\n2. Benchmarking Database Connections & Queries...")
    db_res = benchmark_database()
    print(f"   DB (200 queries): {db_res['total_seconds']}s total, {db_res['ops_per_sec']} ops/sec, {db_res['avg_ms_per_call']} ms/query")

    print("\n3. Benchmarking Embedding Model & CPU Saturation...")
    emb_res = benchmark_embeddings()
    print(f"   Torch intra-op threads: {emb_res['torch_intraop_threads']}")
    print(f"   Torch inter-op threads: {emb_res['torch_interop_threads']}")
    print(f"   30 Embeddings Wall Time: {emb_res['wall_time_seconds']}s ({emb_res['avg_ms_per_sentence']} ms/sentence)")
    print(f"   CPU Time Consumed: {round(emb_res['cpu_user_seconds'] + emb_res['cpu_system_seconds'], 2)}s")
    print(f"   Core Saturation Multiplier: {emb_res['core_saturation_multiplier']}x (cores concurrently saturated)")

    print("\n4. Benchmarking Event Loop Responsiveness / Jitter...")
    loop_res = asyncio.run(benchmark_event_loop_jitter())
    print(f"   Event Loop Average Delay: {loop_res['avg_loop_delay_ms']} ms (ideal: ~0 ms)")
    print(f"   Event Loop Max Freeze: {loop_res['max_loop_freeze_ms']} ms")

    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY (RAW JSON):")
    import json
    summary = {
        "config": cfg_res,
        "database": db_res,
        "embedding": emb_res,
        "event_loop": loop_res,
    }
    print(json.dumps(summary, indent=2))
    print("=" * 60)


if __name__ == "__main__":
    main()
