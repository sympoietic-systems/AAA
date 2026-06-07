import logging
import uuid
from typing import Optional

from fastapi import BackgroundTasks

from backend.api.schemas import ChatResponse
from backend.modules.structural_engine import CompositeStructuralScorer, get_justification
from backend.services.consolidation import ConsolidationService
from backend.services.metrics import MetricsService
from backend.services.semantic_knot import SemanticKnotService
from backend.services.title import TitleService
from backend.utils.token_counter import estimate_tokens

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, state):
        self._state = state

    async def process_chat(
        self,
        content: str,
        speaker: str,
        conversation_id: str,
        attachments: Optional[list[dict]] = None,
        include_structural_scoring: Optional[bool] = None,
        max_tokens_override: Optional[int] = None,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> ChatResponse:
        state = self._state
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
                raise ValueError("Pipeline processing failed")

            content_tokens = estimate_tokens(content)

            scorer = CompositeStructuralScorer(llm_provider=state.structural_provider)
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
                    MetricsService.store(
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
                                MetricsService.store(
                                    metrics_repo=metrics_repo,
                                    message_id=response_msg.id,
                                    metrics=assistant_metrics,
                                    recommendations=None,
                                )
                except Exception:
                    logger.exception("Failed to compute assistant metrics")

            belief_metabolism = getattr(state, "belief_metabolism", None)
            if belief_metabolism and background_tasks:
                background_tasks.add_task(
                    belief_metabolism.metabolize,
                    conversation_id,
                    msg.id,
                    response_msg.id,
                )

            if is_new and conv_repo and background_engine:
                try:
                    title = await TitleService.generate(background_engine, content)
                    conv_repo.update_title(conversation_id, title)
                except Exception:
                    logger.exception("Failed to generate conversation title")

            if not is_new and conv_repo and background_engine:
                conv = conv_repo.get(conversation_id)
                if conv and not conv.title.strip():
                    msg_count = repo.count_messages(conversation_id)
                    if msg_count >= 3:
                        try:
                            title = await TitleService.generate_from_conversation(
                                background_engine, repo, conversation_id
                            )
                            conv_repo.update_title(conversation_id, title)
                        except Exception:
                            logger.exception("Failed to auto-generate conversation title")

            if result.payload.get("trigger_consolidation") and background_engine and conv_repo:
                conv_repo.mark_requires_consolidation(conversation_id, True)
                logger.info("Marked conversation %s as requiring consolidation", conversation_id)

            diff_meta = result.payload.get("diffractive_meta")
            if diff_meta:
                state.latest_diffractive_meta = diff_meta

            should_compact = False
            if result.payload.get("trigger_consolidation"):
                should_compact = True
            elif diff_meta and diff_meta.get("state") == "STAGNANT":
                should_compact = True

            if should_compact:
                SemanticKnotService.fire_and_forget(state, conversation_id)

            justification = get_justification(response_text)
            user_justification = get_justification(content)
            user_sig_list = user_sig.tolist() if 'user_sig' in locals() and user_sig is not None else None

            loaded_skills = result.payload.get("loaded_skills", [])
            active_skill_names = [s.get("name", "") for s in loaded_skills if s.get("name")]

            attractor_window = result.payload.get("attractor_window", [])
            active_belief_labels = [item.get("label", "") for item in attractor_window if item.get("label")]

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
                metrics=MetricsService.build_info(payload_metrics),
                homeostatic_recommendations=MetricsService.build_recommendations(recommendations),
                attachments=self._build_response_attachments(attachments, result),
                context_sent=result.payload.get("context_sent"),
                model_used=response_msg.model_used,
                provider_used=response_msg.provider_used,
                structural_justification=justification,
                user_message_id=msg.id,
                user_structural_signature=user_sig_list,
                user_structural_justification=user_justification,
                truncated=result.payload.get("truncated"),
                finish_reason=result.payload.get("finish_reason"),
                active_skills=active_skill_names,
                active_beliefs=active_belief_labels,
            )
        except ValueError:
            raise
        except Exception as e:
            logger.exception("Chat processing error")
            error_repo.log_error(module="api", error=e, context={"input": content})
            raise

    @staticmethod
    def _build_response_attachments(attachments, result):
        from backend.api.helpers import _build_response_attachments
        return _build_response_attachments(attachments, result)
