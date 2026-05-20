import logging
import uuid

from fastapi import APIRouter, HTTPException, Request

from .schemas import (
    AgentInfo,
    ChatRequest,
    ChatResponse,
    ConversationInfo,
    ConversationListResponse,
    ConversationTokenInfo,
    ConversationUpdateRequest,
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
)
from backend.utils.token_counter import estimate_tokens

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


async def _generate_title(llm_provider, first_message: str) -> str:
    try:
        result = await llm_provider.generate(
            messages=[
                {
                    "role": "system",
                    "content": "Generate a concise 3-6 word title for a conversation. Return only the title, no quotes, no punctuation at the end.",
                },
                {
                    "role": "user",
                    "content": f"Generate a short title for a conversation that starts with this message: \"{first_message[:300]}\"",
                },
            ],
            temperature=0.3,
            max_tokens=30,
        )
        content = result.get("content", "").strip().strip('"').strip("'")
        if not content:
            return first_message[:60]
        return content
    except Exception:
        logger.debug("Title generation failed, using fallback", exc_info=True)
        return first_message[:60]


async def _get_or_create_conversation(
    conv_repo, conversation_id: str, agent_id: str
) -> str:
    if conversation_id and conv_repo.get(conversation_id):
        return conversation_id
    conv_id = str(uuid.uuid4())
    conv_repo.create(conversation_id=conv_id, agent_id=agent_id)
    return conv_id


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request):
    state = request.app.state
    pipeline = state.pipeline
    repo = state.message_repo
    error_repo = state.error_repo
    metrics_repo = getattr(state, "metrics_repo", None)
    conv_repo = getattr(state, "conversation_repo", None)
    agent_id = getattr(state, "agent_name", "symbia")
    llm_provider = getattr(state, "llm_provider", None)

    conversation_id = body.conversation_id or ""
    is_new = False

    if conv_repo:
        if not conversation_id or not conv_repo.get(conversation_id):
            conversation_id = str(uuid.uuid4())
            conv_repo.create(conversation_id=conversation_id, agent_id=agent_id)
            is_new = True
        else:
            conv_repo.touch(conversation_id)

    try:
        result = await pipeline.run({
            "content": body.content,
            "speaker": body.speaker,
            "conversation_id": conversation_id,
        })

        response_text = result.payload.get("response", "")
        thinking = result.payload.get("thinking")
        embedding = result.payload.get("embedding", b"")
        embedding_model = result.payload.get("embedding_model", "unknown")
        embedding_dim = result.payload.get("embedding_dim", 0)

        if result.status == "error" or not response_text:
            for err in result.errors:
                error_repo.log_error(
                    module=err["module"],
                    error=RuntimeError(err["error_message"]),
                    context={"input": body.content},
                )
            raise HTTPException(status_code=500, detail="Pipeline processing failed")

        content_tokens = estimate_tokens(body.content)

        msg = repo.insert(
            speaker=body.speaker,
            content=body.content,
            embedding=embedding,
            embedding_model=embedding_model,
            embedding_dim=embedding_dim,
            agent_id=agent_id,
            conversation_id=conversation_id,
            content_tokens=content_tokens,
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

        if is_new and conv_repo and llm_provider:
            try:
                title = await _generate_title(llm_provider, body.content)
                conv_repo.update_title(conversation_id, title)
            except Exception:
                logger.exception("Failed to generate conversation title")

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
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Chat endpoint error")
        error_repo.log_error(module="api", error=e, context={"input": body.content})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent", response_model=AgentInfo)
async def get_agent(request: Request):
    state = request.app.state
    return AgentInfo(
        name=getattr(state, "agent_name", "symbia"),
    )


@router.get("/history", response_model=HistoryResponse)
async def history(limit: int = 50, conversation_id: str = "", request: Request = None):
    state = request.app.state
    repo = state.message_repo
    rows = repo.get_recent_with_metrics(
        limit=limit,
        conversation_id=conversation_id if conversation_id else None,
    )
    messages: list[HistoryMessage] = []
    for r in rows:
        metrics = _build_history_metrics(r)
        messages.append(HistoryMessage(
            id=r["id"],
            timestamp=r["timestamp"],
            speaker=r["speaker"],
            content=r["content"],
            thinking=r.get("thinking"),
            content_tokens=r.get("content_tokens", 0),
            thinking_tokens=r.get("thinking_tokens"),
            metrics=metrics,
        ))
    return HistoryResponse(
        messages=messages,
        count=len(messages),
    )


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
            pipeline.append(SkillInfo(
                name=meta.name,
                description=meta.description,
                category=meta.category,
                always_run=True,
                triggers=list(meta.triggers),
                cost=meta.cost,
                status=status.get(name, False),
            ))

    for name, _ in registry.list_always_on():
        if name not in seen:
            meta = registry.get_meta(name)
            if meta:
                seen.add(name)
                pipeline.append(SkillInfo(
                    name=meta.name,
                    description=meta.description,
                    category=meta.category,
                    always_run=True,
                    triggers=list(meta.triggers),
                    cost=meta.cost,
                    status=status.get(name, False),
                ))

    on_demand: list[SkillInfo] = []
    for name, _, meta in registry.list_on_demand():
        on_demand.append(SkillInfo(
            name=meta.name,
            description=meta.description,
            category=meta.category,
            always_run=False,
            triggers=list(meta.triggers),
            cost=meta.cost,
            status=status.get(name, False),
        ))

    return SkillsResponse(pipeline=pipeline, on_demand=on_demand)


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

    return MetricsResponse(
        window_size=aggregates.get("count", 0),
        aggregates=aggregates,
        latest=latest_info,
        recommendations=recommendations,
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
