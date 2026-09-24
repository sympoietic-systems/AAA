import uuid

from backend.storage.database import get_db_path, init_db
from backend.storage.repositories.conversation.note import NoteRepository
from backend.storage.repositories.research.research_plan import ResearchPlanRepository
from backend.storage.repositories.research.research_step import ResearchStepRepository
from backend.storage.repositories.research.research_task import ResearchTaskRepository


def _task(task_id: str, *, status: str = "proposed", orchestrator_state: str | None = None) -> dict:
    return {
        "id": task_id,
        "title": "Transaction test",
        "objective": "Verify research mutation boundaries",
        "trigger_source": "test",
        "status": status,
        "priority": 1,
        "max_depth": 2,
        "max_breadth": 2,
        "budget_limit_usd": 0.5,
        "orchestrator_state": orchestrator_state,
    }


def test_research_task_mutations_keep_dependent_rows_consistent():
    db_path = str(get_db_path("data/aaa_transactions_test.db"))
    init_db(db_path).close()
    task_repo = ResearchTaskRepository(db_path)
    plan_repo = ResearchPlanRepository(db_path)
    step_repo = ResearchStepRepository(db_path)
    note_repo = NoteRepository(db_path)
    task_id = str(uuid.uuid4())
    plan_id = str(uuid.uuid4())
    step_id = str(uuid.uuid4())
    note_id = str(uuid.uuid4())

    task_repo.create(_task(task_id, status="completed", orchestrator_state='{"phase":"complete"}'))
    plan_repo.create({"id": plan_id, "task_id": task_id, "plan_json": "{}"})
    step_repo.create(
        {
            "id": step_id,
            "task_id": task_id,
            "plan_id": plan_id,
            "step_number": 1,
            "step_type": "search",
        }
    )
    note_repo.create_note(note_id, "research_task", task_id, selected_text="kept together")

    task_repo.reset_for_rerun(
        task_id,
        {"status": "queued", "orchestrator_state": None, "rerun_count": 1},
    )

    reset_task = task_repo.get(task_id)
    assert reset_task is not None
    assert reset_task["status"] == "queued"
    assert reset_task["orchestrator_state"] is None
    assert plan_repo.get_by_task(task_id) is None
    assert step_repo.get_by_task(task_id) == []

    task_repo.delete_with_notes(task_id)

    assert task_repo.get(task_id) is None
    assert note_repo.get_notes_by_asset("research_task", task_id) == []


def test_approve_updates_metadata_and_status_together():
    db_path = str(get_db_path("data/aaa_transactions_test.db"))
    init_db(db_path).close()
    repo = ResearchTaskRepository(db_path)
    task_id = str(uuid.uuid4())
    repo.create(_task(task_id))

    repo.approve(task_id, "user", "2026-09-23 12:00:00")

    task = repo.get(task_id)
    assert task is not None
    assert task["status"] == "approved"
    assert task["approved_by"] == "user"
    assert task["approved_at"] == "2026-09-23 12:00:00"
