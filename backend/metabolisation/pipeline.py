import logging
from collections.abc import Callable

from backend.metabolisation.context import PipelineResult
from backend.modules.base import ProcessingModule

logger = logging.getLogger(__name__)


class ProcessingPipeline:
    def __init__(
        self,
        modules: list[ProcessingModule],
        error_handler: Callable[[str, Exception, dict], None] | None = None,
    ):
        self._modules = modules
        self._error_handler = error_handler

    async def run(self, initial_payload: dict) -> PipelineResult:
        result = PipelineResult(payload=initial_payload)

        for module in self._modules:
            try:
                output = await module.process(result.payload)
                result.module_outputs[module.name] = output
                result.payload = output
            except Exception as e:
                error_info = {
                    "module": module.name,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
                result.errors.append(error_info)
                result.status = "error"
                logger.exception(f"Module '{module.name}' failed: {e}")
                if self._error_handler:
                    self._error_handler(module.name, e, result.payload)
                break

        return result
