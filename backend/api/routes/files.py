import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from backend.modules.structural_engine import CompositeStructuralScorer, get_justification
from backend.utils.token_counter import estimate_tokens

from backend.api.schemas import ConversationFile, ConversationFilesResponse

logger = logging.getLogger(__name__)

router = APIRouter()


async def _insert_system_message(state, conversation_id: str, content: str):
    repo = state.message_repo
    embedder = state.embedder.service
    agent_id = getattr(state, "agent_name", "symbia")

    try:
        embedding_vec = await embedder.encode_async(content)
        embedding_blob = embedder.serialize(embedding_vec)
        embedding_dim = len(embedding_vec)
        embedding_model = embedder.model_name
    except Exception as e:
        logger.warning("Failed to generate embedding for system message: %s", e)
        embedding_blob = b""
        embedding_dim = 0
        embedding_model = "none"

    scorer = CompositeStructuralScorer(llm_provider=getattr(state, "structural_provider", None))
    try:
        sig_vec = await scorer.score_async(content)
        sig_blob = sig_vec.tobytes()
    except Exception as e:
        logger.warning("Failed to score system message: %s", e)
        sig_blob = b""

    repo.insert(
        speaker="system",
        content=content,
        embedding=embedding_blob,
        embedding_model=embedding_model,
        embedding_dim=embedding_dim,
        agent_id=agent_id,
        conversation_id=conversation_id,
        content_tokens=estimate_tokens(content),
        structural_signature=sig_blob,
        structural_justification=get_justification(content),
    )


async def _run_digest_worker_subprocess(conversation_id: str, file_name: str, file_type: str, reprocess: bool = False):
    cmd = [
        sys.executable,
        "-m",
        "backend.scripts.digest_worker",
        "--conversation_id", conversation_id,
        "--file_name", file_name,
        "--file_type", file_type,
    ]
    if reprocess:
        cmd.append("--reprocess")

    logger.info("Spawning async digest worker subprocess: %s", " ".join(cmd))

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err_msg = stderr.decode('utf-8', errors='replace').strip()
            logger.error("Digest worker failed with code %d for %s. Stderr:\n%s", proc.returncode, file_name, err_msg)
        else:
            out_msg = stdout.decode('utf-8', errors='replace').strip()
            logger.info("Digest worker completed successfully for %s. Output:\n%s", file_name, out_msg)
    except Exception as e:
        logger.exception("Failed to run digest worker subprocess for %s", file_name)


async def _process_and_summarize_file(
    app_state,
    conversation_id: str,
    file_name: str,
    file_type: str,
    file_content=None,
):
    await _run_digest_worker_subprocess(conversation_id, file_name, file_type, reprocess=False)


async def _reprocess_and_summarize_file_background(
    app_state,
    conversation_id: str,
    file_name: str,
    file_type: str,
):
    await _run_digest_worker_subprocess(conversation_id, file_name, file_type, reprocess=True)


@router.post("/conversations/{conversation_id}/files", response_model=ConversationFilesResponse)
async def upload_conversation_files(
    conversation_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
):
    state = request.app.state
    perception_repo = state.perception_repo
    conv_repo = getattr(state, "conversation_repo", None)
    agent_id = getattr(state, "agent_name", "symbia")

    form = await request.form()
    uploaded_files = form.getlist("files")

    if not uploaded_files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    if conversation_id == "new" or not conv_repo or not conv_repo.get(conversation_id):
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
        ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else "txt"
        if ext in ("jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"):
            file_type = "image"
        elif ext == "pdf":
            file_type = "pdf"
        elif ext == "docx":
            file_type = "docx"
        elif ext == "md":
            file_type = "md"
        elif ext == "epub":
            file_type = "epub"
        elif ext == "mobi":
            file_type = "mobi"
        else:
            file_type = "txt"

        upload_dir = os.path.join("backend", "data", "uploads", conversation_id)
        os.makedirs(upload_dir, exist_ok=True)
        cached_filepath = os.path.join(upload_dir, f.filename)
        with open(cached_filepath, "wb") as cache_file:
            cache_file.write(file_bytes)

        perception_repo.create_file(
            conversation_id=conversation_id,
            file_name=f.filename,
            file_type=file_type,
            status="uploading",
        )

        background_tasks.add_task(
            _process_and_summarize_file,
            state,
            conversation_id,
            f.filename,
            file_type,
            file_bytes,
        )

        schema_files.append(ConversationFile(
            file_name=f.filename,
            file_type=file_type,
            status="uploading",
            token_count=0,
            chunk_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ))

    return ConversationFilesResponse(conversation_id=conversation_id, files=schema_files)


@router.get("/conversations/{conversation_id}/files", response_model=ConversationFilesResponse)
async def get_conversation_files(conversation_id: str, request: Request):
    state = request.app.state
    perception_repo = state.perception_repo

    files = perception_repo.get_files_by_conversation(conversation_id)
    schema_files = []
    for f in files:
        created_at_dt = None
        if f.get("created_at"):
            try:
                created_at_dt = datetime.fromisoformat(f["created_at"].replace("Z", "+00:00"))
            except ValueError:
                try:
                    created_at_dt = datetime.strptime(f["created_at"], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass

        updated_at_dt = None
        if f.get("updated_at"):
            try:
                updated_at_dt = datetime.fromisoformat(f["updated_at"].replace("Z", "+00:00"))
            except ValueError:
                try:
                    updated_at_dt = datetime.strptime(f["updated_at"], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass

        schema_files.append(ConversationFile(
            file_name=f["file_name"],
            file_type=f["file_type"],
            status=f["status"],
            summary=None,
            summary_model=f.get("summary_model"),
            token_count=f.get("token_count", 0),
            chunk_count=f.get("chunk_count", 0),
            created_at=created_at_dt,
            updated_at=updated_at_dt,
        ))
    return ConversationFilesResponse(conversation_id=conversation_id, files=schema_files)


@router.delete("/conversations/{conversation_id}/files/{file_name}")
async def delete_conversation_file(conversation_id: str, file_name: str, request: Request):
    state = request.app.state
    perception_repo = state.perception_repo

    files = perception_repo.get_files_by_conversation(conversation_id)
    exists = any(f["file_name"] == file_name for f in files)
    if not exists:
        raise HTTPException(status_code=404, detail="File not found in conversation")

    try:
        cached_file = os.path.join("backend", "data", "uploads", conversation_id, file_name)
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
):
    state = request.app.state
    perception_repo = state.perception_repo

    files = perception_repo.get_files_by_conversation(conversation_id)
    target_file = None
    for f in files:
        if f["file_name"] == file_name:
            target_file = f
            break

    if not target_file:
        raise HTTPException(status_code=404, detail="File not found in conversation")

    perception_repo.update_file(
        conversation_id=conversation_id,
        file_name=file_name,
        status="processing",
    )

    background_tasks.add_task(
        _reprocess_and_summarize_file_background,
        state,
        conversation_id,
        file_name,
        target_file["file_type"],
    )

    return {"status": "success"}


@router.get("/conversations/{conversation_id}/files/{file_name:path}/summary")
async def get_file_summary_endpoint(conversation_id: str, file_name: str, request: Request):
    state = request.app.state
    perception_repo = state.perception_repo

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
async def get_file_by_name_endpoint(file_name: str, request: Request):
    state = request.app.state
    perception_repo = state.perception_repo

    file_info = perception_repo.find_file_by_name(file_name)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    chunks = perception_repo.get_chunks_by_file(file_info["conversation_id"], file_name)
    file_info["chunks"] = chunks
    return file_info
