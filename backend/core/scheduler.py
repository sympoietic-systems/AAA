import os
import logging
import asyncio
import numpy as np
from typing import Callable, Any, List, Dict

logger = logging.getLogger(__name__)

class BackgroundStartupScheduler:
    def __init__(self, app_state: Any, process_file_func: Callable):
        self.app_state = app_state
        self.process_file_func = process_file_func
        self.perception_repo = app_state.perception_repo
        self.message_repo = app_state.message_repo
        self.belief_metabolism = getattr(app_state, "belief_metabolism", None)
        self.config = getattr(app_state, "config", {})
        
        # State tracking for UI visibility
        self._status = "pending"
        self._indexing_tasks_found = 0
        self._indexing_tasks_completed = 0
        self._indexing_tasks_failed = 0
        self._active_indexing_jobs: List[str] = []
        self._belief_turns_found = 0
        self._belief_turns_completed = 0
        self._belief_turns_failed = 0
        self._error_details = None
        # Backfill state
        self._signatures_backfilled = 0
        self._metrics_backfilled = 0

    def start(self) -> None:
        asyncio.create_task(self._run_scheduler())

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": self._status,
            "indexing_tasks_found": self._indexing_tasks_found,
            "indexing_tasks_completed": self._indexing_tasks_completed,
            "indexing_tasks_failed": self._indexing_tasks_failed,
            "active_indexing_jobs": list(self._active_indexing_jobs),
            "belief_turns_found": self._belief_turns_found,
            "belief_turns_completed": self._belief_turns_completed,
            "belief_turns_failed": self._belief_turns_failed,
            "signatures_backfilled": self._signatures_backfilled,
            "metrics_backfilled": self._metrics_backfilled,
            "error_details": self._error_details,
        }

    async def _run_scheduler(self) -> None:
        logger.info("Initializing Background Startup Scheduler...")
        self._status = "running"
        await asyncio.sleep(2)
        
        # 1. Resume unfinished file indexing tasks
        try:
            await self._resume_indexing_tasks()
        except Exception as e:
            logger.exception("Failed during background file indexing resumption: %s", e)
            self._error_details = f"File indexing resumption failure: {str(e)}"

        # 2. Backfill missing structural signatures
        try:
            await self._backfill_structural_signatures()
        except Exception as e:
            logger.exception("Failed during structural signature backfill: %s", e)
            if self._error_details:
                self._error_details += f" | Signature backfill failure: {str(e)}"
            else:
                self._error_details = f"Signature backfill failure: {str(e)}"

        # 3. Backfill missing conversation metrics
        try:
            await self._backfill_conversation_metrics()
        except Exception as e:
            logger.exception("Failed during conversation metrics backfill: %s", e)
            if self._error_details:
                self._error_details += f" | Metrics backfill failure: {str(e)}"
            else:
                self._error_details = f"Metrics backfill failure: {str(e)}"

        # 4. Run catch-up belief metabolism for missed chat turns
        try:
            await self._catch_up_belief_metabolism()
        except Exception as e:
            logger.exception("Failed during background belief metabolism catch-up: %s", e)
            if self._error_details:
                self._error_details += f" | Belief metabolism catch-up failure: {str(e)}"
            else:
                self._error_details = f"Belief metabolism catch-up failure: {str(e)}"
        
        self._status = "completed"
        logger.info("Background Startup Scheduler caught up successfully.")

        # 5. Periodic re-check for new gaps every 60s
        await self._periodic_sweep()

    async def _periodic_sweep(self) -> None:
        interval = self.config.get("background", {}).get("sweep_interval_seconds", 60)
        while True:
            await asyncio.sleep(interval)
            try:
                sig_count = await self._backfill_structural_signatures()
                if sig_count > 0:
                    logger.info("Periodic sweep: backfilled %d signatures", sig_count)
            except Exception as e:
                logger.error("Periodic signature sweep error: %s", e)
            try:
                met_count = await self._backfill_conversation_metrics()
                if met_count > 0:
                    logger.info("Periodic sweep: backfilled %d metrics", met_count)
            except Exception as e:
                logger.error("Periodic metrics sweep error: %s", e)
            try:
                await self._catch_up_belief_metabolism()
            except Exception as e:
                logger.error("Periodic belief metabolism catch-up error: %s", e)

    async def _resume_indexing_tasks(self) -> None:
        unfinished_files = self.perception_repo.get_unfinished_files()
        if not unfinished_files:
            return

        self._indexing_tasks_found = len(unfinished_files)
        logger.info("Found %d unfinished/errored indexing tasks. Initializing resumption...", len(unfinished_files))
        
        max_jobs = self.config.get("perception", {}).get("max_concurrent_indexing_jobs", 2)
        sem = asyncio.Semaphore(max_jobs)

        async def resume_file(f: dict) -> None:
            async with sem:
                convo_id = f["conversation_id"]
                file_name = f["file_name"]
                file_type = f["file_type"]
                cache_path = os.path.join("backend", "data", "uploads", convo_id, file_name)
                
                self._active_indexing_jobs.append(file_name)
                try:
                    if not os.path.exists(cache_path):
                        logger.warning(
                            "Upload cache missing for file %s in conversation %s. Setting status to error.",
                            file_name, convo_id
                        )
                        self.perception_repo.update_file(
                            conversation_id=convo_id,
                            file_name=file_name,
                            status="error",
                            summary="Source file cache missing on restart. Please delete and re-upload."
                        )
                        self._indexing_tasks_failed += 1
                        return

                    logger.info("Resuming indexing for file: %s (conversation: %s)", file_name, convo_id)
                    try:
                        await self.process_file_func(
                            self.app_state,
                            convo_id,
                            file_name,
                            file_type,
                            None
                        )
                        logger.info("Successfully finished resumed indexing for: %s", file_name)
                        self._indexing_tasks_completed += 1
                    except Exception as e:
                        logger.error("Failed to resume indexing for %s: %s", file_name, e)
                        self.perception_repo.update_file(
                            conversation_id=convo_id,
                            file_name=file_name,
                            status="error",
                            summary=f"Failed during background resumption: {str(e)}"
                        )
                        self._indexing_tasks_failed += 1
                finally:
                    if file_name in self._active_indexing_jobs:
                        self._active_indexing_jobs.remove(file_name)

        tasks = [resume_file(f) for f in unfinished_files]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _backfill_structural_signatures(self) -> int:
        messages = self.message_repo.get_messages_without_signatures()
        if not messages:
            return 0

        from backend.modules.structural_engine import CompositeStructuralScorer
        scorer = CompositeStructuralScorer(llm_provider=None)
        count = 0
        logger.info("Backfilling %d messages with missing structural signatures...", len(messages))

        for msg in messages:
            content = msg.content or ""
            if not content.strip():
                continue
            try:
                sig = await scorer.score_async(content, use_llm_scorer=False)
                self.message_repo.update_signature(msg.id, sig.tobytes())
                count += 1
            except Exception as e:
                logger.warning("Failed to backfill signature for message %d: %s", msg.id, e)

        self._signatures_backfilled += count
        logger.info("Structural signature backfill complete: %d messages updated", count)
        return count

    async def _backfill_conversation_metrics(self) -> int:
        messages_without_metrics = self.message_repo.get_messages_without_metrics()
        if not messages_without_metrics:
            return 0

        # Group by conversation, ordered chronologically
        by_convo: Dict[str, list] = {}
        for msg in messages_without_metrics:
            cid = msg.conversation_id or ""
            by_convo.setdefault(cid, []).append(msg)

        metrics_module = getattr(self.app_state, "metrics_module", None)
        metrics_repo = getattr(self.app_state, "metrics_repo", None)
        embedder = getattr(self.app_state, "embedder", None)
        if not metrics_module or not metrics_repo:
            logger.warning("Metrics module or repo not available, skipping metrics backfill")
            return 0

        count = 0
        logger.info("Backfilling conversation metrics for %d messages across %d conversations...",
                     len(messages_without_metrics), len(by_convo))

        for cid, msgs in by_convo.items():
            metrics_module._prior_metrics = {}
            for msg in msgs:
                content = msg.content or ""
                if not content.strip():
                    continue
                try:
                    embedding_blob = getattr(msg, 'embedding', None) or b""
                    embedding_dim = getattr(msg, 'embedding_dim', 0) or 384

                    # For assistant messages, embed the response text to get a proper embedding
                    if msg.speaker == "apparatus" and embedder and embedder.service.is_loaded and content.strip():
                        try:
                            assistant_emb = await embedder.service.encode_async(content)
                            embedding_blob = embedder.service.serialize(assistant_emb)
                            embedding_dim = embedder.service.dim
                            self.message_repo.update_embedding(
                                msg.id, embedding_blob,
                                embedder.service.model_name, embedder.service.dim,
                            )
                        except Exception as e:
                            logger.warning("Failed to embed assistant msg %d: %s", msg.id, e)

                    if not embedding_blob:
                        continue

                    payload = {
                        "content": content,
                        "embedding": embedding_blob,
                        "embedding_dim": embedding_dim,
                        "conversation_id": cid,
                        "exclude_message_id": msg.id,
                    }
                    result = await metrics_module.process(payload)
                    metrics = result.get("metrics")
                    if metrics and metrics.get("pairwise_similarity") is not None:
                        _store_metrics_backfill(metrics_repo, msg.id, metrics)
                        count += 1
                except Exception as e:
                    logger.warning("Failed to backfill metrics for message %d in convo %s: %s",
                                   msg.id, cid, e)

        self._metrics_backfilled += count
        logger.info("Conversation metrics backfill complete: %d messages updated", count)
        return count

    async def _catch_up_belief_metabolism(self) -> None:
        if not self.belief_metabolism:
            logger.warning("Belief metabolism engine is not available. Skipping catch-up.")
            return

        missed_turns = self.perception_repo.get_missed_belief_turns()
        if not missed_turns:
            return

        self._belief_turns_found = len(missed_turns)
        logger.info("Found %d missed chat turns for belief metabolism catch-up. Processing...", len(missed_turns))
        
        for turn in missed_turns:
            user_id = int(turn["user_id"])
            convo_id = turn["conversation_id"]
            assistant_id = int(turn["assistant_id"])
            
            logger.info("Catching up belief metabolism for turn user_msg_id=%d in conversation=%s", user_id, convo_id)
            try:
                await self.belief_metabolism.metabolize(
                    conversation_id=convo_id,
                    user_message_id=user_id,
                    assistant_message_id=assistant_id
                )
                self._belief_turns_completed += 1
            except Exception as e:
                logger.error("Failed catch-up metabolism for turn %d: %s", user_id, e)
                self._belief_turns_failed += 1


def _store_metrics_backfill(metrics_repo, message_id: int, metrics: dict) -> None:
    s_t = metrics.get("pairwise_similarity")
    novelty = metrics.get("conceptual_novelty")
    if s_t is None or novelty is None:
        return

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
    )
