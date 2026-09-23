import asyncio
import json
import logging
import os
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from backend.api.deps import get_agent_name, get_app_state, get_conversation_repo, get_perception_repo
from backend.api.schemas import ConversationFile, ConversationFilesResponse
from backend.services.file import FileService
from backend.utils.filesystem import get_upload_path
from backend.utils.security import (
    DEFAULT_MAX_FILE_SIZE,
    DEFAULT_MAX_IMAGE_SIZE,
    sanitize_filename,
    sanitize_identifier,
)

logger = logging.getLogger(__name__)
router = APIRouter()
DEFAULT_MAX_UPLOAD_FILES = 10
DEFAULT_MAX_UPLOAD_TOTAL_SIZE = 200 * 1024 * 1024


def _parse_file_datetime(val):
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


@router.post("/conversations/{conversation_id}/files", response_model=ConversationFilesResponse)
async def upload_conversation_files(
    conversation_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    state=Depends(get_app_state),
    perception_repo=Depends(get_perception_repo),
    conv_repo=Depends(get_conversation_repo),
    agent_id=Depends(get_agent_name),
):
    try:
        if conversation_id != "new":
            conversation_id = sanitize_identifier(conversation_id, "conversation_id")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    upload_cfg = getattr(state, "config", {}).get("uploads", {})
    max_files = max(1, min(int(upload_cfg.get("max_files", DEFAULT_MAX_UPLOAD_FILES)), 50))
    max_file_bytes = max(1, min(int(upload_cfg.get("max_file_bytes", DEFAULT_MAX_FILE_SIZE)), DEFAULT_MAX_FILE_SIZE))
    max_image_bytes = max(1, min(int(upload_cfg.get("max_image_bytes", DEFAULT_MAX_IMAGE_SIZE)), max_file_bytes))
    max_total_bytes = max(
        max_file_bytes,
        min(int(upload_cfg.get("max_total_bytes", DEFAULT_MAX_UPLOAD_TOTAL_SIZE)), 1024 * 1024 * 1024),
    )

    form = await request.form(max_files=max_files, max_fields=20)
    uploaded_files = form.getlist("files")
    if not uploaded_files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    if len(uploaded_files) > max_files:
        raise HTTPException(status_code=400, detail=f"At most {max_files} files may be uploaded per request")

    create_conversation = conversation_id == "new" or not conv_repo or not conv_repo.get(conversation_id)
    if create_conversation:
        import uuid

        conversation_id = str(uuid.uuid4())

    staged: list[tuple[str, str, int, str]] = []
    seen_names: set[str] = set()
    total_size = 0
    try:
        for upload in uploaded_files:
            if not hasattr(upload, "filename") or not upload.filename:
                raise ValueError("Every uploaded file must have a filename")
            safe_name = sanitize_filename(upload.filename)
            if safe_name in seen_names:
                raise ValueError(f"Duplicate uploaded filename '{safe_name}'")
            seen_names.add(safe_name)
            remaining = max_total_bytes - total_size
            if remaining <= 0:
                raise ValueError(f"Upload batch exceeds {max_total_bytes} byte aggregate limit")
            staged_file = await asyncio.to_thread(
                FileService.cache_upload_stream,
                conversation_id,
                safe_name,
                upload.file,
                max_file_bytes=min(max_file_bytes, remaining),
                max_image_bytes=min(max_image_bytes, remaining),
            )
            staged.append(staged_file)
            total_size += staged_file[2]
    except (ValueError, OSError) as exc:
        await asyncio.to_thread(FileService.remove_cached_files, [item[3] for item in staged])
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if conv_repo:
        if create_conversation:
            conv_repo.create(conversation_id=conversation_id, agent_id=agent_id)
            title_base = staged[0][0].rsplit(".", 1)[0]
            conv_repo.update_title(conversation_id, f"File trace: {title_base[:50]}")
        else:
            conv_repo.touch(conversation_id)

    schema_files = []
    for safe_name, file_type, _file_size, _cached_path in staged:
        perception_repo.create_file(
            conversation_id=conversation_id,
            file_name=safe_name,
            file_type=file_type,
            status="uploading",
        )

        background_tasks.add_task(
            FileService.process_and_summarize,
            state,
            conversation_id,
            safe_name,
            file_type,
        )

        schema_files.append(
            ConversationFile(
                file_name=safe_name,
                file_type=file_type,
                status="uploading",
                token_count=0,
                chunk_count=0,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )

    return ConversationFilesResponse(conversation_id=conversation_id, files=schema_files)


@router.get("/conversations/{conversation_id}/files", response_model=ConversationFilesResponse)
async def get_conversation_files(conversation_id: str, perception_repo=Depends(get_perception_repo)):
    files = perception_repo.get_files_by_conversation(conversation_id)
    schema_files = []
    for f in files:
        created_at_dt = _parse_file_datetime(f.get("created_at"))
        updated_at_dt = _parse_file_datetime(f.get("updated_at"))
        schema_files.append(
            ConversationFile(
                file_name=f["file_name"],
                file_type=f["file_type"],
                status=f["status"],
                summary=None,
                summary_model=f.get("summary_model"),
                token_count=f.get("token_count", 0),
                chunk_count=f.get("chunk_count", 0),
                created_at=created_at_dt,
                updated_at=updated_at_dt,
            )
        )
    return ConversationFilesResponse(conversation_id=conversation_id, files=schema_files)


@router.delete("/conversations/{conversation_id}/files/{file_name}")
async def delete_conversation_file(conversation_id: str, file_name: str, perception_repo=Depends(get_perception_repo)):
    try:
        conversation_id = sanitize_identifier(conversation_id, "conversation_id")
        file_name = sanitize_filename(file_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    files = perception_repo.get_files_by_conversation(conversation_id)
    exists = any(f["file_name"] == file_name for f in files)
    if not exists:
        raise HTTPException(status_code=404, detail="File not found in conversation")
    try:
        cached_file = get_upload_path(conversation_id, file_name)
        if os.path.exists(cached_file):
            os.remove(cached_file)
        convo_dir = os.path.dirname(cached_file)
        if os.path.exists(convo_dir) and not os.listdir(convo_dir):
            os.rmdir(convo_dir)
    except Exception as e:
        logger.error(f"Failed to delete disk cache file {file_name}: {e}")
    perception_repo.delete_file(conversation_id, file_name)
    return {"status": "success"}


@router.post("/conversations/{conversation_id}/files/{file_name}/reprocess")
async def reprocess_conversation_file(
    conversation_id: str,
    file_name: str,
    request: Request,
    background_tasks: BackgroundTasks,
    state=Depends(get_app_state),
    perception_repo=Depends(get_perception_repo),
):
    try:
        conversation_id = sanitize_identifier(conversation_id, "conversation_id")
        file_name = sanitize_filename(file_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    files = perception_repo.get_files_by_conversation(conversation_id)
    target_file = None
    for f in files:
        if f["file_name"] == file_name:
            target_file = f
            break
    if not target_file:
        raise HTTPException(status_code=404, detail="File not found in conversation")
    perception_repo.update_file(conversation_id=conversation_id, file_name=file_name, status="processing")
    background_tasks.add_task(
        FileService.reprocess_and_summarize,
        state,
        conversation_id,
        file_name,
        target_file["file_type"],
    )
    return {"status": "success"}


@router.get("/conversations/{conversation_id}/files/{file_name:path}/summary")
async def get_file_summary_endpoint(conversation_id: str, file_name: str, perception_repo=Depends(get_perception_repo)):
    target_conv_id = conversation_id
    injections = perception_repo.get_injections_for_conversation(conversation_id)
    for inj in injections:
        if inj["source_file_name"] == file_name:
            target_conv_id = inj["source_conversation_id"]
            break
    files = perception_repo.get_files_by_conversation(target_conv_id)
    for f in files:
        if f["file_name"] == file_name:
            res_data = {"summary": f.get("summary"), "summary_model": f.get("summary_model")}
            if f.get("file_type") == "image":
                log_record = perception_repo.get_perception_log_by_image(file_name)
                if log_record:
                    res_data["image_metadata"] = log_record
            elif f.get("file_type") == "web_probe":
                web_record = perception_repo.get_exogenous_stream_by_file(file_name)
                if web_record:
                    res_data["web_metadata"] = web_record
            else:
                try:
                    nodes = json.loads(f.get("belief_nodes_implicated")) if f.get("belief_nodes_implicated") else []
                except Exception:
                    nodes = []
                try:
                    impact = json.loads(f.get("state_vector_impact")) if f.get("state_vector_impact") else [0.0] * 16
                except Exception:
                    impact = [0.0] * 16
                res_data["document_metadata"] = {
                    "interference_score": f.get("interference_score") or 0.0,
                    "belief_nodes_implicated": nodes,
                    "state_vector_impact": impact,
                }
            return res_data
    raise HTTPException(status_code=404, detail="File not found")


@router.get("/files/by-name")
async def get_file_by_name_endpoint(file_name: str, perception_repo=Depends(get_perception_repo)):
    file_info = perception_repo.find_file_by_name(file_name)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")
    chunks = perception_repo.get_chunks_by_file(file_info["conversation_id"], file_name)
    file_info["chunks"] = chunks
    return file_info
