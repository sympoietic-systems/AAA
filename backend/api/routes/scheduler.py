from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/scheduler/status")
async def get_scheduler_status(request: Request):
    state = request.app.state
    scheduler = getattr(state, "startup_scheduler", None)
    if not scheduler:
        return {
            "status": "not_initialized",
            "indexing_tasks_found": 0,
            "indexing_tasks_completed": 0,
            "indexing_tasks_failed": 0,
            "active_indexing_jobs": [],
            "belief_turns_found": 0,
            "belief_turns_completed": 0,
            "belief_turns_failed": 0,
            "error_details": "No startup scheduler registered on app state"
        }
    return scheduler.get_status()
