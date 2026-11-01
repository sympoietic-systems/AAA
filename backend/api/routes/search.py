import asyncio
import logging
from functools import partial

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from backend.services.archive_search import (
    SearchBusy,
    SearchCapacity,
    SearchMatch,
    search_sync,
)

logger = logging.getLogger(__name__)


router = APIRouter()


@router.get("/search", response_model=list[SearchMatch])
async def search_archive(
    request: Request,
    q: str = Query("", max_length=500, description="The query string to search for"),
    conversation_id: str | None = Query(
        None, max_length=100, pattern=r"^[\w-]+$", description="Scope search to a specific conversation ID"
    ),
    mode: str = Query(
        "text",
        pattern=r"^(text|semantic|diffractive|glitch)$",
        description="Baseline search mode: 'text' | 'semantic' | 'diffractive' | 'glitch'",
    ),
    w_text: float = Query(1.0, ge=0.0, le=1.0, description="Weight for text/keyword matches"),
    w_semantic: float = Query(0.0, ge=0.0, le=1.0, description="Weight for semantic vector matches"),
    w_structural: float = Query(0.0, ge=0.0, le=1.0, description="Weight for structural/diffractive matches"),
    w_glitch: float = Query(0.0, ge=0.0, le=1.0, description="Weight for glitch salience metric matches"),
):
    embedder = request.app.state.embedder
    structural_scorer = request.app.state.structural_scorer

    # If a specific mode is selected and weights are default/unset, tune weights automatically
    if mode == "semantic":
        w_text, w_semantic, w_structural, w_glitch = 0.0, 1.0, 0.0, 0.0
    elif mode == "diffractive":
        w_text, w_semantic, w_structural, w_glitch = 0.0, 0.0, 1.0, 0.0
    elif mode == "glitch":
        w_text, w_semantic, w_structural, w_glitch = 0.0, 0.0, 0.0, 1.0
    elif mode == "text" and w_text == 1.0 and w_semantic == 0.0 and w_structural == 0.0 and w_glitch == 0.0:
        # Default text search
        w_text, w_semantic, w_structural, w_glitch = 1.0, 0.0, 0.0, 0.0

    query_emb = None
    query_sig = None
    if w_semantic > 0 and q:
        try:
            query_emb = await embedder.service.encode_async(q)
        except Exception as exc:
            logger.warning("Semantic embedding failed: %s", exc)
    if w_structural > 0 and q:
        try:
            query_sig = await structural_scorer._scorer.score_async(q, use_llm_scorer=False)
        except Exception as exc:
            logger.warning("Structural scoring failed: %s", exc)
    state = request.app.state
    capacity = getattr(state, "search_capacity", None)
    if not isinstance(capacity, SearchCapacity) or capacity.loop is not asyncio.get_running_loop():
        capacity = SearchCapacity()
        state.search_capacity = capacity
    try:
        return await capacity.run(
            partial(
                search_sync,
                state,
                q,
                conversation_id,
                mode,
                w_text,
                w_semantic,
                w_structural,
                w_glitch,
                query_emb,
                query_sig,
            )
        )
    except SearchBusy:
        return JSONResponse(
            status_code=503,
            headers={"Retry-After": "1"},
            content={
                "status": "error",
                "kind": "constraint_violation",
                "message": "Search capacity unavailable",
                "detail": "Search capacity unavailable",
            },
        )
