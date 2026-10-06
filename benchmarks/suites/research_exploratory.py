"""Checkpointed selection comparison against provisional labels, never independent gold."""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import statistics
from collections import Counter
from pathlib import Path

from backend.config import load_config
from backend.core.logging_config import SecretMaskingFilter
from backend.modules.llm_http import OpenAICompatibleProvider
from backend.modules.providers.typesafe_provider import TypeSafeDecisionClient
from backend.modules.sensory.evidence_triage import EvidenceTriage
from benchmarks.suites.calibration_contract import validate_splits
from benchmarks.suites.research_calibration import validate_gold
from benchmarks.suites.research_selection import compare_selection

ARMS = ("legacy", "combined", "separate_axes")
VALID = {"evaluated", "selected", "passthrough"}


def summarize(rows):
    summaries = {}
    for arm in ARMS:
        trials = [r for r in rows if r["arm"] == arm]
        valid = [r for r in trials if r["selection"]["receipt"].get("status") in VALID]
        agreement, contrary = [], []
        for row in valid:
            labels = row["reference_labels"]
            selected = set(row["selection"]["selected_ids"])
            relevant = {identifier for identifier, label in labels.items() if label["relevant"]}
            opposing = {identifier for identifier in relevant if labels[identifier]["contrary"]}
            agreement.append(len(selected & relevant) / len(selected) if selected else 0)
            if opposing:
                contrary.append(len(selected & opposing) / len(opposing))
        summaries[arm] = {
            "attempts": len(trials),
            "valid_selections": len(valid),
            "status_counts": dict(Counter(r["selection"]["receipt"].get("status", "unknown") for r in trials)),
            "provisional_relevance_fraction": statistics.mean(agreement) if agreement else None,
            "provisional_contrary_retention": statistics.mean(contrary) if contrary else None,
            "median_attempt_latency_ms": statistics.median(r["selection"]["latency_ms"] for r in trials)
            if trials
            else None,
            "unique_queries": len({r["id"] for r in trials}),
            "task_families": len({tuple(r["family"]) for r in trials}),
        }
    return {
        "arms": summaries,
        "promotion": "BLOCKED",
        "independent_quality": None,
        "downstream_support_review": "not_run",
        "known_cost_usd": None,
    }


async def run(packet, triage, provider, checkpoint, repeats=3):
    validate_splits(packet["cases"])
    if not 1 <= len(packet["cases"]) <= 200 or not 1 <= repeats <= 3:
        raise ValueError("bounded packet/repeats required")
    rows = []
    for case in packet["cases"]:
        if case["split"] != "heldout":
            continue
        annotations = [a for a in case.get("annotations", []) if a.get("method") == "model_provisional"]
        if not annotations or not case.get("source_pool_complete"):
            raise ValueError("captured pool and provisional annotation required")
        labels = annotations[-1]["label"]
        validate_gold(case, labels)  # Shape validation only; does not establish independent gold.
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
                        "reference_labels": labels,
                        "reference_method": "model_provisional",
                        "selection": selected,
                    }
                )
                checkpoint(rows)
                print(
                    json.dumps(
                        {
                            "case_id": case["id"],
                            "repeat": repeat,
                            "arm": arm,
                            "status": selected["receipt"].get("status"),
                        }
                    ),
                    flush=True,
                )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("fresh output required")
    from dotenv import load_dotenv

    load_dotenv(args.env_file, override=False)
    logging.basicConfig(level=logging.WARNING)
    for handler in logging.getLogger().handlers:
        handler.addFilter(SecretMaskingFilter())
    config = load_config(args.config)
    client = TypeSafeDecisionClient.from_config(config.get("typesafe", {}))
    if not client.is_configured or not os.environ.get("AAA_NVIDIA_API_KEY"):
        parser.error("configured Jev and NVIDIA credentials required")
    provider = OpenAICompatibleProvider(
        api_key=os.environ["AAA_NVIDIA_API_KEY"],
        model="nvidia/nemotron-3-ultra-550b-a55b",
        api_base="https://integrate.api.nvidia.com/v1",
        provider_name="nvidia",
        thinking=False,
        max_retries=0,
        timeout=40,
        default_params={"max_tokens": 1500, "temperature": 0},
    )
    raw = args.dataset.read_bytes()
    packet = json.loads(raw)
    args.output.mkdir(parents=True)
    metadata = {
        "purpose": "provisional exploration",
        "dataset_sha256": hashlib.sha256(raw).hexdigest(),
        "repeats": 3,
        "baseline_provider": "nvidia",
        "jev_model": client.model,
        "independent_gold": False,
        "promotion": "BLOCKED",
    }
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    def checkpoint(rows):
        if args.dataset.read_bytes() != raw:
            raise ValueError("dataset changed during comparison")
        for name, data in (("telemetry_receipts.json", rows), ("summary.json", summarize(rows))):
            temporary = args.output / (name + ".tmp")
            temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            temporary.replace(args.output / name)

    async def execute():
        return await asyncio.wait_for(run(packet, EvidenceTriage(client), provider, checkpoint), timeout=1800)

    rows = asyncio.run(execute())
    checkpoint(rows)
    print(json.dumps(summarize(rows)), flush=True)


if __name__ == "__main__":
    main()
