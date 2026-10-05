"""Explicit NVIDIA-only live receipt probe; never part of the unit test suite."""

import argparse
import asyncio
import json
import os
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from backend.modules.llm_pool import ModelPoolProvider
from backend.modules.provider_attempts import AttemptScope, attempt_scope
from backend.services.research.action_journal import ResearchActionJournal
from backend.services.research.attempt_sink import DurableAttemptSink
from backend.storage.database import init_db
from backend.storage.repositories.research.action_receipt import ResearchActionReceiptRepository
from backend.storage.repositories.research.provider_attempt import ResearchProviderAttemptRepository
from backend.storage.repositories.research.research_task import ResearchTaskRepository


async def probe(env_file: str, model: str) -> int:
    load_dotenv(env_file)
    os.environ["AAA_RUN_MIGRATIONS"] = "true"
    keys = [key.strip() for key in os.getenv("AAA_NVIDIA_API_KEY", "").split(",") if key.strip()]
    if not keys:
        print(json.dumps({"status": "unavailable", "reason": "NVIDIA credential missing"}))
        return 2
    with tempfile.TemporaryDirectory(prefix="research-nvidia-") as directory:
        db = str(Path(directory) / "provider_test.db")
        init_db(db).close()
        ResearchTaskRepository(db).create(
            {
                "id": "probe",
                "title": "Live NVIDIA receipt probe",
                "objective": "Verify transport and receipts",
                "trigger_source": "test",
                "status": "active",
                "priority": 1,
                "max_depth": 1,
                "max_breadth": 1,
                "budget_limit_usd": 0,
            }
        )
        journal = ResearchActionJournal(ResearchActionReceiptRepository(db))
        state = {"phase": "planning", "action_journal_policy": {"contract_hash": "probe", "policy_hash": "nvidia-only"}}
        action = journal.begin("probe", state, "planning", {})
        records = []
        sink = DurableAttemptSink(ResearchProviderAttemptRepository(db), action, records, 1)
        scope = AttemptScope(sink, datetime.now(UTC) + timedelta(seconds=65), 60, 1)
        provider = ModelPoolProvider(
            api_key="",
            models=["nvidia_router/" + model],
            fallback_model="",
            nvidia_keys=keys,
            nvidia_api_base=os.getenv("AAA_NVIDIA_API_BASE", "https://integrate.api.nvidia.com/v1"),
            timeout=60,
        )
        try:
            with attempt_scope(scope):
                await provider.generate(
                    [{"role": "user", "content": "Reply with the single word READY."}], max_tokens=64, temperature=0
                )
        except Exception as error:
            print(
                json.dumps(
                    {
                        "status": "failed",
                        "error_category": type(error).__name__,
                        "attempts": [r.model_dump(mode="json") for r in records],
                    }
                )
            )
            return 1
        print(json.dumps({"status": "observed", "attempts": [r.model_dump(mode="json") for r in records]}, indent=2))
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--model", default="nvidia/nemotron-3-ultra-550b-a55b")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(probe(args.env_file, args.model)))
