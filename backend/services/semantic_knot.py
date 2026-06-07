import asyncio
import json
import logging
import uuid
from typing import Optional

from backend.modules.structural_engine import CompositeStructuralScorer
from backend.utils.token_counter import estimate_tokens

logger = logging.getLogger(__name__)


class SemanticKnotService:
    @staticmethod
    def fire_and_forget(app_state, conversation_id: str) -> None:
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

                result = await engine.run("semantic_knot", {"text": text})
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
            loop = asyncio.get_running_loop()
            loop.create_task(_do_compact())
        except RuntimeError:
            pass
