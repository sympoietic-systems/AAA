from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.services.research.orchestrator import SomaticResearchOrchestrator
from backend.services.research.sedimentation_queue import SedimentationPacketQueue
from backend.services.research.step_executor import ResearchStepExecutor
from backend.services.research.task_state import TaskStateManager


def _orchestrator() -> SomaticResearchOrchestrator:
    return SomaticResearchOrchestrator(
        SimpleNamespace(
            config={},
            research_task_repo=MagicMock(),
            research_plan_repo=MagicMock(),
            research_step_repo=MagicMock(),
            research_meta_log_repo=MagicMock(),
        )
    )


def test_orchestrator_owns_focused_state_execution_and_sedimentation_collaborators():
    orchestrator = _orchestrator()

    assert isinstance(orchestrator._state_mgr, TaskStateManager)
    assert isinstance(orchestrator._step_executor, ResearchStepExecutor)
    assert isinstance(orchestrator._sedimentation_sink, SedimentationPacketQueue)


@pytest.mark.asyncio
async def test_execute_step_remains_a_compatibility_delegate():
    orchestrator = _orchestrator()
    orchestrator._step_executor.execute = AsyncMock(return_value={"next_phase": "searching"})

    result = await orchestrator.execute_step("task-1")

    assert result == {"next_phase": "searching"}
    orchestrator._step_executor.execute.assert_awaited_once_with("task-1")
