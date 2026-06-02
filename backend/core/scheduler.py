import os
import logging
import asyncio
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
            "error_details": self._error_details,
        }

    async def _run_scheduler(self) -> None:
        logger.info("Initializing Background Startup Scheduler...")
        self._status = "running"
        # Wait a few seconds for the server/event loop to settle
        await asyncio.sleep(2)
        
        # 1. Resume unfinished file indexing tasks
        try:
            await self._resume_indexing_tasks()
        except Exception as e:
            logger.exception("Failed during background file indexing resumption: %s", e)
            self._error_details = f"File indexing resumption failure: {str(e)}"

        # 2. Run catch-up belief metabolism for missed chat turns
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

    async def _resume_indexing_tasks(self) -> None:
        unfinished_files = self.perception_repo.get_unfinished_files()
        if not unfinished_files:
            return

        self._indexing_tasks_found = len(unfinished_files)
        logger.info("Found %d unfinished/errored indexing tasks. Initializing resumption...", len(unfinished_files))
        
        # Bound concurrency of indexing jobs
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
                        # Call the process function passed from routes (file_content is None, so it loads from cache)
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
