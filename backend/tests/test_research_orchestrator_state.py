import json
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.storage.database import init_db, get_db_path
from backend.storage.repositories.research_task import ResearchTaskRepository
from backend.services.research_orchestrator import SomaticResearchOrchestrator

DB_PATH = str(get_db_path("data/aaa_test.db"))


def _make_task_id():
    return str(uuid.uuid4())


def _create_task(repo: ResearchTaskRepository, task_id: str, **overrides):
    repo.create({
        "id": task_id,
        "title": overrides.get("title", "Test Research Task"),
        "objective": overrides.get("objective", "Investigate test patterns"),
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
    return state


class TestInitTask:
    def test_init_task_creates_state_with_correct_defaults(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        _create_task(task_repo, task_id)

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        state = orch.init_task(task_id)

        assert state["phase"] == "planning"
        assert state["objective"] == "Investigate test patterns"
        assert state["max_depth"] == 3
        assert state["budget"] == 0.50
        assert state["plan_id"] is None
        assert state["plan"] is None
        assert state["all_findings"] == []
        assert state["sources_analyzed"] == 0
        assert state["stagnation_counter"] == 0
        assert state["step_number"] == 0
        assert state["current_depth"] == 0
        assert state["query_index"] == 0
        assert state["search_results_cache"] == []
        assert state["parsed_sources_cache"] == []
        assert state["digest_results_cache"] == []
        assert state["should_stop"] is False
        assert state["stop_reason"] == ""
        assert state["last_reflection"] == {}

        conn.close()

    def test_init_task_raises_for_missing_task(self):
        state_mock = _make_mock_state()
        state_mock.research_task_repo = ResearchTaskRepository(DB_PATH)
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        try:
            orch.init_task("nonexistent-id")
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "Task not found" in str(e)

    def test_init_task_stores_state_in_memory(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        _create_task(task_repo, task_id)

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        orch.init_task(task_id)

        assert task_id in orch._state_mgr.states
        assert orch._state_mgr.states[task_id]["phase"] == "planning"

        conn.close()


class TestResumeTask:
    def test_resume_from_persisted_orchestrator_state(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        _create_task(task_repo, task_id)

        persisted = {
            "phase": "searching",
            "objective": "Investigate test patterns",
            "max_depth": 3,
            "budget": 0.50,
            "plan_id": "plan-123",
            "plan": {"search_queries": ["q1", "q2"]},
            "all_findings": ["finding A"],
            "sources_analyzed": 2,
            "stagnation_counter": 0,
            "step_number": 5,
            "last_reflection": {"completeness_score": 0.5},
            "current_depth": 1,
            "query_index": 2,
            "search_results_cache": [{"url": "http://example.com"}],
            "digest_results_cache": [],
            "digest_signals": {"followups": []},
            "should_stop": False,
            "stop_reason": "",
        }
        task_repo.update(task_id, orchestrator_state=json.dumps(persisted))

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_step_repo = None
        state_mock.research_plan_repo = None
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        state = orch.resume_task(task_id)

        assert state is not None
        assert state["phase"] == "searching"
        assert state["objective"] == "Investigate test patterns"
        assert state["plan_id"] == "plan-123"
        assert state["plan"]["search_queries"] == ["q1", "q2"]
        assert state["all_findings"] == ["finding A"]
        assert state["step_number"] == 5
        assert state["current_depth"] == 1
        assert state["query_index"] == 2
        assert len(state["search_results_cache"]) == 1
        assert state["max_depth"] == 3
        assert state["budget"] == 0.50

        conn.close()

    def test_resume_task_returns_none_for_missing_task(self):
        state_mock = _make_mock_state()
        state_mock.research_task_repo = ResearchTaskRepository(DB_PATH)
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        result = orch.resume_task("nonexistent-id")
        assert result is None

    def test_resume_adds_missing_mutable_containers(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        _create_task(task_repo, task_id)

        persisted = {"phase": "digesting", "step_number": 3}
        task_repo.update(task_id, orchestrator_state=json.dumps(persisted))

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_step_repo = None
        state_mock.research_plan_repo = None
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        state = orch.resume_task(task_id)

        assert state["all_findings"] == []
        assert state["search_results_cache"] == []
        assert state["parsed_sources_cache"] == []
        assert state["digest_results_cache"] == []
        assert state["last_reflection"] == {}

        conn.close()


class TestEnsureState:
    def test_returns_existing_in_memory_state(self):
        state_mock = _make_mock_state()
        state_mock.research_task_repo = ResearchTaskRepository(DB_PATH)
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        orch._state_mgr.states["test-id"] = {"phase": "planning", "_custom": True}

        state = orch.ensure_state("test-id")
        assert state["_custom"] is True

    def test_raises_runtime_error_for_uninitialized_task(self):
        state_mock = _make_mock_state()
        state_mock.research_task_repo = ResearchTaskRepository(DB_PATH)
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        try:
            orch.ensure_state("nonexistent")
            assert False, "Expected RuntimeError"
        except RuntimeError as e:
            assert "No orchestrator state" in str(e)


class TestGetTaskPhase:
    def test_returns_phase_from_in_memory_state(self):
        state_mock = _make_mock_state()
        state_mock.research_task_repo = ResearchTaskRepository(DB_PATH)
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        orch._state_mgr.states["task-a"] = {"phase": "parsing"}
        assert orch.get_task_phase("task-a") == "parsing"

    def test_returns_empty_string_for_uninitialized(self):
        state_mock = _make_mock_state()
        state_mock.research_task_repo = ResearchTaskRepository(DB_PATH)
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        assert orch.get_task_phase("ghost-task") == ""


class TestSetPhase:
    def test_sets_phase_on_existing_memory_state(self):
        state_mock = _make_mock_state()
        state_mock.research_task_repo = ResearchTaskRepository(DB_PATH)
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        orch._state_mgr.states["task-x"] = {"phase": "planning"}

        orch.set_phase("task-x", "searching")
        assert orch._state_mgr.states["task-x"]["phase"] == "searching"

    def test_raises_runtime_error_for_missing_task(self):
        state_mock = _make_mock_state()
        state_mock.research_task_repo = ResearchTaskRepository(DB_PATH)
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        try:
            orch.set_phase("ghost", "searching")
            assert False, "Expected RuntimeError"
        except RuntimeError as e:
            assert "Cannot set phase" in str(e)


class TestPersistAndLoadState:
    def test_persist_and_load_roundtrip(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        _create_task(task_repo, task_id)

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        orch._state_mgr.states[task_id] = {
            "phase": "reflecting",
            "objective": "Test",
            "max_depth": 2,
            "budget": 0.3,
            "plan_id": "p1",
            "plan": {"goal": "x"},
            "all_findings": ["f1", "f2"],
            "sources_analyzed": 3,
            "stagnation_counter": 1,
            "step_number": 7,
            "last_reflection": {"score": 0.6},
            "current_depth": 2,
            "query_index": 1,
            "search_results_cache": [],
            "digest_results_cache": [],
            "digest_signals": None,
            "should_stop": False,
            "stop_reason": "",
            "extra_field": "should be stripped",
        }

        orch._persist_state(task_id)
        loaded = orch._load_state(task_id)

        assert loaded is not None
        assert loaded["phase"] == "reflecting"
        assert loaded["max_depth"] == 2
        assert loaded["budget"] == 0.3
        assert loaded["plan_id"] == "p1"
        assert loaded["all_findings"] == ["f1", "f2"]
        assert loaded["sources_analyzed"] == 3
        assert loaded["stagnation_counter"] == 1
        assert loaded["step_number"] == 7
        assert loaded["last_reflection"] == {"score": 0.6}
        assert loaded["current_depth"] == 2
        assert "extra_field" not in loaded

        conn.close()

    def test_load_state_returns_none_for_missing_task(self):
        state_mock = _make_mock_state()
        state_mock.research_task_repo = ResearchTaskRepository(DB_PATH)
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        result = orch._load_state("nonexistent")
        assert result is None

    def test_load_state_returns_none_when_no_orchestrator_state_column(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        _create_task(task_repo, task_id)

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        loaded = orch._load_state(task_id)

        assert loaded is None

        conn.close()
