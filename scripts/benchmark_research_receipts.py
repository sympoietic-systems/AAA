"""Offline receipt baseline. Fixture timings are not production performance."""

import argparse
import asyncio
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

from backend.services.research.orchestrator import SomaticResearchOrchestrator
from backend.services.research.provider_observation import generate_unified
from backend.services.research.steps.base import ResearchStepRegistry
from backend.services.research.task_state import ParsePayload, StepOutput
from backend.storage.database import init_db
from backend.storage.repositories.research.research_task import ResearchTaskRepository


class FixtureProvider:
    provider_name = "offline-fixture"

    async def generate(self, **kwargs):
        await asyncio.sleep(0)
        return {
            "content": "Fixture extracted text",
            "provider_used": self.provider_name,
            "model": "fixture",
            "finish_reason": "stop",
        }


class FixtureStep:
    async def execute(self, orch, envelope):
        await generate_unified(FixtureProvider(), user_prompt="fixture input")
        return StepOutput(
            payload=ParsePayload(parsed_sources=[{"source_id": "fixture", "content": "Fixture extracted text"}]),
            signal_flags={"has_parsed_content": True},
            step_ids=["fixture:parsed:1"],
        )


async def run(output: Path, repetitions: int):
    os.environ["AAA_RUN_MIGRATIONS"] = "true"
    samples = []
    original = ResearchStepRegistry.get_step
    try:
        ResearchStepRegistry.get_step = classmethod(lambda cls, phase: FixtureStep())
        with tempfile.TemporaryDirectory(prefix="aaa_receipt_baseline_") as temp:
            # ConnectionTracker closes test scopes immediately on Windows.
            path = str(Path(temp) / "baseline_test.db")
            init_db(path).close()
            repo = ResearchTaskRepository(path)
            for index in range(repetitions):
                task_id = f"fixture-{index}"
                repo.create(
                    {
                        "id": task_id,
                        "title": "Offline receipt baseline",
                        "objective": "Observe fixture execution",
                        "trigger_source": "offline_fixture",
                        "status": "active",
                        "max_depth": 1,
                        "budget_limit_usd": 0.5,
                    }
                )
                app = SimpleNamespace(
                    config={"research_orchestrator": {"action_receipts_enabled": True}},
                    research_task_repo=repo,
                    research_plan_repo=None,
                    research_step_repo=None,
                    research_meta_log_repo=None,
                )
                orch = SomaticResearchOrchestrator(app)
                orch.init_task(task_id)
                orch.set_phase(task_id, "parsing")
                result = await orch.execute_step(task_id)
                receipt = orch._action_journal.repo.get(task_id, result["action_id"])
                state = json.loads(repo.get(task_id)["orchestrator_state"])
                assert receipt.status == "complete"
                samples.append(
                    {
                        "receipt": receipt.model_dump(mode="json"),
                        "first_useful_result_seconds": state["first_useful_result_seconds"],
                    }
                )
    finally:
        ResearchStepRegistry.get_step = original
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "scope": "offline_executor_and_public_provider_fixture",
                "production_performance": "unmeasured",
                "internal_provider_retries": "unobserved",
                "budget_enforcement": "unmeasured",
                "samples": samples,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Recorded {len(samples)} isolated fixture samples at {output.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.repetitions <= 20:
        parser.error("repetitions must be between 1 and 20")
    asyncio.run(run(args.output, args.repetitions))
