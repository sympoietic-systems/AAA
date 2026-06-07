import uuid

from fastapi import APIRouter, Request

from .schemas import (
    SedimentFileInfo,
    SedimentFilesResponse,
    SedimentInjectRequest,
    SedimentInjectionInfo,
    SedimentInjectionsResponse,
)

router = APIRouter()


@router.get("/sediment/files", response_model=SedimentFilesResponse)
async def list_all_sediment_files(
    request: Request,
    exclude_conversation_id: str = "",
    search: str = "",
):
    state = request.app.state
    perception_repo = state.perception_repo

    files = perception_repo.get_all_files_across_conversations(
        exclude_conversation_id=exclude_conversation_id or None,
        search=search or None,
    )
    return SedimentFilesResponse(
        files=[
            SedimentFileInfo(
                conversation_id=f["conversation_id"],
                conversation_title=f.get("conversation_title") or "",
                file_name=f["file_name"],
                file_type=f["file_type"],
                summary=f.get("summary"),
                token_count=f.get("token_count", 0),
                chunk_count=f.get("chunk_count", 0),
                created_at=f.get("created_at"),
                updated_at=f.get("updated_at"),
            )
            for f in files
        ]
    )


@router.post("/conversations/{conversation_id}/sediment/inject", response_model=SedimentInjectionsResponse)
async def inject_sediment(
    conversation_id: str,
    body: SedimentInjectRequest,
    request: Request,
):
    state = request.app.state
    perception_repo = state.perception_repo

    created: list[SedimentInjectionInfo] = []
    for entry in body.files:
        src_conv = entry.get("source_conversation_id", "")
        src_file = entry.get("source_file_name", "")
        if not src_conv or not src_file:
            continue
        injection_id = str(uuid.uuid4())
        perception_repo.inject_sediment(
            injection_id=injection_id,
            source_conversation_id=src_conv,
            source_file_name=src_file,
            target_conversation_id=conversation_id,
        )
        created.append(SedimentInjectionInfo(
            id=injection_id,
            source_conversation_id=src_conv,
            source_file_name=src_file,
        ))

    return SedimentInjectionsResponse(injections=created)


@router.get("/conversations/{conversation_id}/sediment/injections", response_model=SedimentInjectionsResponse)
async def get_conversation_injections(conversation_id: str, request: Request):
    state = request.app.state
    perception_repo = state.perception_repo

    injections = perception_repo.get_injections_for_conversation(conversation_id)
    return SedimentInjectionsResponse(
        injections=[
            SedimentInjectionInfo(
                id=inj["id"],
                source_conversation_id=inj["source_conversation_id"],
                source_file_name=inj["source_file_name"],
                source_conversation_title=inj.get("source_conversation_title") or "",
                file_type=inj.get("file_type", ""),
                token_count=inj.get("token_count", 0),
                chunk_count=inj.get("chunk_count", 0),
                summary=inj.get("summary"),
                injected_at=inj.get("injected_at"),
            )
            for inj in injections
        ]
    )


@router.delete("/sediment/injections/{injection_id}")
async def remove_sediment_injection(injection_id: str, request: Request):
    state = request.app.state
    perception_repo = state.perception_repo
    perception_repo.remove_injection(injection_id)
    return {"status": "success"}
