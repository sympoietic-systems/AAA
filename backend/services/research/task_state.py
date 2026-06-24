import json
import logging
from typing import Optional

from backend.utils.research_logger import log_research_meta

logger = logging.getLogger("aaa.research_orchestrator")

_ORCH_STATE_KEYS = {
    "phase", "objective", "max_depth", "budget", "plan_id", "plan",
    "all_findings", "sources_analyzed", "stagnation_counter",
    "step_number", "last_reflection", "current_depth", "query_index",
    "search_results_cache", "digest_results_cache",
    "digest_signals",
    "should_stop", "stop_reason",
}


def make_initial_state(task: dict) -> dict:
    return {
        "phase": "planning",
        "objective": task["objective"],
        "max_depth": task["max_depth"],
        "budget": task["budget_limit_usd"],
        "plan_id": None,
        "plan": None,
        "all_findings": [],
        "sources_analyzed": 0,
        "stagnation_counter": 0,
        "step_number": 0,
        "last_reflection": {},
        "current_depth": 0,
        "query_index": 0,
        "search_results_cache": [],
        "parsed_sources_cache": [],
        "digest_results_cache": [],
        "should_stop": False,
        "stop_reason": "",
    }


class TaskStateManager:
    def __init__(self, task_repo, plan_repo=None, step_repo=None, meta_log_repo=None):
        self._task_repo = task_repo
        self._plan_repo = plan_repo
        self._step_repo = step_repo
        self._meta_log_repo = meta_log_repo
        self._states: dict[str, dict] = {}
        self._locks: dict[str, object] = {}

    def init_task(self, task_id: str) -> dict:
        task = self._task_repo.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        state = make_initial_state(task)
        self._states[task_id] = state
        log_research_meta(
            self._meta_log_repo, task_id, "orchestrator_step_init",
            {"objective": state["objective"], "max_depth": state["max_depth"],
             "budget": state["budget"], "mode": "step_by_step"},
        )
        return state

    def resume_task(self, task_id: str) -> Optional[dict]:
        task = self._task_repo.get(task_id)
        if not task:
            return None
        loaded = self._load_state(task_id)
        if loaded:
            loaded["objective"] = task["objective"]
            loaded["max_depth"] = task["max_depth"]
            loaded["budget"] = task["budget_limit_usd"]
            self._states[task_id] = loaded
            logger.info("Resumed task %s from orchestrator_state at phase '%s' (step %d)",
                         task_id[:8], loaded.get("phase"), loaded.get("step_number", 0))
            return loaded
        steps = self._step_repo.get_by_task(task_id) if self._step_repo else []
        completed = [s for s in steps if s["status"] == "completed"]
        last_type = completed[-1]["step_type"] if completed else None
        step_number = len(completed)
        plan = None
        plan_id = None
        if self._plan_repo:
            plan_row = self._plan_repo.get_by_task(task_id)
            if plan_row:
                plan_id = plan_row["id"]
                try:
                    plan = json.loads(plan_row["plan_json"])
                except Exception:
                    plan = {}
        phase_after: dict[str, str] = {
            "plan": "searching", "search": "parsing",
            "parallel_parse": "digesting", "digest": "reflecting",
            "reflect": "evaluating", "evaluate": "synthesizing",
            "synthesize": "complete",
        }
        phase = phase_after.get(last_type, "planning") if last_type else "planning"
        state = {
            "phase": phase, "objective": task["objective"],
            "max_depth": task["max_depth"], "budget": task["budget_limit_usd"],
            "plan_id": plan_id, "plan": plan,
            "all_findings": [], "sources_analyzed": task.get("assets_harvested", 0),
            "stagnation_counter": 0, "step_number": step_number,
            "last_reflection": {}, "current_depth": 0, "query_index": 0,
            "search_results_cache": [], "parsed_sources_cache": [],
            "digest_results_cache": [], "should_stop": False, "stop_reason": "",
        }
        self._states[task_id] = state
        logger.info("Resumed task %s from DB reconstruction at phase '%s' (step %d)",
                     task_id[:8], phase, step_number)
        return state

    def set_phase(self, task_id: str, phase: str) -> None:
        s = self._states.get(task_id)
        if s is None:
            s = self.resume_task(task_id)
        if s is None:
            raise RuntimeError(f"Cannot set phase — task not found: {task_id}")
        s["phase"] = phase

    def ensure_state(self, task_id: str) -> dict:
        s = self._states.get(task_id)
        if s is not None:
            return s
        s = self.resume_task(task_id)
        if s is not None:
            return s
        raise RuntimeError(f"No orchestrator state for {task_id}. Call init_task() first.")

    def get_state(self, task_id: str) -> dict:
        s = self._states.get(task_id)
        if s is None:
            s = self.resume_task(task_id)
        if s is None:
            raise RuntimeError(f"No orchestrator state for {task_id}. Call init_task() first.")
        return s

    def get_task_phase(self, task_id: str) -> str:
        state = self._states.get(task_id)
        if state is None:
            state = self.resume_task(task_id)
        return state["phase"] if state else ""

    def _persist_state(self, task_id: str) -> None:
        s = self._states.get(task_id)
        if not s:
            return
        clean = {k: v for k, v in s.items() if k in _ORCH_STATE_KEYS}
        try:
            self._task_repo.update(task_id, orchestrator_state=json.dumps(
                clean, default=str, ensure_ascii=False))
        except Exception:
            logger.warning("Failed to persist orchestrator state for %s", task_id[:8], exc_info=True)

    def _load_state(self, task_id: str) -> Optional[dict]:
        task = self._task_repo.get(task_id)
        if not task or not task.get("orchestrator_state"):
            return None
        try:
            state = json.loads(task["orchestrator_state"])
            for key in ("all_findings", "search_results_cache", "parsed_sources_cache", "digest_results_cache"):
                if key not in state:
                    state[key] = []
            if "last_reflection" not in state:
                state["last_reflection"] = {}
            return state
        except Exception:
            logger.warning("Failed to load orchestrator state for %s", task_id[:8], exc_info=True)
            return None

    @property
    def states(self) -> dict:
        return self._states

    @property
    def locks(self) -> dict:
        return self._locks
