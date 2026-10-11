"""Read-only database inspection endpoints for authenticated diagnostics."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from backend.api.deps import get_database_inspection_repo
from backend.api.schemas import DatabaseRowsRequest, DatabaseRowsResponse, DatabaseSchemaResponse
from backend.core.auth import auth_enabled
from backend.storage.repositories.database_inspection import DatabaseInspectionRepository

router = APIRouter()


def _require_configured_auth() -> None:
    if not auth_enabled():
        raise HTTPException(status_code=503, detail="Database inspection requires AAA_PASSWORD to be configured")


@router.get("/diagnostics/database/schema", response_model=DatabaseSchemaResponse)
async def database_schema(
    repository: DatabaseInspectionRepository = Depends(get_database_inspection_repo),
) -> DatabaseSchemaResponse:
    _require_configured_auth()
    tables = await asyncio.to_thread(repository.list_tables)
    return DatabaseSchemaResponse(tables=tables)


@router.post("/diagnostics/database/rows", response_model=DatabaseRowsResponse)
async def database_rows(
    payload: DatabaseRowsRequest,
    repository: DatabaseInspectionRepository = Depends(get_database_inspection_repo),
) -> DatabaseRowsResponse:
    _require_configured_auth()
    try:
        result = await asyncio.to_thread(
            repository.read_rows,
            table_name=payload.table_name,
            columns=payload.columns,
            filters=[item.model_dump() for item in payload.filters],
            order_by=payload.order_by,
            descending=payload.descending,
            limit=payload.limit,
            offset=payload.offset,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DatabaseRowsResponse.model_validate(result)
