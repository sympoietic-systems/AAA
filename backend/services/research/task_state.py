import json
import logging
from typing import Any, Dict, List, Optional, Generic, TypeVar

from pydantic import BaseModel, Field

from backend.utils.research_logger import log_research_meta

logger = logging.getLogger("aaa.research_orchestrator")

# ── Generic Step Envelope & Payloads ─────────────────────────────────

T = TypeVar("T", bound=BaseModel)

class StepEnvelope(BaseModel, Generic[T]):
    """Unified container for executing any phase. Can be serialized directly."""
    task_id: str
    objective: str
    current_depth: int
    max_depth: int
    budget: float
    all_findings: List[str] = Field(default_factory=list)
    digest_signals: Dict[str, Any] = Field(default_factory=dict)
    inject_file_id: Optional[str] = None
    document_digested: bool = False
    plan_id: Optional[str] = None
    
    # Step-specific payload configuration/data
    payload: T

class PlanPayload(BaseModel):
    previous_context: Optional[str] = None
    inject_file_id: Optional[str] = None
    goal: Optional[str] = None
    search_queries: List[str] = Field(default_factory=list)
    n_results_per_query: int = 3
    estimated_depth: int = 1

class SearchPayload(BaseModel):
    queries: List[str] = Field(default_factory=list)
    direct_urls: List[str] = Field(default_factory=list)
    search_results: List[dict] = Field(default_factory=list)

class ParsePayload(BaseModel):
    search_results_cache: List[dict] = Field(default_factory=list)
    parsed_sources: List[dict] = Field(default_factory=list)

class DigestPayload(BaseModel):
    parsed_sources_cache: List[dict] = Field(default_factory=list)
    learnings: List[str] = Field(default_factory=list)
    followups: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)

class ConsolidatePayload(BaseModel):
    last_reflection: Dict[str, Any] = Field(default_factory=dict)
    completeness_score: float = 0.0
    key_insights: List[str] = Field(default_factory=list)
    remaining_gaps: List[str] = Field(default_factory=list)
    next_queries: List[str] = Field(default_factory=list)
    next_direct_urls: List[str] = Field(default_factory=list)

ReflectPayload = ConsolidatePayload

class EvaluatePayload(BaseModel):
    stagnation_counter: int
    sources_analyzed: int
    reflection: Dict[str, Any] = Field(default_factory=dict)
    should_stop: bool = False
    stop_reason: str = ""

class SynthesizePayload(BaseModel):
    sources_analyzed: int
    result_summary: str = ""

class DocDigestPayload(BaseModel):
    inject_file_id: str
    inject_conversation_id: Optional[str] = None
    document_mode: str = "chunks"
    document_chunk_limit: int = 5
    learnings: List[str] = Field(default_factory=list)
    followups: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)

class StepOutput(BaseModel):
    """Result of step execution returned by any phase processor."""
    status: str = "completed"  # completed, failed, error
    message: str = ""
    payload: BaseModel
    new_findings: List[str] = Field(default_factory=list)
    signal_flags: Dict[str, Any] = Field(default_factory=dict)
    transition_rationale: Optional[str] = None
    step_ids: List[str] = Field(default_factory=list)


_ORCH_STATE_KEYS = {
    "phase", "objective", "max_depth", "budget", "plan_id", "plan",
    "all_findings", "sources_analyzed", "stagnation_counter",
    "step_number", "last_reflection", "current_depth", "query_index",
    "search_results_cache", "parsed_sources_cache",
    "digest_results_cache", "digest_signals",
    "should_stop", "stop_reason",
    "inject_file_id", "inject_conversation_id", "document_mode", "document_chunk_limit",
    "document_digested", "document_learnings",
    "previous_context", "continue_from_task_id",
}


def make_initial_state(task: dict) -> dict:
    import json as _json
    extra = {}
    orch_state_raw = task.get("orchestrator_state")
    if orch_state_raw:
        try:
            extra = _json.loads(orch_state_raw) if isinstance(orch_state_raw, str) else orch_state_raw
        except Exception:
            pass

    state = {
        "phase": "planning",
        "objective": task["objective"],
        "max_depth": task["max_depth"],
        "budget": task["budget_limit_usd"],
        "plan_id": None,
        "plan": None,
        "all_findings": [],
        "sources_analyzed": 0,
        "stagnation_counter": 0,
        "step_number": extra.get("step_number", 0),
        "last_reflection": {},
        "current_depth": extra.get("current_depth", 0),
        "query_index": 0,
        "search_results_cache": [],
        "parsed_sources_cache": [],
        "digest_results_cache": [],
        "digest_signals": extra.get("digest_signals", {}),
        "should_stop": False,
        "stop_reason": "",
        "inject_file_id": task.get("inject_file_id") or extra.get("inject_file_id"),
        "inject_conversation_id": task.get("inject_conversation_id") or extra.get("inject_conversation_id"),
        "document_mode": task.get("document_mode") or extra.get("document_mode", "chunks"),
        "document_chunk_limit": task.get("document_chunk_limit") or extra.get("document_chunk_limit", 5),
        "document_digested": extra.get("document_digested", False),
        "document_learnings": extra.get("document_learnings", []),
        "previous_context": extra.get("previous_context"),
        "continue_from_task_id": extra.get("continue_from_task_id"),
    }
    logger.info("make_initial_state: step_number=%s, previous_context=%d chars",
                 state["step_number"], len(state.get("previous_context") or ""))
    import sys
    print(f">>> make_initial_state: step_number={state['step_number']}, current_depth={state.get('current_depth')}", flush=True)
    return state


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
            if "phase" not in loaded:
                loaded["phase"] = "planning"
            for key, default in [("digest_signals", {}), ("inject_file_id", None),
                                  ("inject_conversation_id", None),
                                  ("document_mode", "chunks"), ("document_chunk_limit", 5),
                                  ("document_digested", False), ("document_learnings", [])]:
                if key not in loaded:
                    loaded[key] = default
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
            "synthesize": "complete", "document_digestion": "searching",
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
            "digest_results_cache": [], "digest_signals": {},
            "should_stop": False, "stop_reason": "",
            "inject_file_id": task.get("inject_file_id"),
            "inject_conversation_id": task.get("inject_conversation_id"),
            "document_mode": task.get("document_mode", "chunks"),
            "document_chunk_limit": task.get("document_chunk_limit", 5),
            "document_digested": False, "document_learnings": [],
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
        return state.get("phase", "") if state else ""

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
            for key in ("last_reflection", "digest_signals"):
                if key not in state:
                    state[key] = {}
            for key_def in [("document_digested", False), ("document_learnings", []),
                            ("inject_conversation_id", None),
                            ("document_mode", "chunks"), ("document_chunk_limit", 5)]:
                if key_def[0] not in state:
                    state[key_def[0]] = key_def[1]
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
