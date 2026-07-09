from fastapi import APIRouter, Depends

from backend.api.deps import verify_password
from backend.api.helpers import _ensure_structural_tags
from backend.api.routes.agent import router as agent_router
from backend.api.routes.auth import router as auth_router
from backend.api.routes.background import router as background_router
from backend.api.routes.beliefs import router as beliefs_router
from backend.api.routes.chat import router as chat_router
from backend.api.routes.conversations import router as conversations_router
from backend.api.routes.daemon import router as daemon_router
from backend.api.routes.errors import router as errors_router
from backend.api.routes.notifications import router as notifications_router
from backend.api.routes.files import router as files_router
from backend.api.routes.health import router as health_router
from backend.api.routes.history import router as history_router
from backend.api.routes.memory_nodes import router as memory_nodes_router
from backend.api.routes.metrics import router as metrics_router
from backend.api.routes.refusals import router as refusals_router
from backend.api.routes.research import router as research_router
from backend.api.routes.notes import router as notes_router
from backend.api.routes.scheduler import router as scheduler_router
from backend.api.routes.sediment import router as sediment_router
from backend.api.routes.skills import router as skills_router
from backend.api.routes.tags import router as tags_router
from backend.api.routes.tokens import router as tokens_router
from backend.api.routes.search import router as search_router

router = APIRouter(prefix="/api", dependencies=[Depends(verify_password)])

router.include_router(auth_router)
router.include_router(agent_router)
router.include_router(chat_router)
router.include_router(beliefs_router)
router.include_router(history_router)
router.include_router(conversations_router)
router.include_router(tokens_router)
router.include_router(health_router)
router.include_router(skills_router)
router.include_router(scheduler_router)
router.include_router(metrics_router)
router.include_router(background_router)
router.include_router(errors_router)
router.include_router(notifications_router)
router.include_router(files_router)
router.include_router(daemon_router)
router.include_router(notes_router)
router.include_router(sediment_router)
router.include_router(tags_router)
router.include_router(memory_nodes_router)
router.include_router(refusals_router)
router.include_router(research_router)
router.include_router(search_router)

