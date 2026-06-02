import logging
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Header, Depends
import os
from dotenv import load_dotenv
load_dotenv()

from .schemas import (
    AgentInfo,
    AttachmentInfo,
    BackgroundTaskRequest,
    BackgroundTaskResponse,
    ChatRequest,
    ChatResponse,
    ConversationInfo,
    ConversationListResponse,
    ConversationTokenInfo,
    ConversationUpdateRequest,
    DiffractiveInfo,
    DiffractiveSourceInfo,
    ErrorResponse,
    HealthResponse,
    HistoryMessage,
    HistoryResponse,
    HomeostaticRecommendations,
    MetricsInfo,
    MetricsResponse,
    SkillInfo,
    SkillsResponse,
    TokenResponse,
    ConversationFile,
    ConversationFilesResponse,
)
from backend.utils.token_counter import estimate_tokens
from backend.modules.structural_engine import CompositeStructuralScorer

logger = logging.getLogger(__name__)

AAA_PASSWORD = os.environ.get("AAA_PASSWORD", "").strip()

async def verify_password(authorization: Optional[str] = Header(None)):
    if not AAA_PASSWORD:
        return
    
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = None
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    
    if token != AAA_PASSWORD:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

router = APIRouter(prefix="/api", dependencies=[Depends(verify_password)])

@router.get("/auth/verify")
async def verify_auth(request: Request):
    """
    Check if the client is authenticated (or if authentication is disabled).
    """
    return {
        "status": "authenticated",
        "auth_enabled": bool(AAA_PASSWORD)
    }



async def _parse_chat_request(request: Request) -> tuple[str, str, str, Optional[list[dict]], Optional[bool]]:
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        content = str(form.get("content", ""))
        conversation_id = str(form.get("conversation_id", ""))
        speaker = str(form.get("speaker", "human"))
        uploaded_files = form.getlist("files")
        include_structural_scoring_raw = form.get("include_structural_scoring")
        if include_structural_scoring_raw is not None:
            include_structural_scoring = str(include_structural_scoring_raw).lower() in ("true", "1", "yes")
        else:
            include_structural_scoring = None

        attachments: list[dict] = []
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
            else:
                file_type = "txt"
            attachments.append({
                "file_name": f.filename,
                "file_type": file_type,
                "content": file_bytes,
            })

        return content, speaker, conversation_id, (attachments if attachments else None), include_structural_scoring

    body = await request.json()
    content = body.get("content", "")
    speaker = body.get("speaker", "human")
    conversation_id = body.get("conversation_id", "")
    json_attachments = body.get("attachments")
    include_structural_scoring = body.get("include_structural_scoring")
    parsed_attachments = None
    if json_attachments:
        parsed_attachments = [
            {
                "file_name": a.get("file_name", ""),
                "file_type": a.get("file_type", "txt"),
                "content": a.get("content", ""),
            }
            for a in json_attachments
        ] if isinstance(json_attachments, list) else None

    return content, speaker, conversation_id, parsed_attachments, include_structural_scoring


async def _generate_title(engine, first_message: str) -> str:
    try:
        result = await engine.run("generate_title", {"text": first_message[:300]})
        content = result.get("content", "").strip().strip('"').strip("'")
        if not content:
            return first_message[:60]
        return content
    except Exception:
        logger.debug("Title generation failed, using fallback", exc_info=True)
        return first_message[:60]


async def _generate_title_from_conversation(engine, message_repo, conversation_id: str) -> str:
    """Generate a title from the conversation's message history."""
    try:
        rows = message_repo.get_recent_with_metrics(limit=20, conversation_id=conversation_id)
        if not rows:
            return "Untitled"
        lines = []
        for r in rows:
            speaker = r.get("speaker", "unknown")
            content = r.get("content", "")[:300]
            if speaker == "human":
                lines.append(f"Human: {content}")
            else:
                lines.append(f"Agent: {content}")
        context = "\n".join(lines)

        result = await engine.run("generate_title", {
            "context": {"first_message": rows[0].get("content", "")[:300]},
            "text": context[:2000],
        })
        content = result.get("content", "").strip().strip('"').strip("'")
        if not content:
            return rows[0].get("content", "")[:60]
        return content
    except Exception:
        logger.debug("Conversation title generation failed", exc_info=True)
        return "Untitled"


def _fire_and_forget_consolidation(engine, message_repo, checkpoint_repo, conversation_id: str, msg_count: int) -> None:
    """Trigger a background consolidation checkpoint without blocking."""
    import asyncio

    async def _do_consolidate():
        try:
            rows = message_repo.get_recent_with_metrics(limit=msg_count + 10, conversation_id=conversation_id)
            if not rows:
                return
            lines = []
            for r in rows:
                speaker = r.get("speaker", "unknown")
                content = r.get("content", "")[:500]
                label = "Human" if speaker == "human" else "Agent"
                lines.append(f"{label}: {content}")
            text = "\n".join(lines)

            result = await engine.run("consolidate", {
                "text": text,
                "context": {"messages": [
                    {"speaker": r.get("speaker", "unknown"), "content": r.get("content", "")}
                    for r in rows
                ]},
            })

            summary = result.get("content", "").strip()
            if summary and checkpoint_repo:
                model_used = result.get("model", "")
                checkpoint_repo.save(conversation_id, msg_count, summary, model_used)
                logger.info("Consolidation checkpoint saved for %s (%d msgs)", conversation_id, msg_count)
        except Exception:
            logger.exception("Background consolidation failed")

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_do_consolidate())
    except RuntimeError:
        pass


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request):
    content, speaker, conversation_id, attachments, include_structural_scoring = await _parse_chat_request(request)

    state = request.app.state
    pipeline = state.pipeline
    repo = state.message_repo
    error_repo = state.error_repo
    metrics_repo = getattr(state, "metrics_repo", None)
    conv_repo = getattr(state, "conversation_repo", None)
    agent_id = getattr(state, "agent_name", "symbia")
    background_engine = getattr(state, "background_engine", None)

    is_new = False

    if conv_repo:
        if not conversation_id or not conv_repo.get(conversation_id):
            conversation_id = str(uuid.uuid4())
            conv_repo.create(conversation_id=conversation_id, agent_id=agent_id)
            is_new = True
        else:
            conv_repo.touch(conversation_id)

    try:
        initial_payload: dict = {
            "content": content,
            "speaker": speaker,
            "conversation_id": conversation_id,
            "include_structural_scoring": include_structural_scoring,
        }
        if attachments:
            initial_payload["attachments"] = attachments

        result = await pipeline.run(initial_payload)

        response_text = result.payload.get("response", "")
        thinking = result.payload.get("thinking")
        embedding = result.payload.get("embedding", b"")
        embedding_model = result.payload.get("embedding_model", "unknown")
        embedding_dim = result.payload.get("embedding_dim", 0)
        model_used = result.payload.get("model_used")
        provider_used = result.payload.get("provider_used")

        if result.status == "error" or not response_text:
            for err in result.errors:
                error_repo.log_error(
                    module=err["module"],
                    error=RuntimeError(err["error_message"]),
                    context={"input": content},
                )
            raise HTTPException(status_code=500, detail="Pipeline processing failed")

        content_tokens = estimate_tokens(content)

        # Calculate structural signatures
        scorer = CompositeStructuralScorer(llm_provider=request.app.state.structural_provider)
        try:
            user_sig = await scorer.score_async(content, use_llm_scorer=include_structural_scoring)
            user_sig_blob = user_sig.tobytes()
        except Exception as e:
            logger.warning("Failed to score user message: %s", e)
            user_sig_blob = b""

        try:
            assistant_sig = await scorer.score_async(response_text, use_llm_scorer=include_structural_scoring)
            assistant_sig_blob = assistant_sig.tobytes()
        except Exception as e:
            logger.warning("Failed to score assistant message: %s", e)
            assistant_sig_blob = b""

        msg = repo.insert(
            speaker=speaker,
            content=content,
            embedding=embedding,
            embedding_model=embedding_model,
            embedding_dim=embedding_dim,
            agent_id=agent_id,
            conversation_id=conversation_id,
            content_tokens=content_tokens,
            structural_signature=user_sig_blob,
        )

        thinking_tokens = estimate_tokens(thinking) if thinking else None

        response_msg = repo.insert(
            speaker="apparatus",
            content=response_text,
            thinking=thinking,
            embedding=embedding,
            embedding_model=embedding_model,
            embedding_dim=embedding_dim,
            agent_id=agent_id,
            conversation_id=conversation_id,
            content_tokens=estimate_tokens(response_text),
            thinking_tokens=thinking_tokens,
            model_used=model_used,
            provider_used=provider_used,
            structural_signature=assistant_sig_blob,
        )

        payload_metrics = result.payload.get("metrics")
        recommendations = result.payload.get("homeostatic_recommendations")

        if payload_metrics and metrics_repo:
            try:
                _store_metrics(
                    metrics_repo=metrics_repo,
                    message_id=msg.id,
                    metrics=payload_metrics,
                    recommendations=recommendations,
                )
            except Exception:
                logger.exception("Failed to store metrics")

        if is_new and conv_repo and background_engine:
            try:
                title = await _generate_title(background_engine, content)
                conv_repo.update_title(conversation_id, title)
            except Exception:
                logger.exception("Failed to generate conversation title")

        if not is_new and conv_repo and background_engine:
            conv = conv_repo.get(conversation_id)
            if conv and not conv.title.strip():
                msg_count = repo.count_messages(conversation_id)
                if msg_count >= 3:
                    try:
                        title = await _generate_title_from_conversation(
                            background_engine, repo, conversation_id
                        )
                        conv_repo.update_title(conversation_id, title)
                    except Exception:
                        logger.exception("Failed to auto-generate conversation title")

        if result.payload.get("trigger_consolidation") and background_engine and conv_repo:
            _fire_and_forget_consolidation(
                background_engine, repo,
                getattr(state, "checkpoint_repo", None),
                conversation_id,
                result.payload.get("consolidate_message_count", 0),
            )

        response_attachments = _build_response_attachments(attachments, result)

        # Store latest diffractive meta on app.state for the /metrics endpoint
        diff_meta = result.payload.get("diffractive_meta")
        if diff_meta:
            request.app.state.latest_diffractive_meta = diff_meta

        from backend.modules.structural_engine import get_justification
        justification = get_justification(response_text)
        user_justification = get_justification(content)
        user_sig_list = user_sig.tolist() if 'user_sig' in locals() and user_sig is not None else None

        return ChatResponse(
            id=response_msg.id,
            timestamp=response_msg.timestamp,
            conversation_id=conversation_id,
            speaker="apparatus",
            content=response_text,
            thinking=thinking,
            content_tokens=estimate_tokens(response_text),
            thinking_tokens=thinking_tokens,
            embedding_generated=bool(embedding),
            metrics=_build_metrics_info(payload_metrics),
            homeostatic_recommendations=_build_recommendations(recommendations),
            attachments=response_attachments,
            context_sent=result.payload.get("context_sent"),
            model_used=response_msg.model_used,
            provider_used=response_msg.provider_used,
            structural_justification=justification,
            user_message_id=msg.id,
            user_structural_signature=user_sig_list,
            user_structural_justification=user_justification,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Chat endpoint error")
        error_repo.log_error(module="api", error=e, context={"input": content})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent", response_model=AgentInfo)
async def get_agent(request: Request):
    state = request.app.state
    return AgentInfo(
        name=getattr(state, "agent_name", "symbia"),
    )


@router.get("/history", response_model=HistoryResponse)
async def history(limit: int = 50, offset: int = 0, conversation_id: str = "", request: Request = None):
    state = request.app.state
    repo = state.message_repo
    rows = repo.get_recent_with_metrics(
        limit=limit,
        offset=offset,
        conversation_id=conversation_id if conversation_id else None,
    )
    messages: list[HistoryMessage] = []
    from backend.modules.structural_engine import get_justification
    for r in rows:
        metrics = _build_history_metrics(r)
        
        sig_bytes = r.get("structural_signature")
        sig_list = None
        if sig_bytes:
            try:
                import numpy as np
                arr = np.frombuffer(sig_bytes, dtype=np.float32)
                sig_list = arr.tolist()
            except Exception:
                pass
                
        justification = get_justification(r["content"])

        messages.append(HistoryMessage(
            id=r["id"],
            timestamp=r["timestamp"],
            speaker=r["speaker"],
            content=r["content"],
            thinking=None,  # Lazy loaded on expand
            context_sent=None,  # Lazy loaded on expand
            has_context=bool(r.get("has_context")),
            content_tokens=r.get("content_tokens", 0),
            thinking_tokens=r.get("thinking_tokens"),
            metrics=metrics,
            model_used=r.get("model_used"),
            provider_used=r.get("provider_used"),
            structural_signature=sig_list,
            structural_justification=justification,
        ))
    
    total_count = repo.count_messages(conversation_id if conversation_id else None)

    return HistoryResponse(
        messages=messages,
        count=total_count,
    )


@router.get("/messages/{message_id}/thinking")
async def get_message_thinking(message_id: int, request: Request):
    state = request.app.state
    repo = state.message_repo
    msg = repo.get_by_id(message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"thinking": msg.thinking}


@router.get("/messages/{message_id}/context")
async def get_message_context(message_id: int, request: Request):
    state = request.app.state
    repo = state.message_repo
    msg = repo.get_by_id(message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"context_sent": msg.context_sent}


@router.get("/conversations/{conversation_id}/files/{file_name:path}/summary")
async def get_file_summary_endpoint(conversation_id: str, file_name: str, request: Request):
    state = request.app.state
    perception_repo = state.perception_repo
    files = perception_repo.get_files_by_conversation(conversation_id)
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
            return res_data
    raise HTTPException(status_code=404, detail="File not found")


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(request: Request):
    state = request.app.state
    conv_repo = getattr(state, "conversation_repo", None)
    if not conv_repo:
        return ConversationListResponse(conversations=[])
    convos = conv_repo.list_all()
    return ConversationListResponse(conversations=[
        ConversationInfo(
            id=c.id,
            title=c.title,
            created_at=c.created_at,
            updated_at=c.updated_at,
            message_count=c.message_count,
        )
        for c in convos
    ])


@router.get("/conversations/{conversation_id}", response_model=ConversationInfo)
async def get_conversation(conversation_id: str, request: Request):
    state = request.app.state
    conv_repo = getattr(state, "conversation_repo", None)
    if not conv_repo:
        raise HTTPException(status_code=404, detail="Conversations not available")
    conv = conv_repo.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationInfo(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=conv.message_count,
    )


@router.patch("/conversations/{conversation_id}", response_model=ConversationInfo)
async def update_conversation(
    conversation_id: str, body: ConversationUpdateRequest, request: Request
):
    state = request.app.state
    conv_repo = getattr(state, "conversation_repo", None)
    if not conv_repo:
        raise HTTPException(status_code=404, detail="Conversations not available")
    conv = conv_repo.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv_repo.update_title(conversation_id, body.title)
    conv = conv_repo.get(conversation_id)
    return ConversationInfo(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=conv.message_count,
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, request: Request):
    state = request.app.state
    conv_repo = getattr(state, "conversation_repo", None)
    if not conv_repo:
        raise HTTPException(status_code=404, detail="Conversations not available")
    conv = conv_repo.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv_repo.delete(conversation_id)
    return {"status": "deleted", "id": conversation_id}


@router.post("/conversations/{conversation_id}/generate-title", response_model=ConversationInfo)
async def generate_conversation_title(conversation_id: str, request: Request):
    state = request.app.state
    conv_repo = getattr(state, "conversation_repo", None)
    if not conv_repo:
        raise HTTPException(status_code=404, detail="Conversations not available")
    conv = conv_repo.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    background_engine = getattr(state, "background_engine", None)
    if not background_engine:
        raise HTTPException(status_code=503, detail="Background engine not available")

    title = await _generate_title_from_conversation(
        background_engine, request.app.state.message_repo, conversation_id
    )
    conv_repo.update_title(conversation_id, title)

    conv = conv_repo.get(conversation_id)
    return ConversationInfo(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=conv.message_count,
    )


@router.get("/tokens", response_model=TokenResponse)
async def get_tokens(conversation_id: str = "", request: Request = None):
    state = request.app.state
    repo = state.message_repo
    conv_repo = getattr(state, "conversation_repo", None)
    system_prompt_tokens = getattr(state, "system_prompt_tokens", 0)

    totals = repo.get_token_totals(
        conversation_id=conversation_id if conversation_id else None
    )

    conversation_tokens: list[ConversationTokenInfo] = []
    for t in totals:
        conv_id = t["conversation_id"]
        title = ""
        if conv_repo:
            conv = conv_repo.get(conv_id)
            if conv:
                title = conv.title
        total = t["user_tokens"] + t["agent_tokens"] + t["thinking_tokens"]
        conversation_tokens.append(ConversationTokenInfo(
            conversation_id=conv_id,
            title=title,
            user_tokens=t["user_tokens"],
            agent_tokens=t["agent_tokens"],
            thinking_tokens=t["thinking_tokens"],
            total_tokens=total,
        ))

    grand_total = system_prompt_tokens + sum(c.total_tokens for c in conversation_tokens)

    return TokenResponse(
        conversations=conversation_tokens,
        system_prompt_tokens=system_prompt_tokens,
        grand_total_tokens=grand_total,
    )


@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    state = request.app.state
    registry = state.registry
    modules_status = registry.validate_all()
    return HealthResponse(
        status="ok",
        modules=modules_status,
    )


@router.post("/background", response_model=BackgroundTaskResponse)
async def run_background_task(body: BackgroundTaskRequest, request: Request):
    state = request.app.state
    engine = getattr(state, "background_engine", None)
    if not engine:
        raise HTTPException(status_code=503, detail="Background engine not initialized")

    try:
        payload = {
            "text": body.text,
            "conversation_id": body.conversation_id,
            "context": body.context or {},
            "use_vision": body.use_vision,
        }
        result = await engine.run(body.action, payload)
        return BackgroundTaskResponse(
            action=body.action,
            result=result.get("content", ""),
            model_used=result.get("model", ""),
            error=result.get("error"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Background task error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/errors", response_model=list[dict])
async def list_errors(limit: int = 20, request: Request = None):
    state = request.app.state
    error_repo = state.error_repo
    errors = error_repo.get_recent(limit=limit)
    return [
        {
            "id": e.id,
            "timestamp": e.timestamp.isoformat(),
            "module": e.module,
            "error_type": e.error_type,
            "error_message": e.error_message,
            "context": e.context,
        }
        for e in errors
    ]


@router.get("/skills", response_model=SkillsResponse)
async def get_skills(request: Request):
    state = request.app.state
    registry = state.registry
    pipeline_order = getattr(state, "pipeline_order", [])

    status = registry.validate_all()

    pipeline: list[SkillInfo] = []
    seen: set[str] = set()

    for name in pipeline_order:
        meta = registry.get_meta(name)
        if meta and name not in seen:
            seen.add(name)
            pipeline.append(_meta_to_skillinfo(meta, status, True))

    for name, _ in registry.list_always_on():
        if name not in seen:
            meta = registry.get_meta(name)
            if meta:
                seen.add(name)
                pipeline.append(_meta_to_skillinfo(meta, status, True))

    on_demand: list[SkillInfo] = []
    for name, _, meta in registry.list_on_demand():
        on_demand.append(_meta_to_skillinfo(meta, status, False))

    return SkillsResponse(pipeline=pipeline, on_demand=on_demand)


def _meta_to_skillinfo(meta, status: dict[str, bool], always_run: bool, parent_status: Optional[bool] = None) -> SkillInfo:
    self_status = status.get(meta.name, parent_status if parent_status is not None else False)
    return SkillInfo(
        name=meta.name,
        description=meta.description,
        category=meta.category,
        always_run=always_run,
        triggers=list(meta.triggers),
        cost=meta.cost,
        status=self_status,
        children=[
            _meta_to_skillinfo(child, status, always_run=True, parent_status=self_status)
            for child in meta.children
        ],
    )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(request: Request, window: int = 20):
    state = request.app.state
    metrics_repo = getattr(state, "metrics_repo", None)
    if not metrics_repo:
        return MetricsResponse(window_size=0, aggregates={"count": 0})

    aggregates = metrics_repo.get_aggregates(limit=max(1, min(window, 100)))
    latest = metrics_repo.get_latest()

    latest_info: MetricsInfo | None = None
    recommendations: HomeostaticRecommendations | None = None
    if latest is not None:
        latest_info = MetricsInfo(
            pairwise_similarity=latest.s_t,
            conceptual_novelty=latest.novelty,
            rolling_entropy=latest.rolling_entropy,
            coupling_coherence=latest.coupling,
            agent_self_divergence=latest.agent_divergence,
            reverse_perturbation=latest.reverse_perturbation,
            surprise_index=latest.surprise_index,
            mutual_perturbation=latest.mutual_perturbation,
            homeostatic_deficit=latest.deficit,
            conversation_vitality=latest.vitality,
            boringness=latest.boringness,
            conceptual_velocity=latest.conceptual_velocity,
            divergence_resolution_ratio=latest.divergence_resolution_ratio,
            paskian_health=latest.paskian_health,
            phase_shifts=_parse_phase_shifts(latest.phase_shifts),
        )
        temp_rec = None
        pres_rec = None
        freq_rec = None
        if latest.temperature_rec is not None:
            temp_rec = {"value": latest.temperature_rec, "base": 0.7, "delta": round(latest.temperature_rec - 0.7, 3), "clamped": False}
        if latest.presence_penalty_rec is not None:
            pres_rec = {"value": latest.presence_penalty_rec, "base": 0.0, "delta": round(latest.presence_penalty_rec, 3), "clamped": False}
        if latest.frequency_penalty_rec is not None:
            freq_rec = {"value": latest.frequency_penalty_rec, "base": 0.0, "delta": round(latest.frequency_penalty_rec, 3), "clamped": False}
        recommendations = HomeostaticRecommendations(
            temperature=temp_rec,
            presence_penalty=pres_rec,
            frequency_penalty=freq_rec,
            state=latest.homeostatic_state or "healthy",
        )

    # Build diffractive info from latest cached state
    diff_info = None
    raw_diff = getattr(state, "latest_diffractive_meta", None)
    if raw_diff:
        diff_sources = [
            DiffractiveSourceInfo(**s) for s in raw_diff.get("sources", [])
        ]
        diff_info = DiffractiveInfo(
            state=raw_diff.get("state", "FLOWING"),
            previous_state=raw_diff.get("previous_state", "FLOWING"),
            p_diffract=raw_diff.get("p_diffract", 0.0),
            stagnation_index=raw_diff.get("stagnation_index", 0.0),
            r_context=raw_diff.get("r_context", 0.0),
            dynamic_max=raw_diff.get("dynamic_max", 0),
            cohesion_timer=raw_diff.get("cohesion_timer", 0),
            similarity_range_memory=raw_diff.get("similarity_range_memory", []),
            similarity_range_files=raw_diff.get("similarity_range_files", []),
            candidates_searched=raw_diff.get("candidates_searched", 0),
            items_injected=raw_diff.get("items_injected", 0),
            tokens_used=raw_diff.get("tokens_used", 0),
            token_budget=raw_diff.get("token_budget", 0),
            duration_ms=raw_diff.get("duration_ms", 0.0),
            sources=diff_sources,
        )

    return MetricsResponse(
        window_size=aggregates.get("count", 0),
        aggregates=aggregates,
        latest=latest_info,
        recommendations=recommendations,
        diffractive=diff_info,
    )


def _store_metrics(metrics_repo, message_id: int, metrics: dict, recommendations: dict | None) -> None:
    s_t = metrics.get("pairwise_similarity")
    novelty = metrics.get("conceptual_novelty")
    if s_t is None or novelty is None:
        return

    temp_rec = None
    pres_rec = None
    freq_rec = None
    homeo_state = None
    if recommendations:
        t = recommendations.get("temperature")
        p = recommendations.get("presence_penalty")
        f = recommendations.get("frequency_penalty")
        if isinstance(t, dict):
            temp_rec = t.get("value")
        if isinstance(p, dict):
            pres_rec = p.get("value")
        if isinstance(f, dict):
            freq_rec = f.get("value")
        homeo_state = recommendations.get("state")

    phase_shifts = metrics.get("phase_shifts")
    phase_shifts_json = None
    if phase_shifts:
        import json as _json
        phase_shifts_json = _json.dumps(phase_shifts)

    metrics_repo.insert(
        message_id=message_id,
        s_t=float(s_t),
        novelty=float(novelty),
        deficit=float(metrics.get("homeostatic_deficit", 0.0)),
        rolling_entropy=float(metrics["rolling_entropy"]) if metrics.get("rolling_entropy") is not None else None,
        coupling=float(metrics["coupling_coherence"]) if metrics.get("coupling_coherence") is not None else None,
        agent_divergence=float(metrics["agent_self_divergence"]) if metrics.get("agent_self_divergence") is not None else None,
        reverse_perturbation=float(metrics["reverse_perturbation"]) if metrics.get("reverse_perturbation") is not None else None,
        surprise_index=float(metrics["surprise_index"]) if metrics.get("surprise_index") is not None else None,
        mutual_perturbation=float(metrics["mutual_perturbation"]) if metrics.get("mutual_perturbation") is not None else None,
        vitality=float(metrics["conversation_vitality"]) if metrics.get("conversation_vitality") is not None else None,
        phase_shifts=phase_shifts_json,
        boringness=float(metrics["boringness"]) if metrics.get("boringness") is not None else None,
        conceptual_velocity=float(metrics["conceptual_velocity"]) if metrics.get("conceptual_velocity") is not None else None,
        divergence_resolution_ratio=float(metrics["divergence_resolution_ratio"]) if metrics.get("divergence_resolution_ratio") is not None else None,
        paskian_health=float(metrics["paskian_health"]) if metrics.get("paskian_health") is not None else None,
        temperature_rec=float(temp_rec) if temp_rec is not None else None,
        presence_penalty_rec=float(pres_rec) if pres_rec is not None else None,
        frequency_penalty_rec=float(freq_rec) if freq_rec is not None else None,
        homeostatic_state=homeo_state,
    )


def _build_metrics_info(metrics: dict | None) -> MetricsInfo | None:
    if not metrics:
        return None
    return MetricsInfo(
        pairwise_similarity=metrics.get("pairwise_similarity"),
        conceptual_novelty=metrics.get("conceptual_novelty"),
        rolling_entropy=metrics.get("rolling_entropy"),
        coupling_coherence=metrics.get("coupling_coherence"),
        agent_self_divergence=metrics.get("agent_self_divergence"),
        reverse_perturbation=metrics.get("reverse_perturbation"),
        surprise_index=metrics.get("surprise_index"),
        mutual_perturbation=metrics.get("mutual_perturbation"),
        homeostatic_deficit=metrics.get("homeostatic_deficit"),
        conversation_vitality=metrics.get("conversation_vitality"),
        boringness=metrics.get("boringness"),
        conceptual_velocity=metrics.get("conceptual_velocity"),
        divergence_resolution_ratio=metrics.get("divergence_resolution_ratio"),
        paskian_health=metrics.get("paskian_health"),
        phase_shifts=metrics.get("phase_shifts"),
    )


def _build_recommendations(recs: dict | None) -> HomeostaticRecommendations | None:
    if not recs:
        return None
    return HomeostaticRecommendations(
        temperature=recs.get("temperature"),
        presence_penalty=recs.get("presence_penalty"),
        frequency_penalty=recs.get("frequency_penalty"),
        state=recs.get("state", "healthy"),
        triggered_flags=recs.get("triggered_flags", []),
    )


def _parse_phase_shifts(raw: str | None) -> list[dict] | None:
    if not raw:
        return None
    import json as _json
    try:
        return _json.loads(raw)
    except Exception:
        return None


def _build_history_metrics(row: dict) -> MetricsInfo | None:
    if row.get("s_t") is None:
        return None
    return MetricsInfo(
        pairwise_similarity=row.get("s_t"),
        conceptual_novelty=row.get("novelty"),
        rolling_entropy=row.get("rolling_entropy"),
        coupling_coherence=row.get("coupling"),
        agent_self_divergence=row.get("agent_divergence"),
        reverse_perturbation=row.get("reverse_perturbation"),
        surprise_index=row.get("surprise_index"),
        mutual_perturbation=row.get("mutual_perturbation"),
        homeostatic_deficit=row.get("deficit"),
        conversation_vitality=row.get("vitality"),
        boringness=row.get("boringness"),
        conceptual_velocity=row.get("conceptual_velocity"),
        divergence_resolution_ratio=row.get("divergence_resolution_ratio"),
        paskian_health=row.get("paskian_health"),
        phase_shifts=None,
    )


def _build_response_attachments(
    attachments: list[dict] | None, result
) -> list[AttachmentInfo] | None:
    if not attachments:
        return None
    response_attachments: list[AttachmentInfo] = []
    for att in attachments:
        file_name = att.get("file_name", "")
        file_type = att.get("file_type", "txt")
        content = att.get("content", "")
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        token_count = estimate_tokens(content) if content else 0
        preview = content[:200] if content else None
        response_attachments.append(AttachmentInfo(
            file_name=file_name,
            file_type=file_type,
            token_count=token_count,
            preview=preview,
        ))
    return response_attachments if response_attachments else None


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

    # Calculate structural signature
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
    )


async def _process_and_summarize_file(
    app_state,
    conversation_id: str,
    file_name: str,
    file_type: str,
    file_content: bytes,
):
    perception_module = app_state.perception_module
    perception_repo = app_state.perception_repo
    background_engine = app_state.background_engine
    error_repo = app_state.error_repo

    try:
        perception_repo.update_file(
            conversation_id=conversation_id,
            file_name=file_name,
            status="processing"
        )

        token_count, chunk_count, extracted_text = await perception_module.ingest_single_file(
            conversation_id, file_name, file_type, file_content
        )

        summary_text = ""
        summary_model = ""
        if file_type == "image":
            # Extract summary from image description
            parts = extracted_text.split("Transcription (OCR):")
            summary_text = parts[0].replace(f"--- Ingested Image: {file_name} ---", "").strip()
            summary_model = "Tripartite Vision Pipeline"
        elif background_engine:
            try:
                res = await background_engine.run("summarize", {"text": extracted_text})
                if res.get("error"):
                    raise RuntimeError(res["error"])
                summary_text = res.get("content", "").strip()
                summary_model = res.get("model", "")
                
                # Apply opacity updates to chunks
                opacity_map = res.get("opacity_map", [])
                if opacity_map:
                    chunks = perception_repo.get_by_file(conversation_id, file_name)
                    op_map_by_p = {item["paragraph_index"]: item for item in opacity_map}
                    
                    import json as _json
                    for chunk in chunks:
                        try:
                            meta = _json.loads(chunk.opacity_meta) if chunk.opacity_meta else {}
                        except Exception:
                            meta = {}
                        
                        p_indices = meta.get("paragraph_indices", [])
                        opaque_hits = [op_map_by_p[pi] for pi in p_indices if pi in op_map_by_p]
                        
                        if opaque_hits:
                            reasons = [h["reason"] for h in opaque_hits if h.get("reason")]
                            shadows = [h["shadow_text"] for h in opaque_hits if h.get("shadow_text")]
                            
                            new_meta = {
                                "paragraph_indices": p_indices,
                                "opaque_hits": opaque_hits,
                                "reason": "; ".join(reasons),
                                "shadow_text": "\n\n".join(shadows),
                            }
                            perception_repo.update_chunk_opacity(
                                chunk_id=chunk.id,
                                opacity=1,
                                opacity_meta=_json.dumps(new_meta),
                            )
            except Exception as se:
                logger.error("Failed to run SummarizeAction for %s: %s", file_name, se)
                raise se


        perception_repo.update_file(
            conversation_id=conversation_id,
            file_name=file_name,
            status="ready",
            summary=summary_text,
            summary_model=summary_model,
            token_count=token_count,
            chunk_count=chunk_count,
        )

        system_content = f"Processed file: **{file_name}** ({file_type}).\n\nAccording to {summary_model or 'the system'}, this file appears to be about:\n{summary_text or 'No summary could be generated.'}"
        await _insert_system_message(app_state, conversation_id, system_content)

    except Exception as e:
        logger.exception("Background processing of %s failed", file_name)
        if error_repo:
            error_repo.log_error(
                module="perception_upload",
                error=e,
                context={"conversation_id": conversation_id, "file_name": file_name},
            )
        try:
            perception_repo.update_file(
                conversation_id=conversation_id,
                file_name=file_name,
                status="error",
                summary=f"Failed to process file: {str(e)}"
            )
        except Exception:
            pass


async def _reprocess_and_summarize_file_background(
    app_state,
    conversation_id: str,
    file_name: str,
    file_type: str,
):
    perception_repo = app_state.perception_repo
    background_engine = app_state.background_engine
    error_repo = app_state.error_repo

    try:
        chunks = perception_repo.get_by_file(conversation_id, file_name)
        if not chunks:
            raise ValueError("No chunks found in database for this file. Please delete and re-upload.")

        sorted_chunks = sorted(chunks, key=lambda c: c.chunk_index)
        extracted_text = "\n\n".join(c.chunk_text for c in sorted_chunks)
        token_count = sum(c.token_count for c in sorted_chunks)
        chunk_count = len(sorted_chunks)

        summary_text = ""
        summary_model = ""
        if background_engine:
            res = await background_engine.run("summarize", {"text": extracted_text})
            if res.get("error"):
                raise RuntimeError(res["error"])
            summary_text = res.get("content", "").strip()
            summary_model = res.get("model", "")
            
            opacity_map = res.get("opacity_map", [])
            if opacity_map:
                op_map_by_p = {item["paragraph_index"]: item for item in opacity_map}
                
                import json as _json
                for chunk in sorted_chunks:
                    try:
                        meta = _json.loads(chunk.opacity_meta) if chunk.opacity_meta else {}
                    except Exception:
                        meta = {}
                    
                    p_indices = meta.get("paragraph_indices", [])
                    opaque_hits = [op_map_by_p[pi] for pi in p_indices if pi in op_map_by_p]
                    
                    if opaque_hits:
                        reasons = [h["reason"] for h in opaque_hits if h.get("reason")]
                        shadows = [h["shadow_text"] for h in opaque_hits if h.get("shadow_text")]
                        
                        new_meta = {
                            "paragraph_indices": p_indices,
                            "opaque_hits": opaque_hits,
                            "reason": "; ".join(reasons),
                            "shadow_text": "\n\n".join(shadows),
                        }
                        perception_repo.update_chunk_opacity(
                            chunk_id=chunk.id,
                            opacity=1,
                            opacity_meta=_json.dumps(new_meta),
                        )

        perception_repo.update_file(
            conversation_id=conversation_id,
            file_name=file_name,
            status="ready",
            summary=summary_text,
            summary_model=summary_model,
            token_count=token_count,
            chunk_count=chunk_count,
        )

        system_content = f"Processed file: **{file_name}** ({file_type}).\n\nAccording to {summary_model or 'the system'}, this file appears to be about:\n{summary_text or 'No summary could be generated.'}"
        await _insert_system_message(app_state, conversation_id, system_content)

    except Exception as e:
        logger.exception("Background reprocessing of %s failed", file_name)
        if error_repo:
            error_repo.log_error(
                module="perception_reprocess",
                error=e,
                context={"conversation_id": conversation_id, "file_name": file_name},
            )
        try:
            perception_repo.update_file(
                conversation_id=conversation_id,
                file_name=file_name,
                status="error",
                summary=f"Failed to process file: {str(e)}"
            )
        except Exception:
            pass


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
        else:
            file_type = "txt"

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
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
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
            summary=None,  # Loaded on demand
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
        
    # Schedule the reprocessing background task
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

