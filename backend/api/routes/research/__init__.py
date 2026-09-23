"""Research API endpoints package — Autonomous Research Engine.

See docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 4.8 and 5.
"""

from fastapi import APIRouter

from backend.api.routes.research.artifacts import router as artifacts_router
from backend.api.routes.research.steps import router as steps_router
from backend.api.routes.research.tasks import router as tasks_router

router = APIRouter()
router.include_router(tasks_router)
router.include_router(steps_router)
router.include_router(artifacts_router)
