import json
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.storage.database import init_db, get_db_path
from backend.storage.repositories.research_task import ResearchTaskRepository
from backend.storage.repositories.research_plan import ResearchPlanRepository
from backend.storage.repositories.research_step import ResearchStepRepository
from backend.services.research_orchestrator import SomaticResearchOrchestrator

DB_PATH = str(get_db_path("data/aaa_test.db"))


def _make_task_id():
    return str(uuid.uuid4())


def _create_task(repo, task_id, **overrides):
    repo.create({
        "id": task_id,
        "title": overrides.get("title", "Test Task"),
        "objective": overrides.get("objective", "Research objective"),
        "trigger_source": overrides.get("trigger_source", "test"),
        "status": overrides.get("status", "active"),
        "priority": overrides.get("priority", 1),
        "conversation_id": overrides.get("conversation_id", None),
        "max_depth": overrides.get("max_depth", 3),
        "max_breadth": overrides.get("max_breadth", 4),
        "budget_limit_usd": overrides.get("budget_limit_usd", 0.50),
    })


def _make_mock_state():
    state = MagicMock()
    state.config = {
        "research_orchestrator": {
            "max_reflect_rounds": 3,
            "default_top_n": 3,
            "satisfaction_threshold": 0.7,
            "early_stop_threshold": 0.8,
            "max_concurrent_parses": 3,
            "upload_dir": "data/uploads/research",
            "html_archive": False,
        }
    }
    state.llm_provider = None
    state.structural_provider = None
    return state


class TestExecuteStepRouting:
    @pytest.mark.asyncio
    async def test_step_plan_transitions_to_searching(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        plan_repo = ResearchPlanRepository(DB_PATH)
        step_repo = ResearchStepRepository(DB_PATH)
        _create_task(task_repo, task_id)

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_plan_repo = plan_repo
        state_mock.research_step_repo = step_repo
        state_mock.research_step_result_repo = MagicMock()
        state_mock.research_meta_log_repo = MagicMock()
        state_mock.scraped_asset_repo = MagicMock()
        state_mock.research_branch_repo = MagicMock()
        state_mock.llm_provider = None
        state_mock.structural_provider = None
        state_mock.skill_repo = None
        state_mock.commitment_repo = None
        state_mock.belief_repo = None

        orch = SomaticResearchOrchestrator(state_mock)
        orch._task_states[task_id] = {
            "phase": "planning",
            "objective": "Research objective",
            "max_depth": 3, "budget": 0.5,
            "plan_id": None, "plan": None, "all_findings": [],
            "sources_analyzed": 0, "stagnation_counter": 0, "step_number": 0,
            "last_reflection": {}, "current_depth": 0, "query_index": 0,
            "search_results_cache": [], "parsed_sources_cache": [],
            "digest_results_cache": [], "should_stop": False, "stop_reason": "",
        }

        result = await orch._step_plan(task_id, orch._task_states[task_id])

        s = orch._task_states[task_id]
        assert s["phase"] == "searching"
        assert s["plan_id"] is not None
        assert "search_queries" in result["plan"]
        assert "plan_id" in result
        assert "step_id" in result
        assert s["step_number"] == 1

        conn.close()

    @pytest.mark.asyncio
    async def test_step_plan_increments_step_number(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        plan_repo = ResearchPlanRepository(DB_PATH)
        step_repo = ResearchStepRepository(DB_PATH)
        _create_task(task_repo, task_id)

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_plan_repo = plan_repo
        state_mock.research_step_repo = step_repo
        state_mock.research_step_result_repo = MagicMock()
        state_mock.research_meta_log_repo = MagicMock()
        state_mock.scraped_asset_repo = MagicMock()
        state_mock.research_branch_repo = MagicMock()
        state_mock.llm_provider = None
        state_mock.structural_provider = None
        state_mock.skill_repo = None
        state_mock.commitment_repo = None
        state_mock.belief_repo = None

        orch = SomaticResearchOrchestrator(state_mock)
        orch._task_states[task_id] = {
            "phase": "planning",
            "objective": "Test", "max_depth": 3, "budget": 0.5,
            "plan_id": None, "plan": None, "all_findings": [],
            "sources_analyzed": 0, "stagnation_counter": 0, "step_number": 5,
            "last_reflection": {}, "current_depth": 0, "query_index": 0,
            "search_results_cache": [], "parsed_sources_cache": [],
            "digest_results_cache": [], "should_stop": False, "stop_reason": "",
        }

        await orch._step_plan(task_id, orch._task_states[task_id])

        assert orch._task_states[task_id]["phase"] == "searching"
        assert orch._task_states[task_id]["step_number"] == 6

        conn.close()


class TestPreviewCacheMechanism:
    def test_preview_returns_cached_result_on_second_call(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        _create_task(task_repo, task_id)

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        cache_key = "planning"
        dummy_cache = {"phase": "planning", "system_prompt": "test prompt", "user_prompt": "test user"}
        orch._save_cache(task_id, {cache_key: dummy_cache})

        loaded = orch._get_cached_phase(task_id, cache_key)
        assert loaded is not None
        assert loaded["system_prompt"] == "test prompt"
        assert loaded["user_prompt"] == "test user"

        conn.close()

    def test_cache_miss_returns_none(self):
        state_mock = _make_mock_state()
        state_mock.research_task_repo = ResearchTaskRepository(DB_PATH)
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        result = orch._get_cached_phase("no-such-task", "planning")
        assert result is None

    def test_reinitialize_clears_cache(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        _create_task(task_repo, task_id)

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        orch._save_cache(task_id, {"planning": {"cached": True}})

        cached = orch._get_cached_phase(task_id, "planning")
        assert cached is not None

        orch.reinitialize(task_id)
        cached_after = orch._get_cached_phase(task_id, "planning")
        assert cached_after is None

        conn.close()


class TestPhasePlanFallback:
    @pytest.mark.asyncio
    async def test_phase_plan_uses_fallback_when_no_llm_provider(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        plan_repo = ResearchPlanRepository(DB_PATH)
        _create_task(task_repo, task_id)

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_plan_repo = plan_repo
        state_mock.research_meta_log_repo = MagicMock()
        state_mock.llm_provider = None
        state_mock.structural_provider = None
        state_mock.skill_repo = None
        state_mock.commitment_repo = None
        state_mock.belief_repo = None

        orch = SomaticResearchOrchestrator(state_mock)
        result = await orch._phase_plan(task_id, "Test objective", 3, 0.5, "")

        assert "id" in result
        assert result["goal"] == "Test objective"
        assert result["search_queries"] == ["Test objective"]
        assert result["n_results_per_query"] == 3
        assert result["estimated_depth"] == 1

        conn.close()
