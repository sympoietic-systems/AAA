import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.core.registry import ModuleRegistry
from backend.metabolisation.pipeline import ProcessingPipeline
from backend.modules.base import ProcessingModule


class MockEchoModule(ProcessingModule):
    @property
    def name(self) -> str:
        return "echo"

    def validate(self) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        payload["echoed"] = True
        return payload


class MockFailingModule(ProcessingModule):
    @property
    def name(self) -> str:
        return "failer"

    def validate(self) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        raise RuntimeError("intentional failure")


async def test_pipeline():
    errors_captured = []

    def on_error(module_name, error, payload):
        errors_captured.append({"module": module_name, "error": str(error)})

    registry = ModuleRegistry()
    registry.register("echo", lambda: MockEchoModule())
    registry.register("failer", lambda: MockFailingModule())

    pipeline_modules = registry.resolve_pipeline(["echo", "failer", "echo"])
    assert len(pipeline_modules) == 3
    print("Registry resolution: OK")

    validation = registry.validate_all()
    print(f"Validation: {validation}")

    pipeline = ProcessingPipeline(pipeline_modules, error_handler=on_error)
    result = await pipeline.run({"content": "test", "speaker": "human"})

    assert result.status == "error"
    assert len(result.errors) == 1
    assert result.errors[0]["module"] == "failer"
    assert result.payload["echoed"] is True
    assert len(errors_captured) == 1
    print("Error propagation: OK")

    pipeline_ok = ProcessingPipeline(registry.resolve_pipeline(["echo"]))
    result_ok = await pipeline_ok.run({"content": "test", "speaker": "human"})
    assert result_ok.status == "ok"
    assert len(result_ok.errors) == 0
    assert result_ok.payload["echoed"] is True
    print("Happy path: OK")

    print("All pipeline tests passed!")


asyncio.run(test_pipeline())
