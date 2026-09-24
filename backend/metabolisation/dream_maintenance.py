"""Idle-time dream daemon maintenance jobs."""

import logging

from backend.metabolisation.dream_collaborator import DreamDaemonCollaborator, DreamResult
from backend.utils.vector import cosine_similarity

logger = logging.getLogger(__name__)


class DreamMaintenanceMixin(DreamDaemonCollaborator):
    async def backfill_structure_on_idle(self, max_files: int = 5) -> DreamResult | None:
        """Backfill heading-paths onto pre-ADR-062 sediment during idle.

        Scans ready files; for those whose chunks lack a heading_path, runs the
        structure_extraction background action (DB-only markers or re-extract
        from the retained original). No LLM, no re-embedding. Emits a trace
        notification per file that gains structure. See ADR-062.
        """
        if not self.perception_repo or not self.background_engine:
            return None

        import json as _json

        try:
            files = self.perception_repo.get_all_files_across_conversations()
        except Exception as e:
            logger.debug("Structure backfill: cannot list files: %s", e)
            return None

        processed = 0
        for f in files:
            if processed >= max_files:
                break
            conversation_id = f.get("conversation_id")
            file_name = f.get("file_name")
            if not conversation_id or not file_name:
                continue

            try:
                chunks = self.perception_repo.get_by_file(conversation_id, file_name)
            except Exception:
                continue
            if not chunks:
                continue

            already = False
            for c in chunks:
                if c.opacity_meta:
                    try:
                        _m = _json.loads(c.opacity_meta)
                        if _m.get("structure_extracted") or _m.get("heading_path"):
                            already = True
                            break
                    except Exception:
                        pass
            if already:
                continue

            try:
                result = await self.background_engine.run(
                    "structure_extraction",
                    {
                        "perception_repo": self.perception_repo,
                        "conversation_id": conversation_id,
                        "file_name": file_name,
                    },
                )
            except Exception as e:
                logger.debug("Structure extraction failed for %s: %s", file_name, e)
                continue

            if result.get("status") == "completed" and result.get("chunks_updated", 0) > 0:
                processed += 1
                if self.notification_repo:
                    try:
                        self.notification_repo.create(
                            type="trace",
                            snippet=(
                                f"Structure extracted: '{file_name}' — "
                                f"{result['chunks_updated']} heading paths recovered "
                                f"({result.get('source')})."
                            ),
                            conversation_id=conversation_id,
                            source=f"perception:{file_name}",
                            source_type="conversation",
                            source_id=conversation_id,
                        )
                    except Exception as ne:
                        logger.debug("Structure backfill notification failed: %s", ne)

        if processed:
            logger.info("Structure backfill: %d file(s) gained heading-paths", processed)
            return {"files_updated": processed}
        return None

    async def compact_memory(self) -> DreamResult | None:
        """Zettelkasten-style memory compaction: merge highly similar semantic knots."""
        if not self.semantic_knot_repo:
            return None
        try:
            records = self.semantic_knot_repo.get_embeddings_and_signatures_except("", limit=1000)
            if len(records) < 2:
                return None

            target_pair = None
            for i in range(len(records)):
                knot_a_id, emb_a, sig_a, payload_a = records[i]
                for j in range(i + 1, len(records)):
                    knot_b_id, emb_b, sig_b, payload_b = records[j]

                    sem_sim = cosine_similarity(emb_a, emb_b)
                    struct_sim = 1.0
                    if sig_a is not None and sig_b is not None and len(sig_a) == 16 and len(sig_b) == 16:
                        struct_sim = cosine_similarity(sig_a, sig_b)

                    if sem_sim > 0.92 and struct_sim > 0.80:
                        target_pair = (records[i], records[j])
                        break
                if target_pair:
                    break

            if not target_pair:
                logger.debug("No highly similar semantic knots found for compaction.")
                return None

            knot_a, knot_b = target_pair
            knot_a_id, emb_a, sig_a, payload_a = knot_a
            knot_b_id, emb_b, sig_b, payload_b = knot_b

            logger.info("Compacting semantic knots: %s and %s", knot_a_id, knot_b_id)

            full_knots = self.semantic_knot_repo.get_by_ids([knot_a_id, knot_b_id])
            if len(full_knots) < 2:
                return None

            k_a = full_knots[0] if full_knots[0].id == knot_a_id else full_knots[1]
            k_b = full_knots[1] if full_knots[1].id == knot_b_id else full_knots[0]

            merged_payload = f"{k_a.concept_payload}\n\n[Consolidated Concept from {k_b.id}]:\n{k_b.concept_payload}"

            try:
                summary_prompt = (
                    "Below are two redundant cybernetic concept notes from our memory. "
                    "Synthesize them into a single, cohesive, posthuman concept note. "
                    "Maintain their theoretical essence but make it concise:\n\n"
                    f"Note 1: {k_a.concept_payload}\n\n"
                    f"Note 2: {k_b.concept_payload}"
                )
                payload = {
                    "content": summary_prompt,
                    "speaker": "human",
                    "conversation_id": k_a.conversation_id,
                    "is_dream_cycle": True,
                    "dream_action": "compaction",
                }
                result = await self.pipeline.run(payload)
                resp = result.payload.get("response", "").strip()
                if resp:
                    merged_payload = resp
            except Exception as llm_err:
                logger.warning("LLM compaction summary failed, falling back to concatenation: %s", llm_err)

            new_weight = k_a.weight + k_b.weight

            self.semantic_knot_repo.update_knot(
                knot_id=k_a.id,
                concept_payload=merged_payload,
                embedding=k_a.embedding,
                weight=new_weight,
                structural_signature=k_a.structural_signature,
            )

            self.semantic_knot_repo.delete_knot(k_b.id)

            logger.info("Successfully compacted knot %s into %s (new weight: %.2f)", k_b.id, k_a.id, new_weight)
            return {
                "action": "compaction",
                "retained_id": k_a.id,
                "deleted_id": k_b.id,
                "new_weight": new_weight,
                "payload": merged_payload[:200] + "...",
            }
        except Exception as e:
            logger.exception("Error during memory compaction: %s", e)
            return None
