"""Bounded NVIDIA research comparison with frozen retrieval and real pipeline phases.

Captured snippets are replayed, never described as full papers or live web retrieval.
Private checkpoints contain the outputs needed for later human support review.
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import statistics
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx

from backend.core.logging_config import SecretMaskingFilter
from backend.modules.llm_http import OpenAICompatibleProvider
from backend.modules.llm_protocol import BaseLLMProvider
from backend.services.research.acquisition import AcquisitionRuntime
from backend.services.research.orchestrator import SomaticResearchOrchestrator
from backend.storage.database import init_db
from backend.storage.migrations import run_all_migrations
from backend.storage.repositories.research.research_plan import ResearchPlanRepository
from backend.storage.repositories.research.research_step import ResearchStepRepository
from backend.storage.repositories.research.research_step_result import ResearchStepResultRepository
from backend.storage.repositories.research.research_task import ResearchTaskRepository


def summarize(rows):
    arms = {}
    for arm in ("legacy", "v2"):
        trials = [row for row in rows if row["arm"] == arm]
        durations = [row["elapsed_seconds"] for row in trials if "elapsed_seconds" in row]
        usage = [call.get("usage") for row in trials for call in row["provider_calls"]]
        totals = [
            value["total_tokens"]
            for value in usage
            if isinstance(value, dict) and type(value.get("total_tokens")) is int
        ]
        arms[arm] = {
            "trials": len(trials),
            "operationally_valid": sum(bool(row.get("operationally_valid")) for row in trials),
            "provider_calls": sum(len(row["provider_calls"]) for row in trials),
            "provider_failures": sum(call["status"] == "failed" for row in trials for call in row["provider_calls"]),
            "provider_incomplete": sum(
                call["status"] in {"started", "cancelled"} for row in trials for call in row["provider_calls"]
            ),
            "provider_truncations": sum(
                call["status"] == "truncated" for row in trials for call in row["provider_calls"]
            ),
            "median_pipeline_seconds": statistics.median(durations) if durations else None,
            "usage_reported_calls": len(totals),
            "reported_total_tokens": sum(totals) if totals else None,
            "degraded_trials": sum(bool(row.get("delivery_degraded")) for row in trials),
        }
    return {
        "arms": arms,
        "scope": "bounded pipeline with frozen snippet retrieval",
        "independent_quality": None,
        "known_cost_usd": None,
        "quality_ranking_allowed": False,
    }


class ObservedProvider(BaseLLMProvider):
    """Independent leaf observations keep swallowed upstream errors visible."""

    def __init__(self, provider, interval=5):
        self.provider = provider
        self.interval = interval
        self.calls = []
        self.lock = asyncio.Lock()
        self.checkpoint = None
        self.permanent_failure = False

    @property
    def provider_name(self):
        return "nvidia"

    @property
    def model_id(self):
        return getattr(self.provider, "model_id", "fixture")

    async def validate_connection(self):
        return await self.provider.validate_connection()

    async def generate(self, messages, **params):
        async with self.lock:
            if self.permanent_failure:
                raise RuntimeError("Benchmark provider unavailable; further calls stopped")
            if len(self.calls) >= 20:
                raise RuntimeError("Benchmark call cap reached")
            if self.calls:
                await asyncio.sleep(self.interval)
            params["max_tokens"] = min(params.get("max_tokens") or 4096, 4096)
            params["thinking_override"] = False
            row = {
                "prompt_sha256": hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest(),
                "requested_controls": params,
                "status": "started",
            }
            self.calls.append(row)
            started = time.perf_counter()
            try:
                result = await self.provider.generate(messages, **params)
                row.update(
                    status="truncated" if result.get("truncated") else "complete",
                    finish_reason=result.get("finish_reason"),
                    usage=result.get("usage"),
                    content=result.get("content"),
                    generation_controls=result.get("generation_controls"),
                )
                return result
            except asyncio.CancelledError:
                row.update(status="cancelled", error_type="CancelledError")
                raise
            except Exception as exc:
                # Benchmark observation re-raises every provider failure; no silent fallback here.
                row.update(status="failed", error_type=type(exc).__name__)
                if isinstance(exc, httpx.HTTPStatusError):
                    row["http_status"] = exc.response.status_code
                    self.permanent_failure = exc.response.status_code in {401, 403, 404, 410}
                raise
            finally:
                row["elapsed_seconds"] = time.perf_counter() - started
                if self.checkpoint is not None:
                    await asyncio.to_thread(self.checkpoint)


async def run_arm(case, arm, provider, db_path, checkpoint):
    def initialize():
        conn = init_db(str(db_path))
        try:
            run_all_migrations(conn)
        finally:
            conn.close()

    await asyncio.to_thread(initialize)
    tasks = ResearchTaskRepository(str(db_path))
    task_id = f"{case['id']}-{arm}"
    await asyncio.to_thread(
        tasks.create,
        dict(
            id=task_id,
            title="Live comparison",
            objective=case["objective"],
            trigger_source="user_console",
            status="active",
            priority=1,
            max_depth=1,
            max_breadth=1,
            budget_limit_usd=0.5,
            subresearch_policy="off",
        ),
    )
    observed = ObservedProvider(provider, interval=0 if provider.provider_name == "fixture" else 5)
    app = SimpleNamespace(
        config={
            "research_orchestrator": {
                "action_receipts_enabled": arm == "v2",
                "max_queries": 1,
                "default_top_n": 2,
                "html_archive": False,
                "provider_limits": {
                    "task_timeout_seconds": 600,
                    "attempt_timeout_seconds": 45,
                    "max_request_attempts": 1,
                    "max_task_attempts": 20,
                },
            },
            "research_triage": {"enabled": False},
        },
        research_task_repo=tasks,
        research_plan_repo=ResearchPlanRepository(str(db_path)),
        research_step_repo=ResearchStepRepository(str(db_path)),
        research_step_result_repo=ResearchStepResultRepository(str(db_path)),
        research_meta_log_repo=None,
        llm_provider=observed,
        structural_provider=None,
    )
    orch = SomaticResearchOrchestrator(app)
    await asyncio.to_thread(orch.init_task, task_id)
    orch._build_orchestrator_persona = AsyncMock(return_value="Evaluate the supplied evidence and name uncertainty.")
    orch._metabolize_step = AsyncMock()  # Identical exclusion of indexing/persona work in both arms.
    pool = case["sources"][:2]

    async def search(*args, **kwargs):
        return pool

    async def fetch(url_or_query, **kwargs):
        source = next((source for source in pool if source["url"] == url_or_query), None)
        if source is None:
            raise ValueError("Requested source is unavailable in frozen replay pool")
        return source["snippet"]

    def frozen_url(url):
        if url in {source["url"] for source in pool} or url.startswith("https://lite.duckduckgo.com/lite/?q="):
            return url
        raise ValueError("URL outside frozen replay pool")

    def replay_runtime(policy, **kwargs):
        return AcquisitionRuntime(policy, validator=frozen_url, **kwargs)

    row = {
        "case_id": case["id"],
        "arm": arm,
        "steps": [],
        "provider_calls": observed.calls,
        "retrieval": "frozen_snippets",
        "available_source_ids": [s["id"] for s in pool],
        "independent_quality": None,
        "known_cost_usd": None,
    }
    observed.checkpoint = lambda: checkpoint(row)
    started = time.perf_counter()
    try:
        with (
            patch("backend.services.research.orchestrator.validate_safe_url", frozen_url),
            patch("backend.services.research.orchestrator.AcquisitionRuntime", replay_runtime),
            patch(
                "backend.services.research.context_builder.ResearchContextBuilder.build_node_context",
                AsyncMock(return_value="Evaluate supplied evidence and uncertainty."),
            ),
            patch("backend.services.research.steps.search.web_search", search),
            patch("backend.services.research.steps.parse.select_and_fetch", fetch),
            patch("backend.services.research.steps.parse.is_crawl4ai_available", return_value=False),
        ):
            for _ in range(24):
                result = await orch.execute_step(task_id)
                row["steps"].append({k: result.get(k) for k in ("phase", "next_phase", "status", "stop_reason")})
                await asyncio.to_thread(checkpoint, row)
                if observed.permanent_failure:
                    row["stop_reason"] = "provider_unavailable"
                    break
                if result.get("next_phase") == "complete" or result.get("status") in {"failed", "partial", "cancelled"}:
                    break
            else:
                row["stop_reason"] = "benchmark_step_cap"
        task = await asyncio.to_thread(tasks.get, task_id)
        row.update(
            task_status=task["status"],
            branches_created=task.get("branches_created"),
            sources_analyzed=task.get("assets_harvested"),
            stop_reason=row.get("stop_reason") or orch._get_state(task_id).get("stop_reason"),
            pipeline_phase=orch._get_state(task_id).get("phase"),
            delivery_degraded=orch._get_state(task_id).get("delivery_degraded", False),
            first_useful_result_seconds=orch._get_state(task_id).get("first_useful_result_seconds"),
            result_summary=task.get("result_summary"),
            elapsed_seconds=time.perf_counter() - started,
        )
        row["operationally_valid"] = (
            bool(row["provider_calls"])
            and all(c["status"] == "complete" for c in row["provider_calls"])
            and bool(row.get("result_summary"))
            and row.get("pipeline_phase") == "complete"
            and not row.get("delivery_degraded")
            and row.get("stop_reason") != "benchmark_step_cap"
            and row.get("stop_reason") != "provider_unavailable"
        )
    except (OSError, RuntimeError, ValueError) as exc:
        row.update(
            task_status="failed",
            operationally_valid=False,
            error_type=type(exc).__name__,
            elapsed_seconds=time.perf_counter() - started,
        )
    finally:
        await orch.aclose()
        await asyncio.to_thread(checkpoint, row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cases", type=int, choices=(1, 2), default=1)
    parser.add_argument("--model", default="nvidia/nemotron-3-super-120b-a12b")
    args = parser.parse_args()
    from dotenv import load_dotenv

    load_dotenv(args.env_file, override=False)
    logging.basicConfig(level=logging.WARNING)
    for handler in logging.getLogger().handlers:
        handler.addFilter(SecretMaskingFilter())
    key = os.environ.get("AAA_NVIDIA_API_KEY")
    if not key:
        parser.error("NVIDIA credential required")
    raw = args.dataset.read_bytes()
    cases = [c for c in json.loads(raw)["cases"] if c["split"] == "heldout"][: args.cases]
    if len(cases) != args.cases or any(not c.get("source_pool_complete") for c in cases):
        parser.error("Complete frozen pools required")
    args.output.mkdir(parents=True, exist_ok=False)
    metadata = {
        "dataset_sha256": hashlib.sha256(raw).hexdigest(),
        "provider": "nvidia",
        "model": args.model,
        "scope": "real pipeline phases; frozen retrieval of two snippets per case",
        "excluded": ["live web retrieval", "full document parsing", "persona generation", "indexing", "branching"],
        "quality_basis": "user_authorized_assumption",
        "independent_quality": None,
        "known_cost_usd": None,
        "max_calls_per_arm": 20,
        "max_tokens_per_call": 4096,
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    rows = []

    def checkpoint(row):
        if args.dataset.read_bytes() != raw:
            raise ValueError("Frozen dataset changed")
        current = rows + [row]
        temporary = args.output / "telemetry_receipts.json.tmp"
        temporary.write_text(json.dumps(current, indent=2, default=str), encoding="utf-8")
        temporary.replace(args.output / "telemetry_receipts.json")

    provider = OpenAICompatibleProvider(
        api_key=key,
        model=args.model,
        api_base="https://integrate.api.nvidia.com/v1",
        provider_name="nvidia",
        thinking=False,
        max_retries=0,
        timeout=40,
        default_params={"max_tokens": 4096, "temperature": 0.4},
    )

    async def execute():
        for index, case in enumerate(cases):
            for arm in ("legacy", "v2") if index % 2 == 0 else ("v2", "legacy"):
                row = await run_arm(case, arm, provider, args.output / f"{case['id']}-{arm}.db", checkpoint)
                rows.append(row)
                print(
                    json.dumps({"arm": arm, "status": row["task_status"], "calls": len(row["provider_calls"])}),
                    flush=True,
                )
        return rows

    try:
        asyncio.run(asyncio.wait_for(execute(), timeout=1800))
    except TimeoutError:
        rows = json.loads((args.output / "telemetry_receipts.json").read_bytes())
        metadata["stop_reason"] = "benchmark_total_deadline"
        (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (args.output / "telemetry_receipts.json").write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
    summary = summarize(rows)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report = "# NVIDIA research pipeline comparison\n\nFrozen snippets; quality and billing are unverified.\n\n"
    for arm, values in summary["arms"].items():
        report += f"- {arm}: {values['operationally_valid']}/{values['trials']} operationally valid; {values['provider_calls']} calls; {values['provider_failures']} failures; median {values['median_pipeline_seconds']} seconds.\n"
    report += "\nThis bounded run excludes live web retrieval, full documents, persona generation, indexing, branching and queue lifecycle. It cannot establish superior research quality.\n"
    (args.output / "summary.md").write_text(report, encoding="utf-8")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
