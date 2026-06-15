import json
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from backend.api.deps import get_app_state, get_conversation_repo, get_perception_repo, get_agent_name
from backend.api.schemas import ConversationFile, ConversationFilesResponse
from backend.services.file import FileService
from backend.utils.filesystem import ensure_upload_dir, get_upload_path

logger = logging.getLogger(__name__)
router = APIRouter()


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
    form = await request.form()
    uploaded_files = form.getlist("files")
    if not uploaded_files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    if conversation_id == "new" or not conv_repo or not conv_repo.get(conversation_id):
        import uuid
        conversation_id = str(uuid.uuid4())
        if conv_repo:
            conv_repo.create(conversation_id=conversation_id, agent_id=agent_id)
            first_filename = uploaded_files[0].filename if hasattr(uploaded_files[0], "filename") else "Uploaded files"
            title_base = first_filename.rsplit(".", 1)[0] if "." in first_filename else first_filename
            conv_repo.update_title(conversation_id, f"File trace: {title_base[:50]}")
    else:
        if conv_repo:
            conv_repo.touch(conversation_id)

    schema_files = []
    for f in uploaded_files:
        if not hasattr(f, "filename") or not f.filename:
            continue
        file_bytes = await f.read()
        file_type = FileService.map_extension_to_type(f.filename)
        FileService.cache_file(conversation_id, f.filename, file_bytes)

        perception_repo.create_file(
            conversation_id=conversation_id,
            file_name=f.filename,
            file_type=file_type,
            status="uploading",
        )

        background_tasks.add_task(
            FileService.process_and_summarize,
            state, conversation_id, f.filename, file_type, file_bytes,
        )

        schema_files.append(ConversationFile(
            file_name=f.filename,
            file_type=file_type,
            status="uploading",
            token_count=0, chunk_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ))

    return ConversationFilesResponse(conversation_id=conversation_id, files=schema_files)


@router.get("/conversations/{conversation_id}/files", response_model=ConversationFilesResponse)
async def get_conversation_files(conversation_id: str, perception_repo=Depends(get_perception_repo)):
    files = perception_repo.get_files_by_conversation(conversation_id)
    schema_files = []
    for f in files:
        created_at_dt = _parse_file_datetime(f.get("created_at"))
        updated_at_dt = _parse_file_datetime(f.get("updated_at"))
        schema_files.append(ConversationFile(
            file_name=f["file_name"], file_type=f["file_type"], status=f["status"],
            summary=None, summary_model=f.get("summary_model"),
            token_count=f.get("token_count", 0), chunk_count=f.get("chunk_count", 0),
            created_at=created_at_dt, updated_at=updated_at_dt,
        ))
    return ConversationFilesResponse(conversation_id=conversation_id, files=schema_files)


@router.delete("/conversations/{conversation_id}/files/{file_name}")
async def delete_conversation_file(conversation_id: str, file_name: str, perception_repo=Depends(get_perception_repo)):
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
    conversation_id: str, file_name: str,
    request: Request, background_tasks: BackgroundTasks,
    state=Depends(get_app_state),
    perception_repo=Depends(get_perception_repo),
):
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
        state, conversation_id, file_name, target_file["file_type"],
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
