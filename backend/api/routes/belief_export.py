"""Authenticated half-open UTC ledger exports under the frozen T3 namespace."""

from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError

from backend.api.belief_review_schemas import ExportItem, ExportPage, ReviewExportQuery
from backend.api.deps import get_belief_repo, verify_password
from backend.core.auth import get_auth_password
from backend.errors import ValidationGlitch
from backend.services.belief_export import BeliefExport
from backend.services.belief_review_contracts import AgentId, Identifier
from backend.storage.repositories.cognitive.belief import BeliefRepository

router = APIRouter(prefix="/beliefs/v2/agents/{agent_id}", dependencies=[Depends(verify_password)])


def export_service(repo: Any = Depends(get_belief_repo)) -> BeliefExport:
    if not isinstance(repo, BeliefRepository):
        raise HTTPException(status_code=503, detail="Belief repository unavailable")
    return BeliefExport(repo._db_path, get_auth_password())


def export_query(
    request: Request,
    from_time: Annotated[datetime, Query(alias="from")],
    to_time: Annotated[datetime, Query(alias="to")],
    limit: Annotated[int, Query(ge=1, le=50)] = 25,
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
) -> ReviewExportQuery:
    if set(request.query_params) - {"from", "to", "limit", "cursor"} or any(
        len(request.query_params.getlist(key)) != 1 for key in request.query_params
    ):
        raise ValidationGlitch("Unknown or repeated export query parameter", entity="belief_export")
    try:
        return ReviewExportQuery(from_time=from_time, to_time=to_time, limit=limit, cursor=cursor)
    except ValidationError as error:
        raise ValidationGlitch("Invalid export interval or cursor", entity="belief_export") from error


@router.get("/{resource}", response_model=ExportPage)
async def export_page(
    agent_id: AgentId,
    resource: Literal["encounters", "assessments", "decisions", "events"],
    query: ReviewExportQuery = Depends(export_query),
    service: BeliefExport = Depends(export_service),
) -> dict[str, Any]:
    """Export stored dated rows; continue every cursor before treating the interval as complete."""
    return await service.page(agent_id, resource, query.from_time, query.to_time, query.limit, query.cursor)


@router.get("/{resource}/{identity}", response_model=ExportItem)
async def export_detail(
    agent_id: AgentId,
    resource: Literal["encounters", "assessments", "decisions"],
    identity: Identifier,
    service: BeliefExport = Depends(export_service),
) -> dict[str, Any]:
    """Get an agent-owned typed receipt, including an explicitly pending assessment."""
    return await service.detail(agent_id, resource, identity)
