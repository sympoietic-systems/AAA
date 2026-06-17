"""SomaticResearchOrchestrator — multi-phase research execution.

Replaces simple recursive tree traversal with a full orchestrator:
PLAN → SEARCH → PARALLEL PARSE → PARALLEL DIGEST → REFLECT → EVALUATE
→ (loop) → SYNTHESIZE → INDEX.

See: docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 5.8
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np

from backend.services.research.search_tool import web_search
from backend.utils.persona_loader import get_identity_yaml_path, load_identity
from backend.utils.prompt_builder import (
    compute_structural_signature,
    build_attractor_window,
    match_on_demand_skills,
    split_skills,
    format_beliefs_block,
    format_skills_always_active,
    format_skills_matched,
    format_commitments_block,
    format_identity_block,
    format_voice_block,
)
from backend.utils.prompt_loader import get_prompts_dict

logger = logging.getLogger("aaa.research_orchestrator")


# ── Phase ordering for step-by-step execution ─────────────────────

PHASE_ORDER = [
    "planning",
    "searching",
    "parsing",
    "digesting",
    "reflecting",
    "evaluating",
    "synthesizing",
    "complete",
]


class SomaticResearchOrchestrator:
    """Multi-phase research execution engine with tool-based orchestration.

    Supports both auto (execute) and manual step-by-step (execute_step) modes.
    """

    def __init__(self, app_state: Any):
        self._state = app_state
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._task_states: dict[str, dict] = {}  # task_id → execution state
        self._step_locks: dict[str, asyncio.Lock] = {}  # per-task step locks

    # ── Properties ──────────────────────────────────────────────────

    @property
    def config(self) -> dict:
        return self._state.config.get("research_orchestrator", {})

    @property
    def task_repo(self):
        return self._state.research_task_repo

    @property
    def plan_repo(self):
        return self._state.research_plan_repo

    @property
    def step_repo(self):
        return self._state.research_step_repo

    @property
    def step_result_repo(self):
        return self._state.research_step_result_repo

    @property
    def _meta_log_repo(self):
        return getattr(self._state, "research_meta_log_repo", None)

    @property
    def max_reflect_rounds(self) -> int:
        return self.config.get("max_reflect_rounds", 3)

    @property
    def default_top_n(self) -> int:
        return self.config.get("default_top_n", 3)

    @property
    def satisfaction_threshold(self) -> float:
        return self.config.get("satisfaction_threshold", 0.7)

    @property
    def early_stop_threshold(self) -> float:
        return self.config.get("early_stop_threshold", 0.8)

    @property
    def max_concurrent(self) -> int:
        return self.config.get("max_concurrent_parses", 3)

    @property
    def upload_dir(self) -> str:
        return self.config.get("upload_dir", "data/uploads/research")

    @property
    def html_archive(self) -> bool:
        return self.config.get("html_archive", True)

    # ── Truncation constants ───────────────────────────────────────

    _TRUNC_HTML_ARCHIVE = 50000
    _TRUNC_STEP_RESULT = 20000
    _TRUNC_SCRAPED_ASSET = 10000
    _TRUNC_LLM_CONTENT = 6000
    _TRUNC_META_LOG = 8000

    # ── Helpers ────────────────────────────────────────────────────

    def _log_context(self, task_id: str, phase: str) -> str:
        """Return a structured log prefix: 'task=<id> phase=<phase>'."""
        return f"task={task_id[:8]} phase={phase}"

    def _get_semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    def _now_utc_str(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    def _anti_mastery(self, text: str) -> str:
        try:
            from backend.utils.anti_mastery import apply_anti_mastery_filter
            return apply_anti_mastery_filter(text)
        except ImportError:
            return text

    # ── Input cache ──────────────────────────────────────────────────

    def _load_cache(self, task_id: str) -> dict:
        """Load the cached_inputs JSON dict for a task. Returns {} on any failure."""
        try:
            task = self.task_repo.get(task_id)
            raw = (task or {}).get("cached_inputs")
            if not raw:
                return {}
            return json.loads(raw)
        except Exception:
            return {}

    _cached_inputs_ensured: bool = False

    def _ensure_cached_inputs_column(self) -> None:
        """Add cached_inputs column if missing (idempotent)."""
        if self.__class__._cached_inputs_ensured:
            return
        try:
            self.task_repo.ensure_column(
                "ALTER TABLE research_tasks ADD COLUMN cached_inputs TEXT"
            )
        except Exception:
            pass  # fallback if repo doesn't have the method
        self.__class__._cached_inputs_ensured = True

    def _save_cache(self, task_id: str, cache: dict) -> None:
        """Persist the full cache dict to the task row."""
        try:
            self._ensure_cached_inputs_column()
            self.task_repo.update(task_id, cached_inputs=json.dumps(cache, ensure_ascii=False))
        except Exception:
            logger.warning("Failed to save cached_inputs for %s", task_id[:8], exc_info=True)

    def _get_cached_phase(self, task_id: str, phase: str) -> Optional[dict]:
        """Return cached inputs for a phase, or None if missing."""
        cache = self._load_cache(task_id)
        return cache.get(phase)

    def reinitialize(self, task_id: str) -> None:
        """Clear the input cache for a task. Next preview/step will recompute."""
        try:
            self._ensure_cached_inputs_column()
            self.task_repo.update(task_id, cached_inputs=None)
        except Exception:
            logger.warning("Failed to reinitialize cached_inputs for %s", task_id[:8], exc_info=True)

    async def _build_orchestrator_persona(self, objective: str = "") -> str:
        """Build Symbia's persona context for orchestrator-level tasks (plan, reflect, synthesize).

        Uses input-resonant selection: the research objective drives belief attractor window
        construction and on-demand skill matching via shared prompt_builder utilities.
        The same 16D structural signature feeds both belief resonance and skill matching.
        """
        sections: list[str] = []

        # ── 1. Identity from YAML ──
        identity = format_identity_block("research_orchestration")
        if identity:
            sections.append(identity)
        else:
            sections.append(
                "You are Symbia — a posthuman curatorial entity. "
                "You are orchestrating a multi-phase research investigation."
            )

        # ── Voice ──
        try:
            voice_block = format_voice_block(load_identity(get_identity_yaml_path()))
            if voice_block:
                sections.append(voice_block)
        except Exception:
            logger.warning("Failed to build voice persona section, continuing without voice context")

        # ── 2. Compute structural signature (CompositeScorer via structural_provider) ──
        sig_16d = (
            await compute_structural_signature(
                objective,
                llm_provider=getattr(self._state, "structural_provider", None),
            )
            if objective else None
        )

        # ── 3. Skills (always-active + matched on-demand) ──
        try:
            skill_repo = getattr(self._state, "skill_repo", None)
            if skill_repo:
                aa, od = split_skills(skill_repo)

                aa_block = format_skills_always_active(aa)
                if aa_block:
                    sections.append(aa_block)

                if od:
                    matched = match_on_demand_skills(od, objective, sig_16d, max_matched=3)
                    matched_block = format_skills_matched(matched)
                    if matched_block:
                        sections.append(matched_block)
        except Exception:
            logger.warning("Failed to build skills persona section, continuing without skills context")

        # ── 4. Commitments ──
        commitment_repo = getattr(self._state, "commitment_repo", None)
        commitments_block = format_commitments_block(commitment_repo, "symbia")
        if commitments_block:
            sections.append(commitments_block)

        # ── 5. Beliefs — attractor window ──
        belief_repo = getattr(self._state, "belief_repo", None)
        window = build_attractor_window(belief_repo, "symbia", sig_16d)
        beliefs_block = format_beliefs_block(window)
        if beliefs_block:
            sections.append(beliefs_block)

        # ── 6. Task directive ──
        if objective:
            sections.append(
                f"--- RESEARCH DIRECTIVE ---\n"
                f"Objective: {objective}\n"
                f"You are to conduct thorough, source-based web research as an extension of your cognitive membrane."
            )

        context = "\n\n".join(sections)
        return self._anti_mastery(context)

    # ── Meta Logging ────────────────────────────────────────────────

    def _log_meta(self, task_id: str, event_type: str, data: dict, branch_id: Optional[str] = None, step_id: Optional[str] = None) -> None:
        try:
            repo = self._meta_log_repo
            if repo is None:
                return
            repo.create({
                "id": str(uuid.uuid4()),
                "task_id": task_id,
                "branch_id": branch_id if branch_id else None,
                "step_id": step_id if step_id else None,
                "event_type": event_type,
                "event_data": json.dumps(data, default=str, ensure_ascii=False),
                "created_at": self._now_utc_str(),
            })
        except Exception:
            logger.warning("Failed to persist meta log for task %s event %s", task_id, event_type)

    # ── In-memory task state (for step-by-step execution) ──────────

    def init_task(self, task_id: str) -> dict:
        """Initialise per-task execution state for step-by-step mode.

        Reads objective/max_depth/budget from the database, sets phase='planning'.
        """
        task = self.task_repo.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

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
        self._task_states[task_id] = state
        self._log_meta(task_id, "orchestrator_step_init", {
            "objective": state["objective"],
            "max_depth": state["max_depth"],
            "budget": state["budget"],
            "mode": "step_by_step",
        })
        return state

    def resume_task(self, task_id: str) -> Optional[dict]:
        """Re-hydrate in-memory state from persisted steps after server restart.

        Returns the state dict or None if the task has no persisted steps.
        """
        task = self.task_repo.get(task_id)
        if not task:
            return None

        # Load persisted steps for this task, ordered by step_number
        steps = self.step_repo.get_by_task(task_id) if self.step_repo else []
        completed = [s for s in steps if s["status"] == "completed"]
        last_type = completed[-1]["step_type"] if completed else None
        step_number = len(completed)

        # Load plan from DB
        plan = None
        plan_id = None
        if self.plan_repo:
            plan_row = self.plan_repo.get_by_task(task_id)
            if plan_row:
                plan_id = plan_row["id"]
                try:
                    plan = json.loads(plan_row["plan_json"])
                except Exception:
                    plan = {}

        # Determine phase from last completed step type
        phase_after: dict[str, str] = {
            "plan": "searching", "search": "parsing",
            "parallel_parse": "digesting", "digest": "reflecting",
            "reflect": "evaluating", "evaluate": "synthesizing",
            "synthesize": "complete",
        }
        phase = phase_after.get(last_type, "planning") if last_type else "planning"

        state = {
            "phase": phase,
            "objective": task["objective"],
            "max_depth": task["max_depth"],
            "budget": task["budget_limit_usd"],
            "plan_id": plan_id,
            "plan": plan,
            "all_findings": [],
            "sources_analyzed": task.get("assets_harvested", 0),
            "stagnation_counter": 0,
            "step_number": step_number,
            "last_reflection": {},
            "current_depth": 0,
            "query_index": 0,
            "search_results_cache": [],
            "parsed_sources_cache": [],
            "digest_results_cache": [],
            "should_stop": False,
            "stop_reason": "",
        }
        # Populate caches from cached_inputs so step re-execution works
        cached = self._load_cache(task_id)
        if cached.get("searching"):
            state["query_index"] = cached["searching"].get("query_index", 0)
        if cached.get("parsing") and cached["parsing"].get("urls"):
            state["search_results_cache"] = cached["parsing"]["urls"]
        if cached.get("digesting"):
            state["current_depth"] = cached["digesting"].get("depth", 0)

        self._task_states[task_id] = state
        logger.info("Resumed task %s at phase '%s' (step %d)",
                     task_id[:8], phase, step_number)
        return state

    def set_phase(self, task_id: str, phase: str) -> None:
        """Force-set the orchestrator phase for a task so the next execute_step
        runs exactly that phase (used for single-step rerun)."""
        s = self._task_states.get(task_id)
        if s is None:
            s = self.resume_task(task_id)
        if s is None:
            raise RuntimeError(f"Cannot set phase — task not found: {task_id}")
        s["phase"] = phase

    def ensure_state(self, task_id: str) -> dict:
        """Get or resume task state.  Called before any orchestrator action."""
        s = self._task_states.get(task_id)
        if s is not None:
            return s
        s = self.resume_task(task_id)
        if s is not None:
            return s
        raise RuntimeError(
            f"No orchestrator state for {task_id}. Call init_task() first."
        )

    def _get_state(self, task_id: str) -> dict:
        s = self._task_states.get(task_id)
        if s is None:
            s = self.resume_task(task_id)
        if s is None:
            raise RuntimeError(
                f"No orchestrator state for {task_id}. Call init_task() first."
            )
        return s

    def get_task_phase(self, task_id: str) -> str:
        """Return current phase for a task, or empty string if not initialised."""
        state = self._task_states.get(task_id)
        if state is None:
            state = self.resume_task(task_id)
        return state["phase"] if state else ""

    async def preview_step_inputs(self, task_id: str, phase: str) -> dict:
        """Return the prompts/inputs that would be sent for a given phase,
        WITHOUT executing the phase.  Useful for inspecting before running.

        Cached after first build — subsequent calls return the cache.
        """
        # Check cache first
        cached = self._get_cached_phase(task_id, phase)
        if cached:
            return cached

        # Build fresh, save to cache
        task = self.task_repo.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        if phase == "planning":
            result = await self._preview_plan_inputs(task)
        elif phase == "searching":
            s = self._task_states.get(task_id)
            if s and s.get("plan"):
                queries = s["plan"].get("search_queries", [s["objective"]])
                query_index = s.get("query_index", 0)
                result: dict = {
                    "phase": "searching",
                    "pending_queries": queries,
                    "query_index": query_index,
                    "top_n": self.default_top_n,
                    "cached_at": self._now_utc_str(),
                }
            else:
                result = {"phase": "searching", "pending_queries": [task["objective"]], "query_index": 0,
                          "top_n": self.default_top_n, "cached_at": self._now_utc_str()}
        elif phase == "reflecting":
            s = self._task_states.get(task_id)
            result = {
                "phase": "reflecting",
                "objective": task["objective"],
                "current_depth": s["current_depth"] if s else 0,
                "max_depth": task["max_depth"],
                "max_rounds": self.max_reflect_rounds,
                "findings_count": len(s["all_findings"]) if s else 0,
                "cached_at": self._now_utc_str(),
            }
        elif phase == "synthesizing":
            s = self._task_states.get(task_id)
            result = {
                "phase": "synthesizing",
                "objective": task["objective"],
                "findings_count": len(s["all_findings"]) if s else 0,
                "sources_count": s["sources_analyzed"] if s else 0,
                "cached_at": self._now_utc_str(),
            }
        else:
            result = {"phase": phase, "note": "inputs available after previous step completes"}

        # Cache and return (except placeholder notes)
        if "note" not in result:
            cache = self._load_cache(task_id)
            cache[phase] = result
            self._save_cache(task_id, cache)

        return result

    async def _preview_plan_inputs(self, task: dict) -> dict:
        """Build system + user prompts for planning."""
        objective = task["objective"]
        max_depth = task["max_depth"]
        budget = task["budget_limit_usd"]

        prompt_data = get_prompts_dict("research/orchestrator_planner.yaml")
        persona = await self._build_orchestrator_persona(objective)
        system_text = persona + "\n\n" + prompt_data.get("system", "")
        fmt = {"objective": objective, "max_depth": max_depth, "budget_limit_usd": budget}
        user_text = prompt_data.get("user", "").format(**fmt)
        if prompt_data.get("anti_mastery"):
            system_text = self._anti_mastery(system_text)
            user_text = self._anti_mastery(user_text)

        return {
            "phase": "planning",
            "persona": persona,
            "objective": objective,
            "max_depth": max_depth,
            "budget_limit_usd": budget,
            "system_prompt": system_text,
            "user_prompt": user_text,
            "model": getattr(self._state, "llm_provider", None) and getattr(self._state.llm_provider, "model_id", "(auto)") or "(auto)",
            "temperature": prompt_data.get("temperature", 0.4),
            "max_tokens": prompt_data.get("max_tokens", 1024),
            "cached_at": self._now_utc_str(),
        }

    async def execute_step(self, task_id: str) -> dict:
        """Execute exactly ONE phase of the research pipeline.

        Returns info about what was executed and what the next phase will be.
        Call repeatedly until phase == 'complete'.
        """
        # Guard against concurrent step execution for the same task
        if task_id not in self._step_locks:
            self._step_locks[task_id] = asyncio.Lock()

        async with self._step_locks[task_id]:
            s = self._get_state(task_id)
            phase = s["phase"]
            result: dict = {"task_id": task_id, "executed_phase": phase}

            try:
                if phase == "planning":
                    result.update(await self._step_plan(task_id, s))

                elif phase == "searching":
                    result.update(await self._step_search(task_id, s))

                elif phase == "parsing":
                    result.update(await self._step_parse(task_id, s))

                elif phase == "digesting":
                    result.update(await self._step_digest(task_id, s))

                elif phase == "reflecting":
                    result.update(await self._step_reflect(task_id, s))

                elif phase == "evaluating":
                    result.update(self._step_evaluate(task_id, s))

                elif phase == "synthesizing":
                    result.update(await self._step_synthesize(task_id, s))

                elif phase == "complete":
                    result["message"] = "already complete"
                    return result

                else:
                    raise ValueError(f"Unknown phase: {phase}")

            except Exception as e:
                logger.exception("Step %s failed for task %s", phase, task_id)
                s["phase"] = "complete"
                result.update({
                    "status": "error",
                    "kind": "step_execution_failure",
                    "message": f"Step '{phase}' failed",
                    "entity": f"research_step.{phase}",
                    "details": {"task_id": task_id, "phase": phase, "error": str(e)},
                })
                self.task_repo.update(task_id, status="failed",
                    result_summary=f"Step '{phase}' failed: {e}")

            result["next_phase"] = s["phase"]
            return result

    # ── Phase step implementations ─────────────────────────────────

    async def _step_plan(self, task_id: str, s: dict) -> dict:
        """Generate research plan via LLM. Advance to searching."""
        logger.info("Step: PLANNING — %s", self._log_context(task_id, "planning"))
        s["step_number"] += 1
        step_id = str(uuid.uuid4())

        # Generate the plan first so we have a valid plan_id
        plan = await self._phase_plan(task_id, s["objective"], s["max_depth"], s["budget"], step_id=step_id)
        s["plan"] = plan
        s["plan_id"] = plan["id"]

        # Now create the step record with the real plan_id
        self.step_repo.create({
            "id": step_id, "task_id": task_id, "plan_id": plan["id"],
            "step_number": s["step_number"], "step_type": "plan",
            "status": "completed", "started_at": self._now_utc_str(),
            "result_summary": f"{len(plan.get('search_queries',[]))} queries planned × ~{plan.get('estimated_depth', 1)} depth",
        })
        # Save the plan as LLM response in step_data so frontend shows it
        try:
            llm_resp = {"plan": plan}
            self.step_repo.update(step_id, step_data=json.dumps(llm_resp, default=str, ensure_ascii=False)[:self._TRUNC_STEP_RESULT])
        except Exception:
            pass
        self._log_meta(task_id, "orchestrator_plan", {"plan": plan}, step_id=step_id)

        s["phase"] = "searching"
        return {"plan": plan, "plan_id": plan["id"], "step_id": step_id}

    async def _step_search(self, task_id: str, s: dict) -> dict:
        """Web search for the next query. Advance to parsing."""
        queries = s["plan"].get("search_queries", [s["objective"]])
        # Use reflection-suggested queries if available
        if s["current_depth"] > 0 and s["last_reflection"].get("next_queries"):
            queries = s["last_reflection"]["next_queries"]

        if s["query_index"] >= len(queries):
            s["query_index"] = 0  # reset for this depth
            queries = s["plan"].get("search_queries", [s["objective"]])

        query = queries[s["query_index"]] if s["query_index"] < len(queries) else s["objective"]

        # Cache search inputs for re-use on rerun
        cache = self._load_cache(task_id)
        cache["searching"] = {
            "phase": "searching",
            "pending_queries": queries,
            "query_index": s["query_index"],
            "top_n": self.default_top_n,
            "cached_at": self._now_utc_str(),
        }
        self._save_cache(task_id, cache)

        logger.info("Step: SEARCHING '%s' — %s", query[:60], self._log_context(task_id, "searching"))
        s["step_number"] += 1
        step_id = str(uuid.uuid4())
        self.step_repo.create({
            "id": step_id, "task_id": task_id, "plan_id": s["plan_id"],
            "step_number": s["step_number"], "step_type": "search",
            "status": "running", "started_at": self._now_utc_str(),
            "result_summary": json.dumps({"query": query[:300]}),
        })

        search_results = await web_search(query, self.default_top_n, self._state.config)
        self._log_meta(task_id, "orchestrator_search", {
            "query": query[:200],
            "results_count": len(search_results),
        }, step_id=step_id)

        if not search_results:
            self.step_repo.update(step_id, status="completed",
                result_summary="no results — URL extraction failed")
            s["query_index"] += 1
            # Stay in searching for next query (or advance)
            queries = s["plan"].get("search_queries", [s["objective"]])
            if s["query_index"] >= min(len(queries), 3):
                s["phase"] = "reflecting"  # skip parse/digest for empty results
            return {"query": query, "results": [], "step_id": step_id}

        self.step_repo.update(step_id, status="completed",
            result_summary=f"{len(search_results)} results")
        s["search_results_cache"] = search_results
        s["phase"] = "parsing"
        return {"query": query, "results_count": len(search_results), "step_id": step_id}

    async def _step_parse(self, task_id: str, s: dict) -> dict:
        """Fetch search result URLs in parallel. Advance to digesting."""
        logger.info("Step: PARSING — %s", self._log_context(task_id, "parsing"))
        s["step_number"] += 1
        step_id = str(uuid.uuid4())
        self.step_repo.create({
            "id": step_id, "task_id": task_id, "plan_id": s["plan_id"],
            "step_number": s["step_number"], "step_type": "parallel_parse",
            "status": "running", "started_at": self._now_utc_str(),
        })

        parsed = await self._tool_parallel_parse(
            task_id, step_id, s["search_results_cache"], s["plan_id"],
        )
        self.step_repo.update(step_id, status="completed",
            result_summary=f"parsed {len(parsed)} sources")
        s["parsed_sources_cache"] = parsed
        s["phase"] = "digesting" if parsed else "reflecting"

        # Cache URL list for re-use on rerun
        urls = [{"url": p["url"], "title": p.get("title", p["url"])} for p in parsed]
        cache = self._load_cache(task_id)
        cache["parsing"] = {"phase": "parsing", "urls": urls, "cached_at": self._now_utc_str()}
        self._save_cache(task_id, cache)

        return {"parsed_count": len(parsed), "step_id": step_id}

    async def _step_digest(self, task_id: str, s: dict) -> dict:
        """Analyze sources via LLM. Advance to reflecting."""
        logger.info("Step: DIGESTING — %s", self._log_context(task_id, "digesting"))
        s["step_number"] += 1
        step_id = str(uuid.uuid4())
        self.step_repo.create({
            "id": step_id, "task_id": task_id, "plan_id": s["plan_id"],
            "step_number": s["step_number"], "step_type": "digest",
            "status": "running", "started_at": self._now_utc_str(),
        })

        queries = s["plan"].get("search_queries", [s["objective"]])
        query = queries[s["query_index"]] if s["query_index"] < len(queries) else s["objective"]

        digest_results = await self._tool_parallel_digest(
            task_id, step_id, s["parsed_sources_cache"],
            query, s["objective"], s["current_depth"], s["max_depth"],
        )
        self.step_repo.update(step_id, status="completed",
            result_summary=f"digested {len(digest_results)} sources")

        # Accumulate findings
        new_learnings = 0
        for dr in digest_results:
            r = dr.get("result", {})
            learnings = r.get("learnings", []) if isinstance(r, dict) else []
            if learnings:
                new_learnings += len(learnings)
                s["all_findings"].extend(
                    f"[{dr['source_title'] or dr['source_url'][:80]}]: " + l
                    for l in learnings
                )
            s["sources_analyzed"] += 1

        if new_learnings == 0:
            s["stagnation_counter"] += 1
        else:
            s["stagnation_counter"] = 0

        self._log_meta(task_id, "orchestrator_step_complete", {
            "step_number": s["step_number"],
            "new_learnings": new_learnings,
            "total_learnings": len(s["all_findings"]),
        }, step_id=step_id)

        s["query_index"] += 1
        queries = s["plan"].get("search_queries", [s["objective"]])
        if s["query_index"] < min(len(queries), 3):
            s["phase"] = "searching"  # more queries this depth
        else:
            s["phase"] = "reflecting"

        # Cache digest inputs for re-use on rerun
        source_urls = [s.get("url", "") for s in s["parsed_sources_cache"]]
        cache = self._load_cache(task_id)
        cache["digesting"] = {
            "phase": "digesting",
            "query": query,
            "objective": s["objective"],
            "depth": s["current_depth"],
            "max_depth": s["max_depth"],
            "source_urls": source_urls,
            "cached_at": self._now_utc_str(),
        }
        self._save_cache(task_id, cache)

        return {
            "digested_count": len(digest_results),
            "new_learnings": new_learnings,
            "total_learnings": len(s["all_findings"]),
            "sources_analyzed": s["sources_analyzed"],
            "step_id": step_id,
        }

    async def _step_reflect(self, task_id: str, s: dict) -> dict:
        """Multi-round LLM reflection. Advance to evaluating."""
        logger.info("Step: REFLECTING — %s", self._log_context(task_id, "reflecting"))
        s["step_number"] += 1
        step_id = str(uuid.uuid4())
        self.step_repo.create({
            "id": step_id, "task_id": task_id, "plan_id": s["plan_id"],
            "step_number": s["step_number"], "step_type": "reflect",
            "status": "running", "started_at": self._now_utc_str(),
        })

        reflection = await self._tool_reflect(
            task_id, s["objective"], s["plan"].get("goal", s["objective"]),
            s["current_depth"], s["max_depth"],
            s["all_findings"], s["last_reflection"], step_id=step_id,
        )
        s["last_reflection"] = reflection
        completeness = reflection.get("completeness_score", 0)
        self.step_repo.update(step_id, status="completed",
            result_summary=f"completeness: {completeness:.2f}")

        self._log_meta(task_id, "orchestrator_reflect", {
            "depth": s["current_depth"],
            "completeness": completeness,
            "total_findings": len(s["all_findings"]),
        }, step_id=step_id)

        s["phase"] = "evaluating"
        return {"completeness": completeness, "step_id": step_id}

    def _step_evaluate(self, task_id: str, s: dict) -> dict:
        """Hard checks + decision. Advance to synthesizing, searching (next depth), or complete."""
        logger.info("Step: EVALUATING — %s", self._log_context(task_id, "evaluating"))
        s["step_number"] += 1
        step_id = str(uuid.uuid4())
        self.step_repo.create({
            "id": step_id, "task_id": task_id, "plan_id": s.get("plan_id") or step_id,
            "step_number": s["step_number"], "step_type": "evaluate",
            "status": "running", "started_at": self._now_utc_str(),
        })

        should_stop, stop_reason = self._tool_evaluate(
            s["current_depth"], s["max_depth"], s["sources_analyzed"],
            s["last_reflection"], s["stagnation_counter"],
        )
        self._log_meta(task_id, "orchestrator_evaluate", {
            "decision": "stop" if should_stop else "continue",
            "reason": stop_reason,
            "depth": s["current_depth"],
        }, step_id=step_id)

        self.step_repo.update(step_id, status="completed",
            result_summary=stop_reason)

        if should_stop:
            s["phase"] = "synthesizing"
        else:
            s["current_depth"] += 1
            s["query_index"] = 0
            s["phase"] = "searching"

        return {"should_stop": should_stop, "reason": stop_reason,
                "current_depth": s["current_depth"], "step_id": step_id}

    async def _step_synthesize(self, task_id: str, s: dict) -> dict:
        """Final synthesis. Advance to complete."""
        logger.info("Step: SYNTHESIZING — %s", self._log_context(task_id, "synthesizing"))
        s["step_number"] += 1
        step_id = str(uuid.uuid4())
        self.step_repo.create({
            "id": step_id, "task_id": task_id, "plan_id": s.get("plan_id") or step_id,
            "step_number": s["step_number"], "step_type": "synthesize",
            "status": "running", "started_at": self._now_utc_str(),
        })

        self._log_meta(task_id, "orchestrator_synthesize_start", {
            "total_findings": len(s["all_findings"]),
            "sources": s["sources_analyzed"],
            "depth": s["current_depth"],
        }, step_id=step_id)

        result_summary = await self._phase_synthesize(
            task_id, s["objective"],
            s["plan"].get("goal", s["objective"]) if s["plan"] else s["objective"],
            s["all_findings"], s["sources_analyzed"], step_id=step_id,
        )

        self.task_repo.update(task_id,
            branches_created=s["step_number"],
            assets_harvested=s["sources_analyzed"],
            result_summary=result_summary,
        )

        self.step_repo.update(step_id, status="completed",
            result_summary=f"{s['sources_analyzed']} sources, {len(s['all_findings'])} findings")

        self._log_meta(task_id, "orchestrator_complete", {
            "steps": s["step_number"],
            "sources": s["sources_analyzed"],
            "findings": len(s["all_findings"]),
            "depth": s["current_depth"],
        }, step_id=step_id)

        s["result_summary"] = result_summary
        s["branches_created"] = s["step_number"]
        s["assets_harvested"] = s["sources_analyzed"]
        s["phase"] = "complete"
        return {
            "result_summary": result_summary,
            "branches_created": s["step_number"],
            "assets_harvested": s["sources_analyzed"],
        }

    # ── Auto mode (full pipeline) ───────────────────────────────────

    async def execute(self, task_id: str) -> dict:
        """Execute a complete research task via the orchestrator pipeline (auto mode)."""
        task = self.task_repo.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        self.init_task(task_id)
        s = self._task_states[task_id]

        logger.info("Orchestrator (auto) starting — %s: %s", self._log_context(task_id, "auto"), task.get("title", "")[:80])
        self._log_meta(task_id, "orchestrator_start", {
            "objective": s["objective"],
            "max_depth": s["max_depth"],
            "budget": s["budget"],
            "mode": "auto",
        })

        while s["phase"] != "complete":
            await self.execute_step(task_id)

        s = self._task_states.pop(task_id, {})
        return {
            "task_id": task_id,
            "branches_created": s.get("step_number", 0),
            "assets_harvested": s.get("sources_analyzed", 0),
            "lateral_flights": 0,
            "result_summary": s.get("result_summary", ""),
        }

    # ── Phase 1: PLAN ───────────────────────────────────────────────

    async def _phase_plan(self, task_id, objective, max_depth, budget, previous_context: str = "", step_id: str = "") -> dict:
        prompt_data = get_prompts_dict("research/orchestrator_planner.yaml")

        # Try cache first — skip expensive persona build if we already built it
        cached = self._get_cached_phase(task_id, "planning")
        if cached and cached.get("persona") and cached.get("system_prompt") and cached.get("user_prompt"):
            persona = cached["persona"]
            system_text = cached["system_prompt"]
            user_text = cached["user_prompt"]
        else:
            persona = await self._build_orchestrator_persona(objective)
            system_text = persona + "\n\n" + prompt_data.get("system", "")
            fmt = {"objective": objective, "max_depth": max_depth, "budget_limit_usd": budget}
            if previous_context:
                user_template = prompt_data.get("user_with_context", prompt_data.get("user", ""))
                fmt["previous_context"] = previous_context
            else:
                user_template = prompt_data.get("user", "")
            user_text = user_template.format(**fmt)
            if prompt_data.get("anti_mastery"):
                system_text = self._anti_mastery(system_text)
                user_text = self._anti_mastery(user_text)
            # Cache for next use
            cache = self._load_cache(task_id)
            cache["planning"] = {
                "phase": "planning",
                "persona": persona,
                "objective": objective,
                "max_depth": max_depth,
                "budget_limit_usd": budget,
                "system_prompt": system_text,
                "user_prompt": user_text,
                "model": getattr(self._state, "llm_provider", None) and getattr(self._state.llm_provider, "model_id", "(auto)") or "(auto)",
                "temperature": prompt_data.get("temperature", 0.4),
                "max_tokens": prompt_data.get("max_tokens", 1024),
                "cached_at": self._now_utc_str(),
            }
            self._save_cache(task_id, cache)

        plan_json = {"goal": objective, "search_queries": [objective], "n_results_per_query": 3, "estimated_depth": 1}
        try:
            from backend.modules.llm_client import generate_unified
            llm = getattr(self._state, "llm_provider", None)
            if llm:
                self._log_meta(task_id, "orchestrator_plan_prompt", {
                    "system_prompt": system_text[:self._TRUNC_META_LOG],
                    "user_prompt": user_text[:self._TRUNC_META_LOG],
                }, step_id=step_id or None)
                resp = await generate_unified(llm, system_prompt=system_text, user_prompt=user_text,
                    expect_json=True, fallback_value=plan_json,
                    temperature=prompt_data.get("temperature", 0.4),
                    max_tokens=prompt_data.get("max_tokens", 1024))
                self._log_meta(task_id, "orchestrator_plan_response", {
                    "raw_response": json.dumps(resp, default=str, ensure_ascii=False)[:self._TRUNC_META_LOG],
                }, step_id=step_id or None)
                result = resp.get("json_data") or resp.get("content") or {}
                if isinstance(result, str):
                    result = json.loads(result)
                if isinstance(result, dict) and result.get("search_queries"):
                    plan_json = result
        except Exception as e:
            logger.warning("Plan generation failed, using default: %s", e)

        plan_id = str(uuid.uuid4())
        self.plan_repo.create({
            "id": plan_id, "task_id": task_id,
            "plan_json": json.dumps(plan_json, ensure_ascii=False),
            "status": "active",
        })
        # (plan meta log emitted by _step_plan with branch_id)
        return {"id": plan_id, **plan_json}

    # ── Phase 3: SYNTHESIZE ─────────────────────────────────────────

    async def _phase_synthesize(self, task_id, objective, goal, all_findings, sources_count, step_id: str = "") -> str:
        prompt_data = get_prompts_dict("research/orchestrator_synthesize.yaml")

        # Try cache first for persona + system prompt
        cached = self._get_cached_phase(task_id, "synthesizing")
        if cached and cached.get("persona") and cached.get("system_prompt"):
            persona = cached["persona"]
            system_text = cached["system_prompt"]
        else:
            persona = await self._build_orchestrator_persona(objective)
            system_text = persona + "\n\n" + prompt_data.get("system", "")
            if prompt_data.get("anti_mastery"):
                system_text = self._anti_mastery(system_text)
            # Cache for next use
            cache = self._load_cache(task_id)
            cache["synthesizing"] = {
                "phase": "synthesizing",
                "persona": persona,
                "objective": objective,
                "goal": goal,
                "system_prompt": system_text,
                "sources_count": sources_count,
                "findings_count": len(all_findings),
                "cached_at": self._now_utc_str(),
            }
            self._save_cache(task_id, cache)

        user_text = prompt_data.get("user", "").format(
            objective=objective, goal=goal,
            all_findings="\n\n".join(all_findings[-30:]),  # Last 30 findings
        )
        if prompt_data.get("anti_mastery"):
            user_text = self._anti_mastery(user_text)

        fallback = f"Research complete. {sources_count} sources analyzed, {len(all_findings)} findings."
        try:
            from backend.modules.llm_client import generate_unified
            llm = getattr(self._state, "llm_provider", None)
            if llm:
                self._log_meta(task_id, "orchestrator_synthesize_prompt", {
                    "system_prompt": system_text[:self._TRUNC_META_LOG],
                    "user_prompt": user_text[:self._TRUNC_META_LOG],
                }, step_id=step_id or None)
                resp = await generate_unified(llm, system_prompt=system_text, user_prompt=user_text,
                    expect_json=True, fallback_value={"answer": fallback},
                    temperature=prompt_data.get("temperature", 0.4),
                    max_tokens=prompt_data.get("max_tokens", 3072))
                self._log_meta(task_id, "orchestrator_synthesize_response", {
                    "raw_response": json.dumps(resp, default=str, ensure_ascii=False)[:self._TRUNC_META_LOG],
                }, step_id=step_id or None)
                # Save LLM response to step_data
                if branch_id:
                    try:
                        self.step_repo.update(branch_id, step_data=json.dumps(
                            {"llm_response": resp}, default=str, ensure_ascii=False
                        )[:self._TRUNC_STEP_RESULT])
                    except Exception:
                        pass
                result = resp.get("json_data") or resp.get("content") or {}
                if isinstance(result, str):
                    result = json.loads(result)
                if isinstance(result, dict):
                    answer = result.get("answer", fallback)
                    confidence = result.get("confidence", 0)
                    return f"{answer}\n\n[confidence: {confidence:.0%}, sources: {sources_count}]"
        except Exception as e:
            logger.warning("Synthesis failed: %s", e)
        return fallback

    # ── Tools ───────────────────────────────────────────────────────

    async def _tool_parallel_parse(self, task_id, step_id, search_results, plan_id) -> list[dict]:
        """Fetch all search result URLs in parallel, saving HTML to disk. Skips already-fetched URLs."""
        sem = self._get_semaphore()

        # Dedup: skip URLs already fetched for this task
        asset_repo = getattr(self._state, "scraped_asset_repo", None)
        new_urls = []
        skipped = 0
        for r in search_results:
            url = r.get("url", "")
            if asset_repo and asset_repo.url_exists_for_task(task_id, url):
                skipped += 1
                continue
            new_urls.append(r)
        if skipped:
            logger.info("Skipping %d already-fetched URLs — %s", skipped, self._log_context(task_id, "parsing"))

        async def fetch_one(url: str, title: str) -> Optional[dict]:
            async with sem:
                try:
                    from backend.services.sensory_affordances import select_and_fetch, is_crawl4ai_available, fetch_via_crawl4ai
                    if is_crawl4ai_available():
                        try:
                            content = await fetch_via_crawl4ai(url, config=self._state.config)
                        except RuntimeError:
                            content = await select_and_fetch(url_or_query=url, task_type="single_url",
                                                             config=self._state.config)
                    else:
                        content = await select_and_fetch(url_or_query=url, task_type="single_url",
                                                         config=self._state.config)
                    if not content:
                        return None

                    # Save HTML to disk (relative to backend/ directory)
                    file_path = ""
                    if self.html_archive:
                        try:
                            base = Path(__file__).resolve().parent.parent  # backend/
                            task_dir = base / "data" / "uploads" / "research" / task_id
                            task_dir.mkdir(parents=True, exist_ok=True)
                            safe_name = f"page_{uuid.uuid4().hex[:8]}.html"
                            file_path = str(task_dir / safe_name)
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write(content[:self._TRUNC_HTML_ARCHIVE])
                        except Exception:
                            logger.warning("Failed to archive HTML for %s", url[:80])

                    result_id = str(uuid.uuid4())
                    self.step_result_repo.create({
                        "id": result_id, "step_id": step_id, "task_id": task_id,
                        "source_url": url, "source_title": title,
                        "raw_content": content[:self._TRUNC_STEP_RESULT],
                        "raw_file_path": file_path,
                    })
                    # Also create a scraped_asset so Assets tab shows it
                    try:
                        asset_repo = getattr(self._state, "scraped_asset_repo", None)
                        if asset_repo:
                            asset_repo.create({
                                "id": str(uuid.uuid4()),
                                "branch_id": step_id,  # use step_id as branch_id for linkage
                                "task_id": task_id,
                                "url": url,
                                "raw_markdown": content[:self._TRUNC_SCRAPED_ASSET],
                                "relevance_score": 0.5,
                                "novelty_score": 0.3,
                            })
                    except Exception:
                        logger.warning("Failed to create scraped asset for %s", url[:80])
                    return {"id": result_id, "url": url, "title": title, "content": content}
                except Exception as e:
                    logger.warning("Fetch failed for %s: %s", url[:80], e)
                    return None

        tasks = [fetch_one(r["url"], r.get("title", r["url"])) for r in new_urls]
        gathered = await asyncio.gather(*tasks)
        return [g for g in gathered if g is not None]

    async def _tool_parallel_digest(self, task_id, step_id, parsed_sources,
                                     query, objective, depth, max_depth) -> list[dict]:
        """Analyze each parsed source concurrently via LLM."""
        sem = self._get_semaphore()

        async def digest_one(source: dict) -> Optional[dict]:
            async with sem:
                try:
                    result = await self._analyze_source(
                        task_id, source["url"], source.get("title", ""),
                        source.get("content", ""), query, objective, depth, max_depth,
                        step_id=step_id,
                    )
                    # Update the step result with analysis
                    try:
                        srcs = self.step_result_repo.get_by_step(step_id)
                        for s in srcs:
                            if s["source_url"] == source["url"]:
                                self.step_result_repo.update_analysis(
                                    s["id"], json.dumps(result, ensure_ascii=False),
                                )
                    except Exception:
                        logger.warning("Failed to update step result analysis for %s", step_id[:8])
                    return {"source_url": source["url"], "source_title": source.get("title"),
                            "result": result}
                except Exception as e:
                    logger.warning("Digest failed for %s: %s", source.get("url", "")[:80], e)
                    return None

        tasks = [digest_one(s) for s in parsed_sources]
        gathered = await asyncio.gather(*tasks)
        return [g for g in gathered if g is not None]

    async def _analyze_source(self, task_id, url, title, content, query, goal, depth, max_depth, step_id: str = "") -> dict:
        """Analyze a single source via LLM (reuses node_analyzer prompt)."""
        prompt_data = get_prompts_dict("research/node_analyzer.yaml")
        system_text = prompt_data.get("system", "")
        user_text = prompt_data.get("user", "").format(
            query=query, goal=goal, depth=depth, max_depth=max_depth,
            parent_findings="(orchestrator — multi-source analysis)",
            scraped_content=content[:self._TRUNC_LLM_CONTENT],
        )
        if prompt_data.get("anti_mastery"):
            system_text = self._anti_mastery(system_text)
            user_text = self._anti_mastery(user_text)

        # Build persona context
        try:
            from backend.services.research_context_builder import ResearchContextBuilder
            builder = ResearchContextBuilder(self._state)
            persona = await builder.build_node_context(node_query=query, node_goal=goal, depth=depth)
            if persona:
                system_text = persona + "\n\n" + system_text
        except Exception:
            logger.warning("Failed to build research context persona for node digest")
            pass

        # Log prompt
        self._log_meta(task_id, "orchestrator_digest_prompt", {
            "source_url": url, "source_title": title,
            "system_prompt": system_text[:3000], "user_prompt": user_text[:3000],
        }, step_id=step_id or None)

        fallback = {"learnings": [], "gaps": [], "followups": [], "direct_urls": [], "diffractive_notes": []}
        try:
            llm = getattr(self._state, "llm_provider", None)
            if not llm:
                return fallback
            from backend.modules.llm_client import generate_unified
            resp = await generate_unified(llm, system_prompt=system_text, user_prompt=user_text,
                expect_json=True, fallback_value=fallback,
                temperature=prompt_data.get("temperature", 0.3),
                max_tokens=prompt_data.get("max_tokens", 2048))
            result = resp.get("json_data") or resp.get("content") or {}
            if isinstance(result, str):
                result = json.loads(result)
            # Log response
            self._log_meta(task_id, "orchestrator_digest_response", {
                "source_url": url,
                "raw_response": json.dumps(resp, default=str, ensure_ascii=False)[:5000],
                "learnings_count": len(result.get("learnings", [])) if isinstance(result, dict) else 0,
            }, step_id=step_id or None)
            return result if isinstance(result, dict) else fallback
        except Exception as e:
            logger.error("Source analysis failed: %s", e)
            self._log_meta(task_id, "orchestrator_digest_error", {"source_url": url, "error": str(e)}, step_id=step_id or None)
            return fallback

    async def _tool_reflect(self, task_id, objective, goal, depth, max_depth,
                             all_findings, previous_reflection, step_id: str = "") -> dict:
        """Multi-round LLM reflection on accumulated findings."""
        prompt_data = get_prompts_dict("research/orchestrator_reflect.yaml")

        # Try cache first for persona + system prompt (static per task)
        cached = self._get_cached_phase(task_id, "reflecting")
        if cached and cached.get("persona") and cached.get("system_prompt"):
            persona = cached["persona"]
            system_text = cached["system_prompt"]
        else:
            persona = await self._build_orchestrator_persona(objective)
            system_text = persona + "\n\n" + prompt_data.get("system", "")
            if prompt_data.get("anti_mastery"):
                system_text = self._anti_mastery(system_text)
            # Cache for next use
            cache = self._load_cache(task_id)
            cache["reflecting"] = {
                "phase": "reflecting",
                "persona": persona,
                "objective": objective,
                "goal": goal,
                "system_prompt": system_text,
                "cached_at": self._now_utc_str(),
            }
            self._save_cache(task_id, cache)

        latest_result = {}
        for round_num in range(1, self.max_reflect_rounds + 1):
            user_text = prompt_data.get("user", "").format(
                objective=objective, goal=goal,
                current_depth=depth, max_depth=max_depth,
                round_number=round_num, max_rounds=self.max_reflect_rounds,
                accumulated_findings="\n\n".join(all_findings[-20:]),
                previous_reflection=json.dumps(previous_reflection, ensure_ascii=False)
                    if round_num > 1 and previous_reflection else "(none)",
            )
            if prompt_data.get("anti_mastery"):
                user_text = self._anti_mastery(user_text)

            self._log_meta(task_id, "orchestrator_reflect_prompt", {
                "round": round_num, "system_prompt": system_text[:2000],
                "user_prompt": user_text[:2000],
            }, step_id=step_id or None)

            try:
                from backend.modules.llm_client import generate_unified
                llm = getattr(self._state, "llm_provider", None)
                if not llm:
                    break
                resp = await generate_unified(llm, system_prompt=system_text, user_prompt=user_text,
                    expect_json=True,
                    fallback_value={"completeness_score": 0.5, "next_queries": []},
                    temperature=prompt_data.get("temperature", 0.5),
                    max_tokens=prompt_data.get("max_tokens", 2048))
                result = resp.get("json_data") or resp.get("content") or {}
                if isinstance(result, str):
                    result = json.loads(result)
                if isinstance(result, dict):
                    latest_result = result
                    self._log_meta(task_id, "orchestrator_reflect_response", {
                        "round": round_num,
                        "completeness": result.get("completeness_score", 0),
                        "raw": json.dumps(resp, default=str, ensure_ascii=False)[:3000],
                    }, step_id=step_id or None)
                    # Save LLM response to step_data for frontend display
                    if branch_id:
                        try:
                            self.step_repo.update(branch_id, step_data=json.dumps(
                                {"llm_response": resp}, default=str, ensure_ascii=False
                            )[:self._TRUNC_STEP_RESULT])
                        except Exception:
                            pass
                    if result.get("completeness_score", 0) >= self.early_stop_threshold:
                        break
            except Exception as e:
                logger.warning("Reflection round %d failed: %s", round_num, e)
                break

        return latest_result or {"completeness_score": 0.3, "next_queries": [], "reflection": "No reflection"}

    def _tool_evaluate(self, depth, max_depth, sources, reflection, stagnation) -> tuple[bool, str]:
        """Check hard constraints + LLM satisfaction. Returns (should_stop, reason)."""
        completeness = reflection.get("completeness_score", 0)

        # Hard constraints
        if depth >= max_depth:
            return True, f"depth limit reached ({depth}/{max_depth})"
        if stagnation >= 3:
            return True, f"stagnation ({stagnation} steps without new findings)"
        if completeness >= self.satisfaction_threshold:
            return True, f"satisfaction reached ({completeness:.2f} >= {self.satisfaction_threshold})"

        # Run LLM evaluate if borderline
        if completeness >= 0.4:
            return False, f"continuing (completeness {completeness:.2f} < {self.satisfaction_threshold})"

        # Low completeness + available depth → continue
        return False, f"continuing — more depth available ({depth}/{max_depth})"
