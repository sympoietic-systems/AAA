"""Authenticated scoped workshop endpoints; shared credential never implies bilateral assent."""

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from backend.api.belief_review_schemas import ReviewDecisionRequest
from backend.api.deps import get_belief_repo, verify_password
from backend.core.auth import auth_enabled
from backend.services.belief_review_contracts import Actor, WorkshopCommand
from backend.services.belief_workshop import BeliefWorkshop
from backend.storage.repositories.cognitive.belief import BeliefRepository
from backend.storage.repositories.cognitive.belief_workshop import BeliefWorkshopRepository

router = APIRouter(prefix="/beliefs/v2/agents/{agent_id}", dependencies=[Depends(verify_password)])


def operator_actor() -> Actor:
    if not auth_enabled():
        raise HTTPException(status_code=403, detail="Operator review requires configured authentication")
    return Actor(kind="operator", principal_id="shared-operator", auth_context_id="server:operator-review")


def workshop(repo: Any = Depends(get_belief_repo)) -> BeliefWorkshop:
    if not isinstance(repo, BeliefRepository):
        raise HTTPException(status_code=503, detail="Belief repository unavailable")
    return BeliefWorkshop(repo._db_path)


async def guard_legacy(request: Request, repo: Any = Depends(get_belief_repo)) -> None:
    if isinstance(repo, BeliefRepository):
        guard = BeliefWorkshopRepository(repo._db_path)
        for name in ("proposal_id", "belief_id"):
            record = request.path_params.get(name)
            if record:
                await asyncio.to_thread(guard.guard_legacy, str(record))


async def guard_target(record: str | None, repo: Any) -> None:
    if record and isinstance(repo, BeliefRepository):
        await asyncio.to_thread(BeliefWorkshopRepository(repo._db_path).guard_legacy, record)


@router.get("/records/{record_id}/review")
async def review(
    agent_id: str, record_id: str, service: BeliefWorkshop = Depends(workshop), actor: Actor = Depends(operator_actor)
) -> dict[str, Any]:
    return await service.family(agent_id, record_id)


@router.post("/records/{record_id}/decisions")
async def decide(
    agent_id: str,
    record_id: str,
    payload: ReviewDecisionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_.:-]+$"),
    actor: Actor = Depends(operator_actor),
    service: BeliefWorkshop = Depends(workshop),
) -> dict[str, Any]:
    return await service.command(
        agent_id, record_id, idempotency_key, WorkshopCommand.model_validate(payload.model_dump()), actor=actor
    )
