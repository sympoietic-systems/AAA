from fastapi import APIRouter, Request

from backend.api.schemas import (
    SedimentFileInfo,
    SedimentFilesResponse,
    SedimentInjectRequest,
    SedimentInjectionInfo,
    SedimentInjectionsResponse,
)
from backend.services.sediment import SedimentService

router = APIRouter()


@router.get("/sediment/files", response_model=SedimentFilesResponse)
async def list_all_sediment_files(request: Request, exclude_conversation_id: str = "", search: str = ""):
    perception_repo = request.app.state.perception_repo
    files = SedimentService.list_files(perception_repo, exclude_conversation_id, search)
    return SedimentFilesResponse(
        files=[
            SedimentFileInfo(
                conversation_id=f["conversation_id"],
                conversation_title=f.get("conversation_title") or "",
                file_name=f["file_name"], file_type=f["file_type"],
                summary=f.get("summary"),
                token_count=f.get("token_count", 0), chunk_count=f.get("chunk_count", 0),
                created_at=f.get("created_at"), updated_at=f.get("updated_at"),
            )
            for f in files
        ]
    )


@router.post("/conversations/{conversation_id}/sediment/inject", response_model=SedimentInjectionsResponse)
async def inject_sediment(conversation_id: str, body: SedimentInjectRequest, request: Request):
    perception_repo = request.app.state.perception_repo
    created = SedimentService.inject(perception_repo, conversation_id, body.files)
    return SedimentInjectionsResponse(
        injections=[SedimentInjectionInfo(**c) for c in created]
    )


@router.get("/conversations/{conversation_id}/sediment/injections", response_model=SedimentInjectionsResponse)
async def get_conversation_injections(conversation_id: str, request: Request):
    perception_repo = request.app.state.perception_repo
    injections = SedimentService.get_injections(perception_repo, conversation_id)
    return SedimentInjectionsResponse(
        injections=[
            SedimentInjectionInfo(
                id=inj["id"], source_conversation_id=inj["source_conversation_id"],
                source_file_name=inj["source_file_name"],
                source_conversation_title=inj.get("source_conversation_title") or "",
                file_type=inj.get("file_type", ""),
                token_count=inj.get("token_count", 0), chunk_count=inj.get("chunk_count", 0),
                summary=inj.get("summary"), injected_at=inj.get("injected_at"),
            )
            for inj in injections
        ]
    )


@router.delete("/sediment/injections/{injection_id}")
async def remove_sediment_injection(injection_id: str, request: Request):
    SedimentService.remove_injection(request.app.state.perception_repo, injection_id)
    return {"status": "success"}
