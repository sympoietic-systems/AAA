import logging
import asyncio
from fastapi import APIRouter, Request

from backend.api.schemas import (
    SedimentFileInfo,
    SedimentFilesResponse,
    SedimentInjectRequest,
    SedimentInjectionInfo,
    SedimentInjectionsResponse,
)
from backend.services.sediment import SedimentService

logger = logging.getLogger("aaa.api.sediment")
router = APIRouter()


@router.get("/sediment/files", response_model=SedimentFilesResponse)
async def list_all_sediment_files(request: Request, exclude_conversation_id: str = "", search: str = ""):
    perception_repo = request.app.state.perception_repo
    files = SedimentService.list_files(perception_repo, exclude_conversation_id, search)
    
    # Virtual completed research tasks list:
    try:
        task_repo = request.app.state.research_task_repo
        completed_tasks = task_repo.list_all(status="completed", limit=100)
        
        # Check files already present to avoid duplicates
        existing_filenames = {f["file_name"] for f in files}
        
        for task in completed_tasks:
            task_id = task["id"]
            filename = f"research-synthesis-{task_id}.md"
            if filename in existing_filenames:
                continue
                
            # Create virtual file info
            files.append({
                "conversation_id": "global-research",
                "conversation_title": "Global Research",
                "file_name": filename,
                "file_type": "research-synthesis",
                "summary": task.get("result_summary") or task.get("objective") or "No summary.",
                "token_count": len(task.get("result_summary", "")) // 4 if task.get("result_summary") else 0,
                "chunk_count": 0,
                "created_at": task.get("completed_at") or task.get("proposed_at"),
                "updated_at": task.get("completed_at") or task.get("proposed_at"),
                "display_name": task.get("objective") or filename,
            })
    except Exception as e:
        logger.error("Failed to append completed research tasks in list_all_sediment_files: %s", e)

    return SedimentFilesResponse(
        files=[
            SedimentFileInfo(
                conversation_id=f["conversation_id"],
                conversation_title=f.get("conversation_title") or "",
                file_name=f["file_name"], file_type=f["file_type"],
                summary=f.get("summary"),
                token_count=f.get("token_count", 0), chunk_count=f.get("chunk_count", 0),
                created_at=f.get("created_at"), updated_at=f.get("updated_at"),
                display_name=f.get("display_name") or f["file_name"],
            )
            for f in files
        ]
    )


@router.post("/conversations/{conversation_id}/sediment/inject", response_model=SedimentInjectionsResponse)
async def inject_sediment(conversation_id: str, body: SedimentInjectRequest, request: Request):
    perception_repo = request.app.state.perception_repo
    task_repo = request.app.state.research_task_repo
    
    # Process files before injection
    processed_files = []
    for entry in body.files:
        src_conv = entry.get("source_conversation_id", "")
        src_file = entry.get("source_file_name", "")
        if src_conv == "global-research" and src_file.startswith("research-synthesis-"):
            task_id = src_file.replace("research-synthesis-", "").replace(".md", "")
            
            # Lazily ensure "global-research" exists in conversations to satisfy DB foreign keys
            try:
                perception_repo.ensure_conversation_exists("global-research", "Global Research Reports", "system")
            except Exception as e:
                logger.error("Failed to insert global-research conversation: %s", e)
                
            # Check if this file is already in perception_files
            f_exists = perception_repo.check_file_exists("global-research", src_file)
            
            if not f_exists:
                # Fetch task result
                task = task_repo.get(task_id)
                if task:
                    result_summary = task.get("result_summary") or "No synthesis result."
                    content_bytes = result_summary.encode("utf-8")
                    
                    # Cache file under global-research
                    from backend.services.file import FileService
                    FileService.cache_file("global-research", src_file, content_bytes)
                    
                    # Create entry in perception_files
                    perception_repo.create_file(
                        conversation_id="global-research",
                        file_name=src_file,
                        file_type="research-synthesis",
                        status="uploading",
                    )
                    
                    # Spawn digest worker
                    coro = FileService.process_and_summarize(
                        request.app.state, "global-research", src_file, "research-synthesis"
                    )
                    asyncio.create_task(coro)
                    
        processed_files.append(entry)

    created = SedimentService.inject(perception_repo, conversation_id, processed_files)
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
                status=inj.get("status") or "ready",
            )
            for inj in injections
        ]
    )


@router.delete("/sediment/injections/{injection_id}")
async def remove_sediment_injection(injection_id: str, request: Request):
    SedimentService.remove_injection(request.app.state.perception_repo, injection_id)
    return {"status": "success"}
