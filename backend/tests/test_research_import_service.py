"""Unit tests for research import service — foreign key integrity and ID remapping.

Covers:
- Tasks with a matching plan correctly remap step plan_id
- Tasks with *multiple* plan IDs in steps fall back to the exported plan
- Tasks with *no* exported plan but existing steps get a synthetic dummy plan
- Step results referencing unknown step IDs are skipped (not crashed)
- Warnings are deduplicated when many steps reference the same unknown plan
"""

import json
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.storage.database import init_db, get_db_path
from backend.storage.repositories.research_task import ResearchTaskRepository
from backend.storage.repositories.research_plan import ResearchPlanRepository
from backend.storage.repositories.research_step import ResearchStepRepository
from backend.storage.repositories.research_step_result import ResearchStepResultRepository
from backend.storage.repositories.research_meta_log import ResearchMetaLogRepository
from backend.storage.repositories.research_branch import ResearchBranchRepository
from backend.storage.repositories.note import NoteRepository
from backend.services.research.import_service import import_research_task

DB_PATH = str(get_db_path("data/aaa_import_test.db"))


def _setup_state():
    init_db(DB_PATH)
    return _AppState(DB_PATH)


class _AppState:
    def __init__(self, db_path: str):
        self.research_task_repo = ResearchTaskRepository(db_path)
        self.research_plan_repo = ResearchPlanRepository(db_path)
        self.research_step_repo = ResearchStepRepository(db_path)
        self.research_step_result_repo = ResearchStepResultRepository(db_path)
        self.research_meta_log_repo = ResearchMetaLogRepository(db_path)
        self.research_branch_repo = ResearchBranchRepository(db_path)
        self.scraped_asset_repo = None
        self.note_repo = NoteRepository(db_path)


def _make_plan_id() -> str:
    return str(uuid.uuid4())


def _make_step(plan_id: str, step_id: str | None = None) -> dict:
    return {
        "id": step_id or str(uuid.uuid4()),
        "plan_id": plan_id,
        "step_number": 1,
        "step_type": "search",
        "step_data": "{}",
        "status": "completed",
        "result_summary": None,
        "started_at": None,
        "completed_at": None,
        "created_at": "2026-06-30 09:00:00",
        "query_group": None,
        "query_text": "test query",
    }


def _make_payload(
    plan_id: str | None = None,
    steps: list | None = None,
    step_results: list | None = None,
) -> dict:
    task_id = str(uuid.uuid4())
    plan = (
        {
            "id": plan_id,
            "task_id": task_id,
            "plan_json": json.dumps({"goal": "test"}),
            "status": "active",
            "created_at": "2026-06-30 09:00:00",
        }
        if plan_id
        else None
    )
    return {
        "task": {
            "id": task_id,
            "title": "Test Task",
            "objective": "Test objective",
            "trigger_source": "user_console",
            "status": "completed",
            "priority": 2,
            "max_depth": 3,
            "max_breadth": 4,
            "budget_limit_usd": 0.50,
            "budget_spent_usd": 0.10,
            "branches_created": 0,
            "assets_harvested": 0,
            "lateral_flights": 0,
            "bifurcation_triggered": 0,
        },
        "plan": plan,
        "branches": [],
        "assets": [],
        "steps": steps or [],
        "step_results": step_results or [],
        "meta_log": [],
        "notes": [],
    }


class TestImportWithMatchingPlan:
    def test_step_plan_id_correctly_remapped(self):
        """Steps whose plan_id matches the exported plan get the new plan UUID."""
        state = _setup_state()
        plan_id = _make_plan_id()
        step = _make_step(plan_id=plan_id)
        payload = _make_payload(plan_id=plan_id, steps=[step])

        result = import_research_task(payload, state)

        assert result.imported is True
        assert result.stats["steps"] == 1
        assert result.stats["plan"] == 1

        steps = state.research_step_repo.get_by_task(result.new_task_id)
        assert len(steps) == 1
        # The step's plan_id must point to a valid research_plan row
        plan_row = state.research_plan_repo.get(steps[0]["plan_id"])
        assert plan_row is not None
        assert plan_row["task_id"] == result.new_task_id


class TestImportWithMultiplePlanIds:
    def test_steps_with_unknown_plan_id_fall_back_to_exported_plan(self):
        """Steps referencing a second (legacy) plan_id fall back to the primary exported plan."""
        state = _setup_state()
        primary_plan_id = _make_plan_id()
        orphan_plan_id = _make_plan_id()   # never in export — simulates legacy multi-plan task

        steps = [
            _make_step(plan_id=primary_plan_id),  # known plan
            _make_step(plan_id=orphan_plan_id),   # unknown plan
        ]
        payload = _make_payload(plan_id=primary_plan_id, steps=steps)

        result = import_research_task(payload, state)

        assert result.imported is True
        assert result.stats["steps"] == 2

        steps_in_db = state.research_step_repo.get_by_task(result.new_task_id)
        assert len(steps_in_db) == 2

        # Both steps must point to a valid plan in the target DB
        for s in steps_in_db:
            plan_row = state.research_plan_repo.get(s["plan_id"])
            assert plan_row is not None, f"Step {s['id']} has an orphan plan_id {s['plan_id']}"

        # Unknown plan ID warning is recorded exactly once
        unknown_warnings = [w for w in result.warnings if orphan_plan_id in w]
        assert len(unknown_warnings) == 1, "Expected exactly one warning per unknown ID"


class TestImportWithNoPlan:
    def test_dummy_plan_created_when_steps_present_but_no_plan_exported(self):
        """When no plan is in the payload but steps exist, a dummy plan is auto-created."""
        state = _setup_state()
        orphan_plan_id = _make_plan_id()
        step = _make_step(plan_id=orphan_plan_id)
        payload = _make_payload(plan_id=None, steps=[step])  # no plan exported

        result = import_research_task(payload, state)

        assert result.imported is True
        assert result.stats["plan"] == 1      # dummy plan was created
        assert result.stats["steps"] == 1

        steps_in_db = state.research_step_repo.get_by_task(result.new_task_id)
        assert len(steps_in_db) == 1
        plan_row = state.research_plan_repo.get(steps_in_db[0]["plan_id"])
        assert plan_row is not None
        assert plan_row["task_id"] == result.new_task_id


class TestImportStepResultsSafety:
    def test_step_result_with_unknown_step_id_is_skipped(self):
        """Step results referencing a non-exported step_id are skipped, not crashed."""
        state = _setup_state()
        plan_id = _make_plan_id()
        step = _make_step(plan_id=plan_id)
        ghost_step_id = str(uuid.uuid4())   # not in the export steps list

        step_results = [
            {
                "id": str(uuid.uuid4()),
                "step_id": step["id"],       # valid reference
                "source_url": "https://example.com",
                "source_title": "Example",
                "relevance_score": 0.8,
                "novelty_score": 0.6,
            },
            {
                "id": str(uuid.uuid4()),
                "step_id": ghost_step_id,    # broken reference
                "source_url": "https://ghost.com",
                "source_title": "Ghost",
                "relevance_score": 0.1,
                "novelty_score": 0.1,
            },
        ]
        payload = _make_payload(plan_id=plan_id, steps=[step], step_results=step_results)

        result = import_research_task(payload, state)

        assert result.imported is True
        assert result.stats["step_results"] == 1  # only the valid one inserted

        # A warning is recorded for the skipped result
        ghost_warnings = [w for w in result.warnings if ghost_step_id in w]
        assert len(ghost_warnings) >= 1

    def test_empty_steps_and_no_plan_imports_task_cleanly(self):
        """A task with no plan and no steps imports with only a task record."""
        state = _setup_state()
        payload = _make_payload(plan_id=None, steps=[], step_results=[])

        result = import_research_task(payload, state)

        assert result.imported is True
        assert result.stats.get("steps", 0) == 0
        assert result.stats.get("plan", 0) == 0

        task = state.research_task_repo.get(result.new_task_id)
        assert task is not None
