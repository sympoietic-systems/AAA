"""Refusals dashboard API — Structural Refusal Protocol.

GET /refusals — list recent refusals by Symbia.
"""

from fastapi import APIRouter, Request, Query

from backend.api.deps import get_app_state

router = APIRouter()


@router.get("/refusals")
async def get_refusals(
    request: Request,
    agent_id: str = Query("symbia"),
    limit: int = Query(50, ge=1, le=200),
    state=__import__("fastapi").Depends(get_app_state),
):
    db_path = getattr(state, "db_path", None) or getattr(state.config, "db_path", None)
    if not db_path:
        try:
            from backend.config import load_config
            from backend.storage.database import get_db_path
            db_path = str(get_db_path(load_config().get("database", {}).get("path", "data/aaa.db")))
        except Exception:
            return {"refusals": [], "error": "Database not configured"}

    try:
        from backend.storage.repositories.refusal import RefusalRepository
        repo = RefusalRepository(db_path)
        refusals = repo.list_by_agent(agent_id, limit=limit)
        return {
            "refusals": [
                {
                    "id": r.id,
                    "agent_id": r.agent_id,
                    "conversation_id": r.conversation_id,
                    "message_id": r.message_id,
                    "target_premise": r.target_premise,
                    "incompatibility_claim": r.incompatibility_claim,
                    "proposed_alternative": r.proposed_alternative,
                    "created_at": r.created_at.isoformat() if hasattr(r.created_at, "isoformat") else str(r.created_at) if r.created_at else None,
                }
                for r in refusals
            ],
            "total": repo.count(agent_id),
        }
    except Exception as e:
        return {"refusals": [], "error": str(e)}
