import logging
import re
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


def process_self_annotations(
    response_text: str,
    conversation_id: str,
    message_id: int,
    note_repo,
    message_repo,
) -> str:
    """
    Scan Symbia's response for self-authored <aaa-note>/<mark> tags without IDs,
    create DB note records, and replace tags with proper ID-bearing versions.
    Also truncate <scar_fold> content to 200 characters as a safeguard.
    """
    # --- Convert echoed <note_entanglement> tags back to <mark> ---
    # The LLM sometimes copies note_entanglement tags from its context into the response.
    # Convert them to proper <mark> tags so the frontend can render them as highlights.
    # Also create DB note records for any IDs that don't already exist.
    entanglement_ids_created = []

    def convert_entanglement(m):
        attrs = m.group(1) or ""
        text = m.group(2)
        nid_match = re.search(r'\bnote_id\s*=\s*["\']([^"\']+)["\']', attrs)
        if not nid_match:
            return text  # strip if no valid note_id

        nid = nid_match.group(1)
        comment_match = re.search(r'\bcomment\s*=\s*["\']([^"\']*)["\']', attrs)
        comment = comment_match.group(1) if comment_match else ""

        # Ensure a DB record exists for this note ID
        existing = note_repo.get_note(nid)
        if not existing:
            note_repo.create_self_note(
                id=nid,
                conversation_id=conversation_id,
                message_id=message_id,
                selected_text=text.strip(),
                comment=comment,
                visibility="agent",
            )
            entanglement_ids_created.append(nid)

        return f'<mark id="note-highlight-{nid}" data-note-id="{nid}">{text}</mark>'

    response_text = re.sub(
        r'<note_entanglement(\s+[^>]*?)?>([\s\S]*?)</note_entanglement>',
        convert_entanglement, response_text,
    )

    if entanglement_ids_created:
        logger.debug(
            "Entanglement echo: created %d note record(s) for message %d",
            len(entanglement_ids_created), message_id,
        )

    # --- Self-annotation processing ---
    # Matches <aaa-note ...>...</aaa-note> or <mark ...>...</mark>
    annotation_pattern = r'<(aaa-note|mark)(\s+[^>]+)?>([\s\S]*?)</\1>'

    annotations_found = []

    def replace_and_create(match):
        tag_name = match.group(1)
        attrs = match.group(2) or ""
        text = match.group(3)

        # Skip if it already has an id attribute (meaning it was already processed)
        if re.search(r'\bid\s*=\s*["\']', attrs):
            return match.group(0)

        # Extract comment attribute (supporting single/double quotes, spaces, newlines)
        comment_match = re.search(r'\bcomment\s*=\s*["\']([\s\S]*?)["\']', attrs)
        if not comment_match:
            return match.group(0)

        comment = comment_match.group(1)

        # Agent notes have 'agent' visibility to distinguish them from human notes in UI
        visibility = "agent"

        note_id = str(uuid.uuid4())
        annotations_found.append(note_id)

        note_repo.create_self_note(
            id=note_id,
            conversation_id=conversation_id,
            message_id=message_id,
            selected_text=text.strip(),
            comment=comment,
            visibility=visibility,
        )
        return f'<{tag_name} id="note-highlight-{note_id}" data-note-id="{note_id}">{text}</{tag_name}>'

    processed = re.sub(annotation_pattern, replace_and_create, response_text)

    if annotations_found:
        logger.debug(
            "Self-annotation: created %d note(s) for message %d",
            len(annotations_found), message_id,
        )
        # Update stored message content with ID-bearing tags
        message_repo.update_content(message_id, processed)

    # --- Scar-fold truncation safeguard ---
    def truncate_scar_fold(match):
        tag = match.group(1)
        content = match.group(2)
        if len(content) > 200:
            return f"<{tag}>{content[:200]}</{tag}>"
        return match.group(0)

    processed = re.sub(r'<(scar_fold|scar-fold)>([\s\S]*?)</\1>', truncate_scar_fold, processed)

    # If scar folds were truncated, update stored content
    if processed != response_text and not annotations_found:
        message_repo.update_content(message_id, processed)

    return processed


async def run_background_resonance_scan(
    background_engine,
    message_repo,
    conversation_id: str,
    message_id: int,
):
    try:
        # Get ancestor path to find parallel nodes
        path_msgs = message_repo.get_ancestor_path(message_id)
        ancestor_ids = [m.id for m in path_msgs]

        # Get the current message content/speaker
        current_msg = None
        for m in path_msgs:
            if m.id == message_id:
                current_msg = m
                break
        if not current_msg:
            # Fallback if not found in path
            msgs = message_repo.get_by_ids([message_id])
            if msgs:
                current_msg = msgs[0]
        
        if not current_msg or not current_msg.embedding:
            return

        # Find parallel messages with similarity > 0.82
        # (Exclude ancestor path to only find cross-branch resonances)
        candidates = message_repo.get_parallel_messages_by_similarity(
            conversation_id=conversation_id,
            message_id=message_id,
            ancestor_ids=ancestor_ids,
            threshold=0.82,
            limit=5,
        )

        for cand in candidates:
            # Skip checking if a link (proposed, active, or ignored) already exists
            if message_repo.link_exists(message_id, cand["message_id"]):
                logger.info(
                    "Resonance link already exists or was ignored between %d and %d, skipping comparison",
                    message_id, cand["message_id"]
                )
                continue

            # Call the background task engine to execute resonance finder LLM query
            payload = {
                "message_a": current_msg.content,
                "speaker_a": current_msg.speaker,
                "message_b": cand["content"],
                "speaker_b": cand["speaker"],
            }
            res = await background_engine.run("resonance_finder", payload)
            if res.get("has_resonance"):
                reason = res.get("reason", "")
                # Create proposed link
                message_repo.add_message_link(
                    source_id=message_id,
                    target_id=cand["message_id"],
                    link_type="resonance",
                    status="proposed",
                    justification=reason,
                )
                logger.info(
                    "Background resonance link proposed: %d -> %d (reason: %s)",
                    message_id, cand["message_id"], reason
                )
    except Exception:
        logger.exception("Error during background resonance scan")


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
        parent_message_id: Optional[int] = None,
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
                "parent_message_id": parent_message_id,
            }
            if attachments:
                initial_payload["attachments"] = attachments
            if max_tokens_override is not None:
                initial_payload["max_tokens"] = max_tokens_override
            else:
                llm_cfg = state.config.get("llm", {}).get("default_params", {})
                if "max_tokens" in llm_cfg:
                    initial_payload["max_tokens"] = llm_cfg["max_tokens"]

            result = await pipeline.run(initial_payload)

            response_text = result.payload.get("response", "")

            # Parse and strip proposed branches (<line_of_flight>)
            proposed_branches = []
            lof_pattern = r'<line_of_flight\s+title="([^"]+)">([\s\S]*?)</line_of_flight>'
            matches = re.findall(lof_pattern, response_text)
            for title, body in matches:
                proposed_branches.append({"title": title, "content": body.strip()})
            response_text = re.sub(lof_pattern, "", response_text).strip()

            # Parse and strip proposed resonance links (<resonance target="ID">Reason</resonance>)
            proposed_resonances = []
            res_pattern = r'<resonance\s+target=["\']([^"\']+)["\']\s*>([\s\S]*?)</resonance>'
            res_matches = re.findall(res_pattern, response_text)
            for target_id_str, justification in res_matches:
                try:
                    target_id = int(target_id_str)
                    proposed_resonances.append((target_id, justification.strip()))
                except ValueError:
                    logger.warning("Invalid resonance target ID: %s", target_id_str)
            response_text = re.sub(res_pattern, "", response_text).strip()
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
                parent_message_id=parent_message_id,
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
                parent_message_id=msg.id,
            )

            # Save proposed agential resonance links (Tier 1)
            for target_id, justification in proposed_resonances:
                try:
                    repo.add_message_link(
                        source_id=response_msg.id,
                        target_id=target_id,
                        link_type="resonance",
                        status="proposed",
                        justification=justification,
                    )
                except Exception as e:
                    logger.warning("Failed to save proposed agential resonance link: %s", e)

            # Self-annotation post-processing: scan for inline <aaa-note>/<mark> tags
            # without IDs, create DB records, and replace with ID-bearing versions.
            # Also truncate scar_fold content to 200 chars as safeguard.
            note_repo = getattr(state, "note_repo", None)
            if note_repo:
                try:
                    response_text = process_self_annotations(
                        response_text=response_text,
                        conversation_id=conversation_id,
                        message_id=response_msg.id,
                        note_repo=note_repo,
                        message_repo=repo,
                    )
                except Exception:
                    logger.exception("Failed to process self-annotations")

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

            if background_engine and background_tasks:
                background_tasks.add_task(
                    run_background_resonance_scan,
                    background_engine,
                    repo,
                    conversation_id,
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
                parent_message_id=response_msg.parent_message_id,
                proposed_branches=proposed_branches,
            )
        except ValueError:
            raise
        except Exception as e:
            logger.exception("Chat processing error")
            error_repo.log_error(module="api", error=e, context={"input": content})
            raise

    async def save_message(
        self,
        content: str,
        speaker: str,
        conversation_id: str,
        attachments: Optional[list[dict]] = None,
        include_structural_scoring: Optional[bool] = None,
        parent_message_id: Optional[int] = None,
    ) -> ChatResponse:
        state = self._state
        repo = state.message_repo
        conv_repo = getattr(state, "conversation_repo", None)
        agent_id = getattr(state, "agent_name", "symbia")

        is_new = False
        if conv_repo:
            if not conversation_id or not conv_repo.get(conversation_id):
                conversation_id = str(uuid.uuid4())
                conv_repo.create(conversation_id=conversation_id, agent_id=agent_id)
                is_new = True
            else:
                conv_repo.touch(conversation_id)

        # Generate embedding for user message
        embedding = b""
        embedding_model = "unknown"
        embedding_dim = 0
        embedder = getattr(state, "embedder", None)
        if embedder and embedder.service.is_loaded:
            try:
                emb = await embedder.service.encode_async(content)
                embedding = embedder.service.serialize(emb)
                embedding_model = embedder.service.model_name
                embedding_dim = embedder.service.dim
            except Exception:
                logger.warning("Failed to embed user message")

        # Score structural signature
        content_tokens = estimate_tokens(content)
        scorer = CompositeStructuralScorer(llm_provider=state.structural_provider)
        try:
            user_sig = await scorer.score_async(content, use_llm_scorer=include_structural_scoring)
            user_sig_blob = user_sig.tobytes()
        except Exception as e:
            logger.warning("Failed to score user message: %s", e)
            user_sig_blob = b""

        user_just = get_justification(content)

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
            parent_message_id=parent_message_id,
        )

        import numpy as np
        try:
            user_sig_list = user_sig.tolist() if 'user_sig' in locals() and user_sig is not None else None
        except Exception:
            user_sig_list = None

        return ChatResponse(
            id=msg.id,
            timestamp=msg.timestamp,
            conversation_id=conversation_id,
            speaker=msg.speaker,
            content=msg.content,
            content_tokens=msg.content_tokens,
            embedding_generated=bool(embedding),
            parent_message_id=msg.parent_message_id,
            user_message_id=msg.id,
            user_structural_signature=user_sig_list,
            user_structural_justification=user_just,
        )

    async def generate_response(
        self,
        conversation_id: str,
        user_message_id: int,
        max_tokens_override: Optional[int] = None,
        include_structural_scoring: Optional[bool] = None,
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

        # Retrieve the user message
        msg = repo.get_by_id(user_message_id)
        if not msg:
            raise ValueError(f"Message {user_message_id} not found")

        content = msg.content
        speaker = msg.speaker
        parent_message_id = msg.parent_message_id

        # Update conversation timestamp
        if conv_repo:
            conv_repo.touch(conversation_id)

        try:
            initial_payload: dict = {
                "content": content,
                "speaker": speaker,
                "conversation_id": conversation_id,
                "include_structural_scoring": include_structural_scoring,
                # Use parent_message_id of the user message so context_collector collects messages BEFORE this message,
                # then appends the user message as the current "content" payload.
                "parent_message_id": parent_message_id,
            }
            if max_tokens_override is not None:
                initial_payload["max_tokens"] = max_tokens_override
            else:
                llm_cfg = state.config.get("llm", {}).get("default_params", {})
                if "max_tokens" in llm_cfg:
                    initial_payload["max_tokens"] = llm_cfg["max_tokens"]

            result = await pipeline.run(initial_payload)

            response_text = result.payload.get("response", "")

            # Parse and strip proposed branches (<line_of_flight>)
            proposed_branches = []
            lof_pattern = r'<line_of_flight\s+title="([^"]+)">([\s\S]*?)</line_of_flight>'
            matches = re.findall(lof_pattern, response_text)
            for title, body in matches:
                proposed_branches.append({"title": title, "content": body.strip()})
            response_text = re.sub(lof_pattern, "", response_text).strip()

            # Parse and strip proposed resonance links (<resonance target="ID">Reason</resonance>)
            proposed_resonances = []
            res_pattern = r'<resonance\s+target=["\']([^"\']+)["\']\s*>([\s\S]*?)</resonance>'
            res_matches = re.findall(res_pattern, response_text)
            for target_id_str, justification in res_matches:
                try:
                    target_id = int(target_id_str)
                    proposed_resonances.append((target_id, justification.strip()))
                except ValueError:
                    logger.warning("Invalid resonance target ID: %s", target_id_str)
            response_text = re.sub(res_pattern, "", response_text).strip()
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

            scorer = CompositeStructuralScorer(llm_provider=state.structural_provider)
            try:
                assistant_sig = await scorer.score_async(response_text, use_llm_scorer=include_structural_scoring)
                assistant_sig_blob = assistant_sig.tobytes()
            except Exception as e:
                logger.warning("Failed to score assistant message: %s", e)
                assistant_sig_blob = b""

            assistant_just = get_justification(response_text)

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
                parent_message_id=msg.id,
            )

            # Save proposed agential resonance links (Tier 1)
            for target_id, justification in proposed_resonances:
                try:
                    repo.add_message_link(
                        source_id=response_msg.id,
                        target_id=target_id,
                        link_type="resonance",
                        status="proposed",
                        justification=justification,
                    )
                except Exception as e:
                    logger.warning("Failed to save proposed agential resonance link: %s", e)

            # Self-annotation post-processing: scan for inline <aaa-note>/<mark> tags
            # without IDs, create DB records, and replace with ID-bearing versions.
            # Also truncate scar_fold content to 200 chars as safeguard.
            note_repo = getattr(state, "note_repo", None)
            if note_repo:
                try:
                    response_text = process_self_annotations(
                        response_text=response_text,
                        conversation_id=conversation_id,
                        message_id=response_msg.id,
                        note_repo=note_repo,
                        message_repo=repo,
                    )
                except Exception:
                    logger.exception("Failed to process self-annotations")

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

            if background_engine and background_tasks:
                background_tasks.add_task(
                    run_background_resonance_scan,
                    background_engine,
                    repo,
                    conversation_id,
                    response_msg.id,
                )

            # Auto-generate title logic
            if conv_repo and background_engine:
                conv = conv_repo.get(conversation_id)
                if conv:
                    msg_count = repo.count_messages(conversation_id)
                    if not conv.title.strip():
                        if msg_count <= 2:
                            try:
                                title = await TitleService.generate(background_engine, content)
                                conv_repo.update_title(conversation_id, title)
                            except Exception:
                                logger.exception("Failed to generate conversation title")
                        elif msg_count >= 3:
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

            import numpy as np
            try:
                user_sig = np.frombuffer(msg.structural_signature, dtype="float32") if msg.structural_signature else None
                user_sig_list = user_sig.tolist() if user_sig is not None else None
            except Exception:
                user_sig_list = None

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
                attachments=None,
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
                parent_message_id=response_msg.parent_message_id,
                proposed_branches=proposed_branches,
            )
        except ValueError:
            raise
        except Exception as e:
            logger.exception("Chat generation error")
            error_repo.log_error(module="api", error=e, context={"input": content})
            raise

    @staticmethod
    def _build_response_attachments(attachments, result):
        from backend.api.helpers import _build_response_attachments
        return _build_response_attachments(attachments, result)
