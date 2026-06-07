import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from backend.api.helpers import _build_response_attachments, _parse_chat_request
from backend.api.schemas import AttachmentInfo, ChatResponse, ConversationInfo, MetricsInfo
from backend.modules.structural_engine import CompositeStructuralScorer, get_justification
from backend.utils.token_counter import estimate_tokens

logger = logging.getLogger(__name__)

router = APIRouter()


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


def _fire_and_forget_semantic_knot_compaction(app_state, conversation_id: str) -> None:
    import asyncio as _asyncio

    engine = getattr(app_state, "background_engine", None)
    message_repo = getattr(app_state, "message_repo", None)
    semantic_knot_repo = getattr(app_state, "semantic_knot_repo", None)
    embedder = getattr(app_state, "embedder", None)
    structural_provider = getattr(app_state, "structural_provider", None)

    if not engine or not message_repo or not semantic_knot_repo or not embedder:
        logger.warning("Missing dependencies for semantic knot compaction")
        return

    async def _do_compact():
        try:
            rows = message_repo.get_recent_with_metrics(limit=1000, conversation_id=conversation_id)
            if not rows:
                return

            rows.reverse()

            keep_raw = 8
            if len(rows) <= keep_raw:
                return

            older_rows = rows[:-keep_raw]

            existing_knots = semantic_knot_repo.get_by_conversation(conversation_id)
            last_compacted_msg_id = 0
            for knot in existing_knots:
                try:
                    data = json.loads(knot.concept_payload)
                    if "max_message_id" in data:
                        last_compacted_msg_id = max(last_compacted_msg_id, data["max_message_id"])
                except Exception:
                    pass

            messages_to_compact = [r for r in older_rows if r["id"] > last_compacted_msg_id]
            if len(messages_to_compact) < 4:
                return

            logger.info("Compacting %d messages for conversation %s", len(messages_to_compact), conversation_id)

            formatted_lines = []
            for r in messages_to_compact:
                speaker = r.get("speaker", "unknown")
                content = r.get("content", "")
                label = "Human" if speaker == "human" else "Agent"
                formatted_lines.append(f"{label}: {content}")

            text = "\n".join(formatted_lines)

            result = await engine.run("semantic_knot", {
                "text": text,
            })

            concept_text = result.get("content", "").strip()
            if not concept_text:
                logger.warning("Distillation returned empty content for semantic knot")
                return

            emb_res = await embedder.embed_text(concept_text)
            embedding_bytes = emb_res["embedding"].tobytes()
            embedding_model = emb_res["model"]

            scorer = CompositeStructuralScorer(llm_provider=structural_provider)
            sig_vec = await scorer.score_async(concept_text)
            sig_bytes = sig_vec.tobytes()

            token_count = estimate_tokens(concept_text)

            payload_data = {
                "text": concept_text,
                "max_message_id": max(r["id"] for r in messages_to_compact),
            }
            payload_str = json.dumps(payload_data)

            semantic_knot_repo.insert_knot(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                concept_payload=payload_str,
                embedding=embedding_bytes,
                embedding_model=embedding_model,
                token_count=token_count,
                weight=1.0,
                structural_signature=sig_bytes,
            )
            logger.info("Successfully compacted conversation log into a Semantic Knot for %s", conversation_id)

        except Exception:
            logger.exception("Background semantic knot compaction failed")

    try:
        loop = _asyncio.get_running_loop()
        loop.create_task(_do_compact())
    except RuntimeError:
        pass


def _fire_and_forget_consolidation(engine, message_repo, checkpoint_repo, conversation_id: str, msg_count: int) -> None:
    import asyncio as _asyncio

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
        loop = _asyncio.get_running_loop()
        loop.create_task(_do_consolidate())
    except RuntimeError:
        pass


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
        phase_shifts_json = json.dumps(phase_shifts)

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


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, background_tasks: BackgroundTasks):
    content, speaker, conversation_id, attachments, include_structural_scoring, max_tokens_override = await _parse_chat_request(request)

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
        if max_tokens_override is not None:
            initial_payload["max_tokens"] = max_tokens_override

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

        user_just = get_justification(content)
        assistant_just = get_justification(response_text)

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
            structural_justification=user_just,
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
            context_sent=result.payload.get("context_sent"),
            structural_signature=assistant_sig_blob,
            structural_justification=assistant_just,
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

        if metrics_repo and response_text.strip():
            try:
                embedder = getattr(state, "embedder", None)
                if embedder and embedder.service.is_loaded:
                    assistant_emb = await embedder.service.encode_async(response_text)
                    assistant_emb_blob = embedder.service.serialize(assistant_emb)
                    repo.update_embedding(
                        response_msg.id,
                        assistant_emb_blob,
                        embedder.service.model_name,
                        embedder.service.dim,
                    )
                    metrics_module = getattr(state, "metrics_module", None)
                    if metrics_module:
                        assistant_payload = {
                            "content": response_text,
                            "embedding": assistant_emb_blob,
                            "embedding_dim": embedder.service.dim,
                            "conversation_id": conversation_id,
                            "exclude_message_id": response_msg.id,
                        }
                        assistant_result = await metrics_module.process(assistant_payload)
                        assistant_metrics = assistant_result.get("metrics")
                        if assistant_metrics and assistant_metrics.get("pairwise_similarity") is not None:
                            _store_metrics(
                                metrics_repo=metrics_repo,
                                message_id=response_msg.id,
                                metrics=assistant_metrics,
                                recommendations=None,
                            )
            except Exception:
                logger.exception("Failed to compute assistant metrics")

        belief_metabolism = getattr(state, "belief_metabolism", None)
        if belief_metabolism:
            background_tasks.add_task(
                belief_metabolism.metabolize,
                conversation_id,
                msg.id,
                response_msg.id
            )

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
            conv_repo.mark_requires_consolidation(conversation_id, True)
            logger.info("Marked conversation %s as requiring consolidation", conversation_id)

        response_attachments = _build_response_attachments(attachments, result)

        diff_meta = result.payload.get("diffractive_meta")
        if diff_meta:
            request.app.state.latest_diffractive_meta = diff_meta

        should_compact = False
        if result.payload.get("trigger_consolidation"):
            should_compact = True
        elif diff_meta and diff_meta.get("state") == "STAGNANT":
            should_compact = True

        if should_compact:
            _fire_and_forget_semantic_knot_compaction(state, conversation_id)

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
            truncated=result.payload.get("truncated"),
            finish_reason=result.payload.get("finish_reason"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Chat endpoint error")
        error_repo.log_error(module="api", error=e, context={"input": content})
        raise HTTPException(status_code=500, detail=str(e))


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


def _build_recommendations(recs: dict | None):
    from backend.api.schemas import HomeostaticRecommendations
    if not recs:
        return None
    return HomeostaticRecommendations(
        temperature=recs.get("temperature"),
        presence_penalty=recs.get("presence_penalty"),
        frequency_penalty=recs.get("frequency_penalty"),
        state=recs.get("state", "healthy"),
        triggered_flags=recs.get("triggered_flags", []),
    )
