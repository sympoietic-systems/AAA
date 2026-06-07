from fastapi import APIRouter, HTTPException, Request

from backend.modules.structural_engine import get_justification

from backend.api.schemas import HistoryMessage, HistoryResponse

router = APIRouter()


def _build_history_metrics(row: dict):
    from backend.api.schemas import MetricsInfo
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

        justification = r.get("structural_justification") or get_justification(r["content"])

        messages.append(HistoryMessage(
            id=r["id"],
            timestamp=r["timestamp"],
            speaker=r["speaker"],
            content=r["content"],
            thinking=None,
            context_sent=None,
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
