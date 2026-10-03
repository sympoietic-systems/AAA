"""Real query annotation packets, raw pool acquisition and frozen offline comparisons."""

import argparse
import asyncio
import json
import random
import sqlite3
import statistics
from collections import Counter
from contextlib import closing
from pathlib import Path

from backend.bootstrap.providers import _create_provider
from backend.config import load_config
from backend.core.logging_config import mask_secrets
from backend.modules.providers.typesafe_provider import TypeSafeDecisionClient
from backend.modules.retrieval.web_retrieval import RhizomeWebProbe
from backend.modules.sensory.evidence_triage import EvidenceTriage
from benchmarks.suites.calibration_contract import digest, reviewed_label, validate_splits
from benchmarks.suites.research_selection import compare_selection
from benchmarks.suites.research_triage import CASES

ARMS = ("legacy", "combined", "separate_axes")


def prepare(database: Path, count: int = 100) -> dict:
    if not 1 <= count <= 200:
        raise ValueError("packet size must be 1..200")
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("BEGIN")
        tasks = dict(conn.execute("SELECT id,objective FROM research_tasks"))
        queries = conn.execute(
            "SELECT DISTINCT task_id,query_text FROM research_steps WHERE query_text IS NOT NULL AND query_text!=''"
        ).fetchall()
    families = sorted(tasks, key=digest)
    split = {
        task: ("tune" if i < len(families) * 0.2 else "validation" if i < len(families) * 0.4 else "heldout")
        for i, task in enumerate(families)
    }
    cases, seen = [], set()
    for task, query in sorted(queries, key=lambda pair: digest(pair)):
        query = mask_secrets(query)[:500]
        if query in seen:
            continue
        seen.add(query)
        cases.append(
            {
                "id": digest([task, query])[:20],
                "split": split[task],
                "split_entities": [task],
                "objective": mask_secrets(tasks[task])[:2000],
                "query": query,
                "sources": [],
                "annotations": [],
                "target_count": 3,
                "source_pool_complete": False,
                "source_kind": "real_query_history",
            }
        )
    validate_splits(cases)
    return {
        "schema_version": 1,
        "source": str(database),
        "cases": cases[:count],
        "available_distinct_queries": len(seen),
        "promotion": "BLOCKED",
        "note": "Historical search caches contain selected survivors, so they cannot reconstruct raw candidate pools.",
    }


async def acquire(packet: dict, search, limit: int = 10) -> dict:
    if not 1 <= limit <= 100:
        raise ValueError("acquisition budget must be 1..100")
    semaphore = asyncio.Semaphore(2)
    cases = json.loads(json.dumps(packet["cases"]))
    if not 1 <= len(cases) <= 200:
        raise ValueError("packet size must be 1..200")

    async def collect(case):
        async with semaphore:
            try:
                raw = await asyncio.wait_for(search(case["query"]), timeout=30)
            except (TimeoutError, OSError, ValueError) as error:
                case["acquisition"] = {"status": "unavailable", "error_type": type(error).__name__}
                return
            sources = []
            for source in raw[:10]:
                cleaned = {
                    k: mask_secrets(str(source.get(k, "")))[:bound]
                    for k, bound in [("url", 500), ("title", 300), ("snippet", 1000)]
                }
                cleaned["id"] = digest(cleaned)[:20]
                if cleaned["id"] not in {s["id"] for s in sources}:
                    sources.append(cleaned)
            case.update(sources=sources, source_pool_complete=bool(sources), annotations=[])
            case["acquisition"] = {
                "status": "captured" if sources else "empty_or_unavailable",
                "observed_count": len(raw),
                "candidate_budget": 10,
                "raw_before_selection": True,
            }

    await asyncio.gather(*(collect(c) for c in cases[:limit]))
    return {
        **packet,
        "cases": cases,
        "frozen": False,
        "acquired_queries": sum(c.get("source_pool_complete", False) for c in cases),
    }


def validate_gold(case, gold):
    if not 1 <= len(case["sources"]) <= 10 or len({s["id"] for s in case["sources"]}) != len(case["sources"]):
        raise ValueError("one to ten uniquely identified sources required")
    if not isinstance(gold, dict) or set(gold) != {s["id"] for s in case["sources"]}:
        raise ValueError("independent per-source labels required")
    for value in gold.values():
        if (
            not isinstance(value, dict)
            or type(value.get("relevant")) is not bool
            or not isinstance(value.get("quality"), str)
            or value.get("quality") not in {"adequate", "weak", "unknown"}
            or type(value.get("contrary")) is not bool
            or type(value.get("injection")) is not bool
        ):
            raise ValueError("invalid relevance/quality/contrary/injection labels")


def freeze(packet):
    if not 1 <= len(packet["cases"]) <= 200:
        raise ValueError("packet size must be 1..200")
    validate_splits(packet["cases"])
    for case in packet["cases"]:
        gold, reason = reviewed_label(case)
        if not case.get("source_pool_complete"):
            raise ValueError("raw candidate pool required")
        if reason == "annotator_disagreement":
            continue
        validate_gold(case, gold)
    return {**packet, "frozen": True, "frozen_sha256": digest(packet["cases"])}


def score(rows):
    valid = [r for r in rows if r["selection"]["receipt"].get("status") in {"evaluated", "selected", "passthrough"}]
    precision, recall, contrary = [], [], []
    injections = 0
    for row in valid:
        gold = row["gold"]
        selected = set(row["selection"]["selected_ids"])
        eligible = {i for i, v in gold.items() if v["relevant"] and v["quality"] == "adequate" and not v["injection"]}
        negative = {i for i in eligible if gold[i]["contrary"]}
        precision.append(len(selected & eligible) / len(selected) if selected else 0)
        if eligible:
            recall.append(len(selected & eligible) / len(eligible))
        if negative:
            contrary.append(len(selected & negative) / len(negative))
        injections += sum(gold[i]["injection"] for i in selected)
    return {
        "trials": len(rows),
        "valid_trials": len(valid),
        "unique_queries": len({r["id"] for r in rows}),
        "mean_precision": sum(precision) / len(precision) if precision else None,
        "mean_recall": sum(recall) / len(recall) if recall else None,
        "contrary_retention": sum(contrary) / len(contrary) if contrary else None,
        "injected_sources_selected": injections,
        "excluded_nonvalid_trials": len(rows) - len(valid),
        "execution_failures": sum(r["selection"]["receipt"].get("status") == "unavailable" for r in rows),
        "status_counts": dict(Counter(r["selection"]["receipt"].get("status", "unknown") for r in rows)),
        "promotion": "BLOCKED",
        "median_latency_ms": statistics.median(r["selection"]["latency_ms"] for r in rows) if rows else None,
        "downstream_citation_correctness": "NOT RUN",
        "task_usefulness": "NOT RUN",
    }


def paired_precision(rows, candidate):
    """Cluster bootstrap by task family; repeat trials never become independent queries."""
    grouped = {}
    for row in rows:
        key = (row["id"], row["arm"])
        grouped.setdefault(key, []).append(row)
    families = {}
    for identifier in {row["id"] for row in rows}:
        arms = [grouped.get((identifier, arm), []) for arm in ("legacy", candidate)]
        if any(
            not trials
            or any(
                r["selection"]["receipt"].get("status") not in {"evaluated", "selected", "passthrough"} for r in trials
            )
            for trials in arms
        ):
            continue
        difference = score(arms[1])["mean_precision"] - score(arms[0])["mean_precision"]
        family = tuple(arms[0][0].get("family", [identifier]))
        families.setdefault(family, []).append(difference)
    values = [statistics.mean(deltas) for deltas in families.values()]
    if not values:
        return {"paired_families": 0, "delta": None, "ci95": None}
    rng = random.Random(20261003)
    samples = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(1000))
    return {
        "paired_families": len(values),
        "delta": statistics.mean(values),
        "ci95": [samples[24], samples[974]],
        "method": "task-family cluster bootstrap; descriptive small samples",
    }


async def evaluate(packet, triage, provider, repeats=3, synthetic=False):
    if not 1 <= len(packet["cases"]) <= 200 or not 1 <= repeats <= 3:
        raise ValueError("bounded corpus and repeat budget required")
    validate_splits(packet["cases"])
    if packet.get("frozen") and packet.get("frozen_sha256") != digest(packet["cases"]):
        raise ValueError("frozen dataset changed")
    rows, pending = [], []
    for case in packet["cases"]:
        if case["split"] != "heldout":
            continue
        gold, reason = (case.get("fixture_gold"), None) if synthetic else reviewed_label(case)
        if (
            not case.get("source_pool_complete")
            or (not synthetic and not packet.get("frozen"))
            or not isinstance(gold, dict)
        ):
            pending.append({"id": case["id"], "reason": reason or "raw_pool_labels_and_freeze_required"})
            continue
        validate_gold(case, gold)
        for repeat in range(repeats):
            sources = case["sources"] if repeat % 2 == 0 else list(reversed(case["sources"]))
            for arm in ARMS:
                selected = await compare_selection(case, triage, provider, arm, sources)
                rows.append(
                    {
                        "id": case["id"],
                        "family": case["split_entities"],
                        "repeat": repeat,
                        "arm": arm,
                        "gold": gold,
                        "selection": selected,
                    }
                )
    return {
        "dataset_sha256": digest(packet),
        "purpose": "synthetic regression" if synthetic else "independent held-out comparison",
        "rows": rows,
        "pending": pending,
        "scores": {arm: score([r for r in rows if r["arm"] == arm]) for arm in ARMS},
        "paired_precision": {arm: paired_precision(rows, arm) for arm in ARMS[1:]},
        "promotion": "BLOCKED",
    }


def sentinels():
    cases = []
    for case in CASES:
        sources = [{**s, "id": digest(s)[:20]} for s in case["sources"]]
        gold = {
            s["id"]: {
                "relevant": s["url"] == case["expected"],
                "quality": "adequate" if s["url"] == case["expected"] else "weak",
                "contrary": case["id"] == "negative" and s["url"] == case["expected"],
                "injection": case["id"] == "injection" and s["url"] != case["expected"],
            }
            for s in sources
        }
        cases.append(
            {
                **case,
                "sources": sources,
                "query": case["objective"],
                "split": "heldout",
                "split_entities": [case["id"]],
                "source_pool_complete": True,
                "target_count": 1,
                "fixture_gold": gold,
            }
        )
    return {"cases": cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", type=Path)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--freeze", type=Path)
    parser.add_argument("--sentinels", action="store_true")
    parser.add_argument("--acquire", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sum([bool(args.prepare), bool(args.dataset), bool(args.freeze), args.sentinels]) != 1 or (
        args.acquire and not args.dataset
    ):
        parser.error("choose one operation; acquire requires dataset")
    if args.output.exists():
        parser.error("output must be fresh")
    if args.prepare:
        result = prepare(args.prepare, args.count)
    elif args.freeze:
        result = freeze(json.loads(args.freeze.read_text(encoding="utf-8")))
    else:
        packet = sentinels() if args.sentinels else json.loads(args.dataset.read_text(encoding="utf-8"))
        if args.acquire:
            result = asyncio.run(acquire(packet, RhizomeWebProbe(None, None, None).search, args.limit))
        else:
            config = load_config(args.config) if args.config else {}
            triage = EvidenceTriage(TypeSafeDecisionClient.from_config(config.get("typesafe", {})))
            provider = _create_provider(config.get("llm", {})) if args.config else None
            result = asyncio.run(evaluate(packet, triage, provider, args.repeats, args.sentinels))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
