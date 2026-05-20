import logging

from fastapi import APIRouter, HTTPException, Request

from .schemas import (
    AgentInfo,
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    HealthResponse,
    HistoryMessage,
    HistoryResponse,
    HomeostaticRecommendations,
    MetricsInfo,
    MetricsResponse,
    SkillInfo,
    SkillsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request):
    state = request.app.state
    pipeline = state.pipeline
    repo = state.message_repo
    error_repo = state.error_repo
    metrics_repo = getattr(state, "metrics_repo", None)
    agent_id = getattr(state, "agent_name", "symbia")

    try:
        result = await pipeline.run({
            "content": body.content,
            "speaker": body.speaker,
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

        msg = repo.insert(
            speaker=body.speaker,
            content=body.content,
            embedding=embedding,
            embedding_model=embedding_model,
            embedding_dim=embedding_dim,
            agent_id=agent_id,
        )

        response_msg = repo.insert(
            speaker="apparatus",
            content=response_text,
            thinking=thinking,
            embedding=embedding,
            embedding_model=embedding_model,
            embedding_dim=embedding_dim,
            agent_id=agent_id,
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

        return ChatResponse(
            id=response_msg.id,
            timestamp=response_msg.timestamp,
            speaker="apparatus",
            content=response_text,
            thinking=thinking,
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
async def history(limit: int = 50, request: Request = None):
    state = request.app.state
    repo = state.message_repo
    messages = repo.get_recent(limit=limit)
    return HistoryResponse(
        messages=[
            HistoryMessage(
                id=m.id,
                timestamp=m.timestamp,
                speaker=m.speaker,
                content=m.content,
                thinking=m.thinking,
            )
            for m in messages
        ],
        count=len(messages),
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
            homeostatic_deficit=latest.deficit,
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

    metrics_repo.insert(
        message_id=message_id,
        s_t=float(s_t),
        novelty=float(novelty),
        deficit=float(metrics.get("homeostatic_deficit", 0.0)),
        rolling_entropy=float(metrics["rolling_entropy"]) if metrics.get("rolling_entropy") is not None else None,
        coupling=float(metrics["coupling_coherence"]) if metrics.get("coupling_coherence") is not None else None,
        agent_divergence=float(metrics["agent_self_divergence"]) if metrics.get("agent_self_divergence") is not None else None,
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
        homeostatic_deficit=metrics.get("homeostatic_deficit"),
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
