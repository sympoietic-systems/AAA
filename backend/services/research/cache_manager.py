import contextlib
import json
import logging

logger = logging.getLogger("aaa.research_orchestrator")


class CacheManager:
    _cached_inputs_ensured: bool = False

    def __init__(self, task_repo):
        self._task_repo = task_repo

    def load_cache(self, task_id: str) -> dict:
        try:
            task = self._task_repo.get(task_id)
            raw = (task or {}).get("cached_inputs")
            if not raw:
                return {}
            return json.loads(raw)
        except Exception:
            return {}

    def ensure_cached_inputs_column(self) -> None:
        if CacheManager._cached_inputs_ensured:
            return
        with contextlib.suppress(Exception):
            self._task_repo.ensure_column("ALTER TABLE research_tasks ADD COLUMN cached_inputs TEXT")
        CacheManager._cached_inputs_ensured = True

    def save_cache(self, task_id: str, cache: dict) -> None:
        try:
            self.ensure_cached_inputs_column()
            self._task_repo.update(task_id, cached_inputs=json.dumps(cache, ensure_ascii=False))
        except Exception:
            logger.warning("Failed to save cached_inputs for %s", task_id[:8], exc_info=True)

    def get_cached_phase(self, task_id: str, phase: str) -> dict | None:
        cache = self.load_cache(task_id)
        return cache.get(phase)

    def reinitialize(self, task_id: str) -> None:
        try:
            self.ensure_cached_inputs_column()
            self._task_repo.update(task_id, cached_inputs=None)
        except Exception:
            logger.warning("Failed to reinitialize cached_inputs for %s", task_id[:8], exc_info=True)
