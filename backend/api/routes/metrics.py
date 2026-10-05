import asyncio

from fastapi import APIRouter, Request

from backend.api.schemas import (
    DiffractiveInfo,
    DiffractiveSourceInfo,
    HomeostaticRecommendations,
    MetricsInfo,
    MetricsResponse,
)
from backend.services.metrics import MetricsService

router = APIRouter()


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    request: Request,
    window: int = 20,
    limit: int = 30,
    conversation_id: str | None = None,
):
    state = request.app.state
    metrics_repo = getattr(state, "metrics_repo", None)
    if not metrics_repo:
        return MetricsResponse(window_size=0, aggregates={"count": 0})

    fetch_limit = max(1, min(limit, 100))
    conv_id = conversation_id if conversation_id and conversation_id.strip() else None

    def _fetch():
        aggs = metrics_repo.get_aggregates(limit=max(1, min(window, 100)), conversation_id=conv_id)
        # Prefer the most recent complete metric record (with boringness/vitality calculated)
        lat = metrics_repo.get_latest(require_complete=True, conversation_id=conv_id) or metrics_repo.get_latest(
            require_complete=False, conversation_id=conv_id
        )
        # Fetch recent rounds for time-series sparkline/progression visualization
        recents = metrics_repo.get_recent(limit=fetch_limit, conversation_id=conv_id)
        return aggs, lat, recents

    aggregates, latest, recent_records = await asyncio.to_thread(_fetch)

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
            phase_shifts=await asyncio.to_thread(MetricsService.parse_phase_shifts, latest.phase_shifts),
            collapse_pressure=latest.collapse_pressure if latest.collapse_pressure is not None else latest.boringness,
            phase_transition_magnitude=latest.phase_transition_magnitude,
            cpi=latest.cpi,
            teachback_ratio=latest.teachback_ratio,
            actionability=latest.actionability,
        )
        temp_rec = None
        pres_rec = None
        freq_rec = None
        if latest.temperature_rec is not None:
            temp_rec = {
                "value": latest.temperature_rec,
                "base": 0.7,
                "delta": round(latest.temperature_rec - 0.7, 3),
                "clamped": False,
            }
        if latest.presence_penalty_rec is not None:
            pres_rec = {
                "value": latest.presence_penalty_rec,
                "base": 0.0,
                "delta": round(latest.presence_penalty_rec, 3),
                "clamped": False,
            }
        if latest.frequency_penalty_rec is not None:
            freq_rec = {
                "value": latest.frequency_penalty_rec,
                "base": 0.0,
                "delta": round(latest.frequency_penalty_rec, 3),
                "clamped": False,
            }
        recommendations = HomeostaticRecommendations(
            temperature=temp_rec,
            presence_penalty=pres_rec,
            frequency_penalty=freq_rec,
            state=latest.homeostatic_state or "healthy",
        )

    # If live homeostatic recommendations are cached in app state, merge them to surface prompt interventions
    live_recs = getattr(state, "latest_homeostatic_recommendations", None)
    if live_recs:
        live_model = MetricsService.build_recommendations(live_recs)
        if live_model:
            if recommendations is None:
                recommendations = live_model
            else:
                # Merge intervention and directive details
                if live_model.intervention:
                    recommendations.intervention = live_model.intervention
                if live_model.somatic_reflection_prompt:
                    recommendations.somatic_reflection_prompt = live_model.somatic_reflection_prompt
                if live_model.triggered_flags:
                    recommendations.triggered_flags = list(
                        set(recommendations.triggered_flags + live_model.triggered_flags)
                    )
                if live_model.consecutive_stagnant_turns:
                    recommendations.consecutive_stagnant_turns = live_model.consecutive_stagnant_turns
                if live_model.state:
                    recommendations.state = live_model.state

    raw_diff = getattr(state, "latest_diffractive_meta", None)
    if not raw_diff:
        raw_diff = {
            "state": "FLOWING",
            "previous_state": "FLOWING",
            "p_diffract": 0.0,
            "stagnation_index": 0.0,
            "r_context": 0.20,
            "dynamic_max": 0,
            "cohesion_timer": 0,
            "similarity_range_memory": [0.45, 0.85],
            "similarity_range_files": [0.35, 0.75],
            "candidates_searched": 0,
            "items_injected": 0,
            "tokens_used": 0,
            "token_budget": 0,
            "duration_ms": 0.0,
            "sources": [],
        }

    diff_sources = [DiffractiveSourceInfo(**s) for s in raw_diff.get("sources", [])]
    diff_info = DiffractiveInfo(
        state=raw_diff.get("state", "FLOWING"),
        previous_state=raw_diff.get("previous_state", "FLOWING"),
        p_diffract=raw_diff.get("p_diffract", 0.0),
        activation_reason=raw_diff.get("activation_reason", ""),
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

    history_items: list[MetricsInfo] = []
    for r in recent_records:
        history_items.append(
            MetricsInfo(
                pairwise_similarity=r.s_t,
                conceptual_novelty=r.novelty,
                rolling_entropy=r.rolling_entropy,
                coupling_coherence=r.coupling,
                agent_self_divergence=r.agent_divergence,
                reverse_perturbation=r.reverse_perturbation,
                surprise_index=r.surprise_index,
                mutual_perturbation=r.mutual_perturbation,
                homeostatic_deficit=r.deficit,
                conversation_vitality=r.vitality,
                boringness=r.boringness,
                conceptual_velocity=r.conceptual_velocity,
                divergence_resolution_ratio=r.divergence_resolution_ratio,
                paskian_health=r.paskian_health,
                collapse_pressure=r.collapse_pressure if r.collapse_pressure is not None else r.boringness,
                phase_transition_magnitude=r.phase_transition_magnitude,
                cpi=r.cpi,
                teachback_ratio=r.teachback_ratio,
                actionability=r.actionability,
            )
        )

    return MetricsResponse(
        window_size=aggregates.get("count", 0),
        aggregates=aggregates,
        latest=latest_info,
        recommendations=recommendations,
        diffractive=diff_info,
        history=history_items,
    )
