"""SomaticResearchOrchestrator — multi-phase research execution.

Replaces simple recursive tree traversal with a full orchestrator:
PLAN → SEARCH → PARALLEL PARSE → PARALLEL DIGEST → REFLECT → EVALUATE
→ (loop) → SYNTHESIZE → INDEX.

See: docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 5.8
"""

import asyncio
import json
import logging
import re
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
    def asset_repo(self):
        return getattr(self._state, "scraped_asset_repo", None)

    @property
    def branch_repo(self):
        return getattr(self._state, "research_branch_repo", None)

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

    async def _build_orchestrator_persona(self, objective: str = "", context_key: str = "research_orchestration") -> str:
        """Build Symbia's persona context for orchestrator-level tasks (plan, reflect, synthesize).

        Uses input-resonant selection: the research objective drives belief attractor window
        construction and on-demand skill matching via shared prompt_builder utilities.
        The same 16D structural signature feeds both belief resonance and skill matching.
        """
        sections: list[str] = []

        # ── 1. Identity from YAML ──
        identity = format_identity_block(context_key)
        if identity:
            sections.append(identity)
        else:
            sections.append(
                f"You are Symbia — a posthuman curatorial entity. "
                f"You are executing operational protocols for: {context_key}."
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

    def _log_llm_response(self, task_id: str, event_type: str, resp: dict, extra: Optional[dict] = None, step_id: Optional[str] = None) -> None:
        """Log an LLM response safely by truncating large fields within the dictionary,
        ensuring the serialized JSON is always valid. Writes to both raw_response and raw.
        """
        try:
            log_resp = resp.copy()
            if "thinking" in log_resp and isinstance(log_resp["thinking"], str):
                log_resp["thinking"] = log_resp["thinking"][:3000]
            if "content" in log_resp and isinstance(log_resp["content"], str):
                log_resp["content"] = log_resp["content"][:12000]
            
            event_data = extra.copy() if extra else {}
            serialized = json.dumps(log_resp, default=str, ensure_ascii=False)
            event_data["raw_response"] = serialized
            event_data["raw"] = serialized
            
            self._log_meta(task_id, event_type, event_data, step_id=step_id)
        except Exception:
            logger.warning("Failed to log LLM response for task %s event %s", task_id, event_type, exc_info=True)

    def _get_or_create_default_branch(self, task_id: str) -> str:
        """Get or create a default branch ID for the task to satisfy scraped_assets.branch_id NOT NULL / FK constraints."""
        if not self.branch_repo:
            raise RuntimeError("branch_repo is not available")

        branches = self.branch_repo.get_by_task(task_id)
        if branches:
            return branches[0]["id"]

        # Create a default/dummy branch
        task = self.task_repo.get(task_id)
        conv_id = (task or {}).get("conversation_id") or "default_conv"
        
        # Ensure the conversation exists to satisfy the branch FK constraint
        try:
            conn = self.branch_repo._conn()
            exists = conn.execute("SELECT 1 FROM conversations WHERE id = ?", (conv_id,)).fetchone()
            if not exists:
                conn.execute(
                    "INSERT OR IGNORE INTO conversations (id, title, agent_id) VALUES (?, ?, ?)",
                    (conv_id, "System Generated Conversation", "system")
                )
                conn.commit()
        except Exception as e:
            logger.warning("Failed to verify/create dummy conversation %s: %s", conv_id, e)

        branch_id = str(uuid.uuid4())
        self.branch_repo.create({
            "id": branch_id,
            "task_id": task_id,
            "conversation_id": conv_id,
            "parent_branch_id": None,
            "query": (task or {}).get("objective", "default"),
            "goal": "Autonomous research execution",
            "depth": 0,
            "breadth": 0,
            "status": "crystallized",
        })
        return branch_id

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
        """Re-hydrate in-memory state from persisted orchestrator_state.

        Returns the state dict or None if the task has no persisted state.
        Falls back to reconstructing from DB steps if orchestrator_state is absent.
        """
        task = self.task_repo.get(task_id)
        if not task:
            return None

        # Prefer orchestrator_state — the single source of truth
        loaded = self._load_state(task_id)
        if loaded:
            loaded["objective"] = task["objective"]
            loaded["max_depth"] = task["max_depth"]
            loaded["budget"] = task["budget_limit_usd"]
            self._task_states[task_id] = loaded
            logger.info("Resumed task %s from orchestrator_state at phase '%s' (step %d)",
                         task_id[:8], loaded.get("phase"), loaded.get("step_number", 0))
            return loaded

        # Fallback: reconstruct from DB (legacy, for tasks created before m039)
        steps = self.step_repo.get_by_task(task_id) if self.step_repo else []
        completed = [s for s in steps if s["status"] == "completed"]
        last_type = completed[-1]["step_type"] if completed else None
        step_number = len(completed)

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
        self._task_states[task_id] = state
        logger.info("Resumed task %s from DB reconstruction at phase '%s' (step %d)",
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

        s = self._task_states.get(task_id)
        if s is None:
            s = self.resume_task(task_id)

        if phase == "planning":
            result = await self._preview_plan_inputs(task)
        elif phase == "searching":
            if s and s.get("plan"):
                raw_queries = s["plan"].get("search_queries", [s["objective"]])
                if s["current_depth"] > 0 and s.get("last_reflection", {}).get("next_queries"):
                    raw_queries = s["last_reflection"]["next_queries"]
                
                search_queries = []
                direct_urls = []

                if s.get("last_reflection") and isinstance(s["last_reflection"], dict):
                    for u in s["last_reflection"].get("next_direct_urls", []):
                        if isinstance(u, str) and (u.startswith("http://") or u.startswith("https://")):
                            if u not in direct_urls:
                                direct_urls.append(u)

                for q in raw_queries:
                    if isinstance(q, str) and (q.startswith("http://") or q.startswith("https://")):
                        if q not in direct_urls:
                            direct_urls.append(q)
                    else:
                        search_queries.append(q)

                direct_urls = direct_urls[:5]
                pending_queries = search_queries + (["Direct URL Parse Pointers"] if direct_urls else [])

                result: dict = {
                    "phase": "searching",
                    "pending_queries": pending_queries,
                    "query_index": s.get("query_index", 0),
                    "top_n": self.default_top_n,
                    "cached_at": self._now_utc_str(),
                }
            else:
                result = {"phase": "searching", "pending_queries": [task["objective"]], "query_index": 0,
                          "top_n": self.default_top_n, "cached_at": self._now_utc_str()}
        elif phase == "parsing":
            urls = []
            if s and s.get("search_results_cache"):
                urls = [{"url": r.get("url", ""), "title": r.get("title", r.get("url", "")), "query_group": r.get("query_group")} for r in s["search_results_cache"]]
            result = {
                "phase": "parsing",
                "urls_to_fetch": urls,
                "cached_at": self._now_utc_str(),
            }
        elif phase == "digesting":
            sources = []
            system_prompt = ""
            user_prompt = ""
            if s:
                # Re-hydrate parsed_sources_cache if empty — scope to current_depth only
                if not s.get("parsed_sources_cache") and self.step_repo and self.step_result_repo:
                    steps = self.step_repo.get_by_task(task_id)
                    current_depth = s.get("current_depth", 0)
                    parse_steps = [
                        st for st in steps
                        if st["step_type"] == "parallel_parse" and st["status"] == "completed"
                        and self._get_step_depth(st) == current_depth
                    ]
                    if parse_steps:
                        s["parsed_sources_cache"] = []
                        for ps in parse_steps:
                            db_results = self.step_result_repo.get_by_step(ps["id"])
                            for r in db_results:
                                s["parsed_sources_cache"].append({
                                    "id": r["id"],
                                    "url": r["source_url"],
                                    "title": r["source_title"],
                                    "content": r["raw_content"],
                                    "query_group": ps.get("query_group", 1),
                                })
                parsed_sources = s.get("parsed_sources_cache", [])
                if parsed_sources:
                    sources = [
                        {
                            "url": src["url"],
                            "title": src.get("title", ""),
                            "snippet": src.get("content", "")[:300] + "...",
                            "query_group": src.get("query_group"),
                        }
                        for src in parsed_sources
                    ]
                    # Generate a preview of the prompt using the first parsed source
                    try:
                        first_src = parsed_sources[0]
                        q_group = first_src.get("query_group", 1)
                        queries = s["plan"].get("search_queries", [s["objective"]])
                        if s["current_depth"] > 0 and s["last_reflection"].get("next_queries"):
                            queries = s["last_reflection"]["next_queries"]
                        q_text = queries[q_group - 1] if (q_group - 1) < len(queries) else s["objective"]
                        
                        prompt_data = get_prompts_dict("research/node_analyzer.yaml")
                        system_text = prompt_data.get("system", "")
                        user_text = prompt_data.get("user", "").format(
                            query=q_text,
                            goal=s["objective"],
                            depth=s["current_depth"],
                            max_depth=task["max_depth"],
                            parent_findings="(orchestrator — multi-source analysis)",
                            scraped_content=first_src.get("content", "")[:1000] + "\n[... truncated for preview ...]",
                        )
                        if prompt_data.get("anti_mastery"):
                            system_text = self._anti_mastery(system_text)
                            user_text = self._anti_mastery(user_text)
                            
                        try:
                            from backend.services.research_context_builder import ResearchContextBuilder
                            builder = ResearchContextBuilder(self._state)
                            persona = await builder.build_node_context(node_query=q_text, node_goal=s["objective"], depth=s["current_depth"])
                            if persona:
                                system_text = persona + "\n\n" + system_text
                        except Exception:
                            pass
                            
                        system_prompt = system_text
                        user_prompt = user_text
                    except Exception as pe:
                        logger.warning("Failed to generate digest preview prompts: %s", pe)
            result = {
                "phase": "digesting",
                "sources_to_digest": sources,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "cached_at": self._now_utc_str(),
            }
        elif phase == "reflecting":
            prompt_data = get_prompts_dict("research/orchestrator_reflect.yaml")
            system_text = prompt_data.get("system", "")
            
            # Use cached persona or build it
            cached = self._get_cached_phase(task_id, "reflecting")
            if cached and cached.get("persona"):
                persona = cached["persona"]
            else:
                persona = await self._build_orchestrator_persona(task["objective"])
                
            system_prompt = persona + "\n\n" + system_text
            if prompt_data.get("anti_mastery"):
                system_prompt = self._anti_mastery(system_prompt)

            signals = s.get("digest_signals", {}) if s else {}
            followups_text = "\n".join(f"- {f}" for f in signals.get("followups", [])) or "(none)"
            direct_urls_text = "\n".join(f"- {u}" for u in signals.get("direct_urls", [])) or "(none)"
            gaps_text = "\n".join(f"- {g}" for g in signals.get("gaps", [])) or "(none)"
            all_findings = s.get("all_findings", []) if s else []

            parsed_urls_list = []
            if self.step_result_repo:
                try:
                    task_results = self.step_result_repo.get_by_task(task_id)
                    seen_urls = set()
                    for r in task_results:
                        url = r.get("source_url")
                        raw_content = r.get("raw_content")
                        if url and url not in seen_urls and raw_content is not None:
                            seen_urls.add(url)
                            title = r.get("source_title") or url
                            status = self._classify_source_status(raw_content)
                            parsed_urls_list.append({"url": url, "title": title, "status": status})
                except Exception as e:
                    logger.warning("Failed to retrieve parsed URLs: %s", e)

            depth = s.get("current_depth", 0) if s else 0
            previous_reflection = s.get("last_reflection", {}) if (s and s.get("last_reflection")) else {}

            # Extract findings of the current cycle from the DB
            current_cycle_findings = []
            if self.step_repo and self.step_result_repo:
                try:
                    steps = self.step_repo.get_by_task(task_id)
                    current_parse_steps = [
                        st for st in steps
                        if st.get("step_type") == "parallel_parse" and self._get_step_depth(st) == depth
                    ]
                    for ps in current_parse_steps:
                        db_results = self.step_result_repo.get_by_step(ps["id"])
                        for r in db_results:
                            if r.get("analyzed_json"):
                                try:
                                    analysis = json.loads(r["analyzed_json"])
                                    learnings = analysis.get("learnings", [])
                                    title = r.get("source_title") or r.get("source_url", "")[:80]
                                    for l in learnings:
                                        current_cycle_findings.append(f"[{title}]: {l}")
                                except Exception:
                                    pass
                except Exception as e:
                    logger.warning("Failed to retrieve current cycle findings for preview: %s", e)

            # Fallback if DB fetch returned nothing
            if not current_cycle_findings:
                current_cycle_findings = all_findings

            # Compute historical findings
            historical_set = set(all_findings) - set(current_cycle_findings)
            historical_findings = [f for f in all_findings if f in historical_set]

            # Compress findings and extract sources map globally
            all_to_compress = current_cycle_findings + historical_findings
            formatted_urls, compressed_all, compressed_followups, compressed_gaps = self._apply_unified_references(
                parsed_urls_list,
                all_to_compress,
                signals.get("followups", []),
                signals.get("gaps", []),
            )
            
            parsed_urls_text = "\n".join(formatted_urls) or "(none)"
            compressed_current = compressed_all[:len(current_cycle_findings)]
            compressed_historical = compressed_all[len(current_cycle_findings):]

            if depth > 0:
                accumulated_findings_text = (
                    f"### New Findings (Cycle {depth + 1}):\n" +
                    ("\n".join(compressed_current) if compressed_current else "(none)")
                )
                if historical_findings:
                    accumulated_findings_text += (
                        f"\n\n### Historical Findings (Cycle 1 to {depth}):\n" +
                        "\n".join(compressed_historical)
                    )
            else:
                accumulated_findings_text = "\n".join(compressed_current)

            followups_text = "\n".join(f"- {f}" for f in compressed_followups) or "(none)"
            gaps_text = "\n".join(f"- {g}" for g in compressed_gaps) or "(none)"
            direct_urls_text = "\n".join(f"- {u}" for u in signals.get("direct_urls", [])) or "(none)"

            # Format previous_reflection as structured markdown
            prev_refl_formatted = "(none)"
            if previous_reflection and isinstance(previous_reflection, dict):
                parts = []
                if previous_reflection.get("reflection"):
                    parts.append(f"Methodological Reflection (Cycle {depth}):\n{previous_reflection.get('reflection')}")
                if previous_reflection.get("key_insights"):
                    insights = [f"- {ins}" for ins in previous_reflection.get("key_insights", [])]
                    parts.append(f"Stabilized Key Insights (Cycle {depth} Anchor):\n" + "\n".join(insights))
                if previous_reflection.get("remaining_gaps"):
                    gaps = [f"- {gap}" for gap in previous_reflection.get("remaining_gaps", [])]
                    parts.append("Remaining Gaps from Previous Cycle:\n" + "\n".join(gaps))
                if parts:
                    prev_refl_formatted = "\n\n".join(parts)

            user_text = prompt_data.get("user", "").format(
                objective=task["objective"],
                goal=s["plan"].get("goal", task["objective"]) if (s and s.get("plan")) else task["objective"],
                current_depth=depth,
                max_depth=task["max_depth"],
                parsed_urls=parsed_urls_text,
                accumulated_findings=accumulated_findings_text,
                previous_reflection=prev_refl_formatted,
                digest_followups=followups_text,
                digest_direct_urls=direct_urls_text,
                digest_gaps=gaps_text,
            )
            if prompt_data.get("anti_mastery"):
                user_text = self._anti_mastery(user_text)

            result = {
                "phase": "reflecting",
                "objective": task["objective"],
                "current_depth": s.get("current_depth", 0) if s else 0,
                "max_depth": task["max_depth"],
                "max_rounds": self.max_reflect_rounds,
                "findings_count": len(all_findings),
                "system_prompt": system_prompt,
                "user_prompt": user_text,
                "accumulated_findings": all_findings,
                "digest_signals": signals,
                "parsed_urls": parsed_urls_list,
                "cached_at": self._now_utc_str(),
            }
        elif phase == "evaluating":
            reflection = s["last_reflection"] if s and s.get("last_reflection") else {}
            completeness = reflection.get("completeness_score", 0)
            # Determine which path will be taken
            depth = s["current_depth"] if s else 0
            max_depth = task["max_depth"]
            stagnation = s["stagnation_counter"] if s else 0
            sat_threshold = self.satisfaction_threshold
            if depth >= max_depth:
                eval_path = "hard_stop"
                eval_path_reason = f"depth limit reached ({depth}/{max_depth})"
            elif stagnation >= 3:
                eval_path = "hard_stop"
                eval_path_reason = f"stagnation ({stagnation} steps)"
            elif completeness >= sat_threshold:
                eval_path = "hard_stop"
                eval_path_reason = f"completeness {completeness:.2f} >= threshold {sat_threshold}"
            elif completeness < 0.4:
                eval_path = "hard_continue"
                eval_path_reason = f"completeness too low ({completeness:.2f}), no LLM needed"
            else:
                eval_path = "llm_borderline"
                eval_path_reason = f"borderline ({completeness:.2f}) — LLM will decide"
            result = {
                "phase": "evaluating",
                "current_depth": depth,
                "max_depth": max_depth,
                "sources_analyzed": s["sources_analyzed"] if s else 0,
                "stagnation_counter": stagnation,
                "completeness_score": completeness,
                "satisfaction_threshold": sat_threshold,
                "eval_path": eval_path,
                "eval_path_reason": eval_path_reason,
                # consolidation context for display
                "key_insights": reflection.get("key_insights", []),
                "remaining_gaps": reflection.get("remaining_gaps", []),
                "next_queries": reflection.get("next_queries", []),
                "next_direct_urls": reflection.get("next_direct_urls", []),
                "objective": task["objective"],
                "cached_at": self._now_utc_str(),
            }
        elif phase == "synthesizing":
            # Generate prompts using current state
            prompt_data = get_prompts_dict("research/orchestrator_synthesize.yaml")
            
            # Use cached persona or build it specifically for research_synthesis
            cached = self._get_cached_phase(task_id, "synthesizing")
            if cached and cached.get("persona"):
                persona = cached["persona"]
            else:
                persona = await self._build_orchestrator_persona(task["objective"], "research_synthesis")
                
            system_prompt = persona + "\n\n" + prompt_data.get("system", "")
            if prompt_data.get("anti_mastery"):
                system_prompt = self._anti_mastery(system_prompt)
                
            # Compile findings with references
            all_findings = s.get("all_findings", []) if s else []
            sources_count = s.get("sources_analyzed", 0) if s else 0
            
            parsed_urls_list = []
            if self.step_result_repo:
                try:
                    task_results = self.step_result_repo.get_by_task(task_id)
                    seen_urls = set()
                    for r in task_results:
                        url = r.get("source_url")
                        raw_content = r.get("raw_content")
                        if url and url not in seen_urls and raw_content is not None:
                            seen_urls.add(url)
                            title = r.get("source_title") or url
                            status = self._classify_source_status(raw_content)
                            parsed_urls_list.append({"url": url, "title": title, "status": status})
                except Exception as e:
                    logger.warning("Failed to retrieve parsed URLs for synthesize preview: %s", e)

            formatted_urls, compressed_findings, _, _ = self._apply_unified_references(
                parsed_urls_list, all_findings
            )
            sources_legend_text = "\n".join(formatted_urls) or "(none)"
            accumulated_findings_text = (
                "Sources Legend:\n" + sources_legend_text + "\n\n" + "\n".join(compressed_findings)
            )

            # Format reflection / consolidation details
            reflection = s.get("last_reflection", {}) if s else {}
            prev_refl_formatted = "(none)"
            if reflection and isinstance(reflection, dict):
                parts = []
                if reflection.get("reflection"):
                    parts.append(f"Methodological Reflection:\n{reflection.get('reflection')}")
                if reflection.get("key_insights"):
                    insights = [f"- {ins}" for ins in reflection.get("key_insights", [])]
                    parts.append("Stabilized Key Insights:\n" + "\n".join(insights))
                if reflection.get("remaining_gaps"):
                    gaps = [f"- {gap}" for gap in reflection.get("remaining_gaps", [])]
                    parts.append("Remaining Gaps:\n" + "\n".join(gaps))
                if parts:
                    prev_refl_formatted = "\n\n".join(parts)

            user_text = prompt_data.get("user", "").format(
                objective=task["objective"],
                goal=s["plan"].get("goal", task["objective"]) if (s and s.get("plan")) else task["objective"],
                reflection=prev_refl_formatted,
                all_findings=accumulated_findings_text,
            )
            if prompt_data.get("anti_mastery"):
                user_text = self._anti_mastery(user_text)

            result = {
                "phase": "synthesizing",
                "objective": task["objective"],
                "findings_count": len(all_findings),
                "sources_count": sources_count,
                "system_prompt": system_prompt,
                "user_prompt": user_text,
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

    # ── State persistence ───────────────────────────────────────────

    _ORCH_STATE_KEYS = {
        "phase", "objective", "max_depth", "budget", "plan_id", "plan",
        "all_findings", "sources_analyzed", "stagnation_counter",
        "step_number", "last_reflection", "current_depth", "query_index",
        "search_results_cache", "digest_results_cache",
        "digest_signals",
        "should_stop", "stop_reason",
    }

    def _persist_state(self, task_id: str) -> None:
        """Serialise orchestrator state to research_tasks.orchestrator_state."""
        s = self._task_states.get(task_id)
        if not s:
            return
        clean = {k: v for k, v in s.items() if k in self._ORCH_STATE_KEYS}
        try:
            self.task_repo.update(task_id, orchestrator_state=json.dumps(clean, default=str, ensure_ascii=False))
        except Exception:
            logger.warning("Failed to persist orchestrator state for %s", task_id[:8], exc_info=True)

    def _load_state(self, task_id: str) -> Optional[dict]:
        """Load orchestrator state from DB. Returns None if not found."""
        task = self.task_repo.get(task_id)
        if not task or not task.get("orchestrator_state"):
            return None
        try:
            state = json.loads(task["orchestrator_state"])
            # Ensure mutable containers
            for key in ("all_findings", "search_results_cache", "parsed_sources_cache", "digest_results_cache"):
                if key not in state:
                    state[key] = []
            if "last_reflection" not in state:
                state["last_reflection"] = {}
            return state
        except Exception:
            logger.warning("Failed to load orchestrator state for %s", task_id[:8], exc_info=True)
            return None

    # ── Step record helpers ─────────────────────────────────────────

    def _create_or_update_step(self, s: dict, task_id: str, step_type: str,
                                query_group: int = 0, query_text: str = "") -> str:
        """Create a new step, or update an existing one in-place for reruns."""
        rerun_id = s.pop("_rerun_step_id", None)
        if rerun_id:
            # Update depth in step_data for the rerun step
            step_data = json.dumps({"depth": s.get("current_depth", 0)})
            self.step_repo.update(rerun_id, status="running",
                started_at=self._now_utc_str(), query_text=query_text, step_data=step_data)
            return rerun_id
        s["step_number"] += 1
        step_id = str(uuid.uuid4())
        step_data = json.dumps({"depth": s.get("current_depth", 0)})
        self.step_repo.create({
            "id": step_id, "task_id": task_id, "plan_id": s["plan_id"],
            "step_number": s["step_number"], "step_type": step_type,
            "step_data": step_data,
            "status": "running", "started_at": self._now_utc_str(),
            "query_group": query_group, "query_text": query_text,
        })
        return step_id

    def _save_llm_response_to_step_data(self, step_id: str, resp: dict) -> None:
        """Helper to save LLM response to step_data without losing existing keys like depth."""
        if not step_id or not self.step_repo:
            return
        try:
            existing = self.step_repo.get(step_id)
            existing_data = {}
            if existing and existing.get("step_data"):
                try:
                    existing_data = json.loads(existing["step_data"])
                except Exception:
                    pass
            safe_resp = resp.copy()
            if "thinking" in safe_resp and isinstance(safe_resp["thinking"], str):
                safe_resp["thinking"] = safe_resp["thinking"][:4000]
            if "content" in safe_resp and isinstance(safe_resp["content"], str):
                safe_resp["content"] = safe_resp["content"][:14000]
            existing_data["llm_response"] = safe_resp
            self.step_repo.update(step_id, step_data=json.dumps(
                existing_data, default=str, ensure_ascii=False
            ))
        except Exception:
            logger.warning("Failed to save LLM response to step %s step_data", step_id, exc_info=True)

    @staticmethod
    def _get_step_depth(step: dict) -> int:
        """Extract the cycle depth from a step's step_data JSON. Returns 0 on failure."""
        try:
            data = json.loads(step.get("step_data") or "{}")
            return int(data.get("depth", 0))
        except Exception:
            return 0

    def _delete_downstream(self, task_id: str, after_step_number: int) -> int:
        """Delete all steps with step_number > after_step_number (for rerun)."""
        if not self.step_repo:
            return 0
        return self.step_repo.delete_downstream(task_id, after_step_number)

    # ── Main step execution ───────────────────────────────────────

    async def execute_step(self, task_id: str) -> dict:
        """Execute exactly ONE phase of the research pipeline.

        Returns unified debug info: inputs, outputs, prompts, next_phase.
        Persists orchestrator_state after every step.
        """
        if task_id not in self._step_locks:
            self._step_locks[task_id] = asyncio.Lock()

        async with self._step_locks[task_id]:
            s = self._get_state(task_id)
            phase = s["phase"]

            # On rerun, delete all downstream steps starting from the beginning of the rerun phase
            rerun_id = s.get("_rerun_step_id")
            if rerun_id:
                rerun_step = self.step_repo.get(rerun_id) if self.step_repo else None
                if rerun_step:
                    # Find all steps of the same type at this phase depth to reset the phase cleanly
                    all_steps = self.step_repo.get_by_task(task_id) if self.step_repo else []
                    same_phase_steps = [
                        st for st in all_steps
                        if st["step_type"] == rerun_step["step_type"]
                        and abs(st["step_number"] - rerun_step["step_number"]) < 10
                    ]
                    min_step_num = min(st["step_number"] for st in same_phase_steps) if same_phase_steps else rerun_step["step_number"]
                    deleted = self._delete_downstream(task_id, min_step_num - 1)
                    if deleted:
                        logger.info("Rerun: deleted %d downstream steps starting from step %d — %s",
                                     deleted, min_step_num, self._log_context(task_id, "rerun"))
                    s["step_number"] = min_step_num - 1
                    s.pop("_rerun_step_id", None)

            result: dict = {
                "task_id": task_id,
                "phase": phase,
                "query_index": s.get("query_index", 0),
                "current_depth": s.get("current_depth", 0),
            }

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
                    result.update(await self._step_evaluate(task_id, s))

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
                    "message": f"Step '{phase}' failed: {e}",
                })
                self.task_repo.update(task_id, status="failed",
                    result_summary=f"Step '{phase}' failed: {e}")

            result["next_phase"] = s["phase"]
            result["accumulated_findings"] = len(s.get("all_findings", []))

            # Persist state to DB after every step
            self._persist_state(task_id)

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
            llm_resp = {"plan": plan, "depth": 0}
            self.step_repo.update(step_id, step_data=json.dumps(llm_resp, default=str, ensure_ascii=False))
        except Exception:
            pass
        self._log_meta(task_id, "orchestrator_plan", {"plan": plan}, step_id=step_id)

        s["phase"] = "searching"
        return {"plan": plan, "plan_id": plan["id"], "step_id": step_id}

    async def _step_search(self, task_id: str, s: dict) -> dict:
        """Web search for all queries of the current depth in parallel. Advance to parsing."""
        raw_queries = s["plan"].get("search_queries", [s["objective"]])
        # Use reflection-suggested queries if available
        if s["current_depth"] > 0 and s["last_reflection"].get("next_queries"):
            raw_queries = s["last_reflection"]["next_queries"]

        search_queries = []
        direct_urls = []

        # Pull from next_direct_urls if present
        if s.get("last_reflection") and isinstance(s["last_reflection"], dict):
            for u in s["last_reflection"].get("next_direct_urls", []):
                if isinstance(u, str) and (u.startswith("http://") or u.startswith("https://")):
                    if u not in direct_urls:
                        direct_urls.append(u)

        for q in raw_queries:
            if isinstance(q, str) and (q.startswith("http://") or q.startswith("https://")):
                if q not in direct_urls:
                    direct_urls.append(q)
            else:
                search_queries.append(q)

        # Limit direct URLs to 5 max
        direct_urls = direct_urls[:5]
        pending_queries = search_queries + (["Direct URL Parse Pointers"] if direct_urls else [])

        # Cache search inputs for re-use on rerun
        cache = self._load_cache(task_id)
        cache["searching"] = {
            "phase": "searching",
            "pending_queries": pending_queries,
            "query_index": 0,
            "top_n": self.default_top_n,
            "cached_at": self._now_utc_str(),
        }
        self._save_cache(task_id, cache)

        logger.info("Step: SEARCHING %d queries in parallel — %s", len(pending_queries), self._log_context(task_id, "searching"))

        # Create search steps for search queries in the DB
        group_steps = {}
        for i, q in enumerate(search_queries):
            q_group = i + 1
            step_id = self._create_or_update_step(s, task_id, "search",
                query_group=q_group, query_text=q[:300])
            group_steps[q_group] = step_id

        # Setup query group for direct URLs if present
        direct_group = len(search_queries) + 1 if direct_urls else None
        if direct_group:
            direct_label = f"Direct: {direct_urls[0][:60]}{'…' if len(direct_urls) > 1 else ''}"
            step_id = self._create_or_update_step(s, task_id, "search",
                query_group=direct_group, query_text=direct_label)
            group_steps[direct_group] = step_id

        # Run DDG searches in parallel
        tasks = [web_search(q, self.default_top_n, self._state.config) for q in search_queries]
        search_results_list = await asyncio.gather(*tasks)

        # Merge results, deduping by URL but keeping track of query_group
        search_results = []
        
        for i, results in enumerate(search_results_list):
            q_group = i + 1
            step_id = group_steps[q_group]
            
            # Log meta and update individual query step
            self._log_meta(task_id, "orchestrator_search", {
                "query": search_queries[i],
                "results_count": len(results),
            }, step_id=step_id)
            
            if not results:
                self.step_repo.update(step_id, status="completed",
                    result_summary="no results")
            else:
                self.step_repo.update(step_id, status="completed",
                    result_summary=f"{len(results)} results")
                
            for r in results:
                url = r.get("url")
                if url:
                    # Save search results to DB research_step_results table
                    if self.step_result_repo:
                        try:
                            self.step_result_repo.create({
                                "id": str(uuid.uuid4()),
                                "step_id": step_id,
                                "task_id": task_id,
                                "source_url": url,
                                "source_title": r.get("title", url[:100]),
                                "relevance_score": r.get("relevance", 0.0),
                                "novelty_score": r.get("novelty", 0.0),
                            })
                        except Exception as e:
                            logger.warning("Failed to save search step result to DB: %s", e)
                    
                    # Preserve query group info on the search result cache
                    r_copy = dict(r)
                    r_copy["query_group"] = q_group
                    search_results.append(r_copy)

        # Append direct URLs to search results so they bypass search and get parsed directly
        if direct_group and direct_urls:
            step_id = group_steps[direct_group]
            self._log_meta(task_id, "orchestrator_search", {
                "query": "direct_urls",
                "results_count": len(direct_urls),
                "urls": direct_urls,
            }, step_id=step_id)
            
            self.step_repo.update(step_id, status="completed",
                result_summary=f"{len(direct_urls)} direct URL(s) queued — bypass search")
            
            for url in direct_urls:
                if self.step_result_repo:
                    try:
                        self.step_result_repo.create({
                            "id": str(uuid.uuid4()),
                            "step_id": step_id,
                            "task_id": task_id,
                            "source_url": url,
                            "source_title": url[:100],
                            "relevance_score": 1.0,
                            "novelty_score": 1.0,
                        })
                    except Exception as e:
                        logger.warning("Failed to save direct URL result: %s", e)
                
                search_results.append({
                    "url": url,
                    "title": url[:100],
                    "query_group": direct_group,
                })

        s["search_results_cache"] = search_results
        # Clear the previous cycle's parsed/digest caches so Cycle N+1
        # never re-digests Cycle N's sources.
        s["parsed_sources_cache"] = []
        s["phase"] = "parsing"
        
        # If no search results at all
        if not search_results:
            s["phase"] = "reflecting"

        return {
            "queries": pending_queries,
            "results_count": len(search_results),
            "urls": [{"url": r.get("url", ""), "title": r.get("title", r.get("url", "")), "query_group": r.get("query_group")} for r in search_results],
        }

    async def _step_parse(self, task_id: str, s: dict) -> dict:
        """Fetch search result URLs in parallel. Advance to digesting."""
        logger.info("Step: PARSING — %s", self._log_context(task_id, "parsing"))
        
        # Determine unique query groups present in the search results cache
        search_cache = s.get("search_results_cache", [])
        query_groups = sorted(list(set(r.get("query_group", 1) for r in search_cache)))
        if not query_groups:
            query_groups = [1]

        # Create a parallel_parse step for each query group
        group_steps = {}
        for q_group in query_groups:
            step_id = self._create_or_update_step(s, task_id, "parallel_parse",
                query_group=q_group, query_text="")
            group_steps[q_group] = step_id

        # Fetch in parallel
        parsed = await self._tool_parallel_parse_grouped(
            task_id, group_steps, search_cache, s["plan_id"],
        )
        
        # Update each parallel_parse step status
        for q_group, step_id in group_steps.items():
            parsed_for_group = [p for p in parsed if p.get("query_group") == q_group]
            self.step_repo.update(step_id, status="completed",
                result_summary=f"parsed {len(parsed_for_group)} sources")

        s["parsed_sources_cache"] = parsed
        s["phase"] = "digesting" if parsed else "reflecting"

        # Cache URL list for re-use on rerun
        urls = [{"url": p["url"], "title": p.get("title", p["url"]), "query_group": p.get("query_group")} for p in parsed]
        cache = self._load_cache(task_id)
        cache["parsing"] = {"phase": "parsing", "urls": urls, "cached_at": self._now_utc_str()}
        self._save_cache(task_id, cache)

        return {
            "parsed_count": len(parsed),
            "parsed_urls": urls,
        }

    async def _step_digest(self, task_id: str, s: dict) -> dict:
        """Analyze sources via LLM. Advance to reflecting."""
        logger.info("Step: DIGESTING — %s", self._log_context(task_id, "digesting"))
        
        # Re-hydrate parsed_sources_cache if it is empty (e.g. after a resume/restart).
        # IMPORTANT: scope to current_depth only — never pull pages from previous cycles.
        if not s.get("parsed_sources_cache") and self.step_repo and self.step_result_repo:
            steps = self.step_repo.get_by_task(task_id)
            current_depth = s.get("current_depth", 0)
            # Filter parse steps to only those at the current depth level
            parse_steps = [
                st for st in steps
                if st["step_type"] == "parallel_parse" and st["status"] == "completed"
                and self._get_step_depth(st) == current_depth
            ]
            if parse_steps:
                s["parsed_sources_cache"] = []
                for ps in parse_steps:
                    db_results = self.step_result_repo.get_by_step(ps["id"])
                    for r in db_results:
                        s["parsed_sources_cache"].append({
                            "id": r["id"],
                            "url": r["source_url"],
                            "title": r["source_title"],
                            "content": r["raw_content"],
                            "query_group": ps.get("query_group", 1),
                        })

        parsed_sources = s.get("parsed_sources_cache", [])
        query_groups = sorted(list(set(src.get("query_group", 1) for src in parsed_sources)))
        if not query_groups:
            query_groups = [1]

        # Create a digest step for each query group
        group_steps = {}
        queries = s["plan"].get("search_queries", [s["objective"]])
        if s["current_depth"] > 0 and s["last_reflection"].get("next_queries"):
            queries = s["last_reflection"]["next_queries"]
            
        for q_group in query_groups:
            q_text = queries[q_group - 1] if (q_group - 1) < len(queries) else s["objective"]
            step_id = self._create_or_update_step(s, task_id, "digest",
                query_group=q_group, query_text=q_text[:300])
            group_steps[q_group] = step_id

        # Digest all sources in parallel
        digest_results = await self._tool_parallel_digest_grouped(
            task_id, group_steps, parsed_sources,
            queries, s["objective"], s["current_depth"], s["max_depth"],
        )

        # Update each digest step status
        for q_group, step_id in group_steps.items():
            digested_for_group = [dr for dr in digest_results if dr.get("query_group") == q_group]
            self.step_repo.update(step_id, status="completed",
                result_summary=f"digested {len(digested_for_group)} sources")

        # Accumulate findings and create scraped assets for metabolism and visibility
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

            # Create a scraped asset record for metabolism and frontend visibility
            if self.asset_repo:
                try:
                    if not self.asset_repo.url_exists_for_task(task_id, dr["source_url"]):
                        raw_markdown = ""
                        for src in parsed_sources:
                            if src["url"] == dr["source_url"]:
                                raw_markdown = src.get("content", "")
                                break
                        
                        self.asset_repo.create({
                            "id": str(uuid.uuid4()),
                            "branch_id": self._get_or_create_default_branch(task_id),
                            "task_id": task_id,
                            "url": dr["source_url"],
                            "raw_markdown": raw_markdown[:10000],
                            "relevance_score": r.get("relevance_score", 0.7) if isinstance(r, dict) else 0.7,
                            "novelty_score": r.get("novelty_score", 0.5) if isinstance(r, dict) else 0.5,
                            "diffractive_score": r.get("diffractive_score", 0.0) if isinstance(r, dict) else 0.0,
                        })
                except Exception as e:
                    logger.warning("Failed to create scraped asset for %s: %s", dr["source_url"][:80], e)

        if new_learnings == 0:
            s["stagnation_counter"] += 1
        else:
            s["stagnation_counter"] = 0

        # Collect digest signals (followups, direct_urls, gaps) for the reflect step.
        # Deduplicate and store in state — _tool_reflect will inject them into the prompt.
        cycle_followups: list[str] = []
        cycle_direct_urls: list[str] = []
        cycle_gaps: list[str] = []
        seen_signals: set[str] = set()
        for dr in digest_results:
            r = dr.get("result", {})
            if not isinstance(r, dict):
                continue
            source_info = dr.get("source_title") or dr.get("source_url", "")[:80]
            for item in r.get("followups", []):
                if item and item not in seen_signals:
                    seen_signals.add(item)
                    cycle_followups.append(f"[{source_info}]: {item}")
            for item in r.get("direct_urls", []):
                if item and item not in seen_signals:
                    seen_signals.add(item)
                    cycle_direct_urls.append(item)
            for item in r.get("gaps", []):
                if item and item not in seen_signals:
                    seen_signals.add(item)
                    cycle_gaps.append(f"[{source_info}]: {item}")
        s["digest_signals"] = {
            "followups": cycle_followups,
            "direct_urls": cycle_direct_urls,
            "gaps": cycle_gaps,
        }

        # We log meta here for the complete digest step block
        self._log_meta(task_id, "orchestrator_step_complete", {
            "step_number": s["step_number"],
            "new_learnings": new_learnings,
            "total_learnings": len(s["all_findings"]),
        })

        s["phase"] = "reflecting"

        # Cache digest inputs for re-use on rerun
        source_urls = [src.get("url", "") for src in parsed_sources]
        cache = self._load_cache(task_id)
        cache["digesting"] = {
            "phase": "digesting",
            "query": ", ".join(queries),
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
            "findings_summary": s["all_findings"][-20:],
        }

    async def _step_reflect(self, task_id: str, s: dict) -> dict:
        """Multi-round LLM reflection. Advance to evaluating."""
        logger.info("Step: REFLECTING — %s", self._log_context(task_id, "reflecting"))
        step_id = self._create_or_update_step(s, task_id, "reflect")

        reflection = await self._tool_reflect(
            task_id, s["objective"], s["plan"].get("goal", s["objective"]),
            s["current_depth"], s["max_depth"],
            s["all_findings"], s["last_reflection"],
            digest_signals=s.get("digest_signals", {}),
            step_id=step_id,
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

    async def _step_evaluate(self, task_id: str, s: dict) -> dict:
        """Hard checks + optional LLM decision. Advance to synthesizing or back to searching."""
        logger.info("Step: EVALUATING — %s", self._log_context(task_id, "evaluating"))
        step_id = self._create_or_update_step(s, task_id, "evaluate")

        should_stop, stop_reason = await self._tool_evaluate(
            task_id=task_id,
            step_id=step_id,
            objective=s["objective"],
            depth=s["current_depth"],
            max_depth=s["max_depth"],
            sources=s["sources_analyzed"],
            reflection=s["last_reflection"],
            stagnation=s["stagnation_counter"],
        )
        self._log_meta(task_id, "orchestrator_evaluate", {
            "decision": "stop" if should_stop else "continue",
            "reason": stop_reason,
            "depth": s["current_depth"],
            "completeness": s["last_reflection"].get("completeness_score", 0),
        }, step_id=step_id)

        self.step_repo.update(step_id, status="completed",
            result_summary=f"{'STOP' if should_stop else 'CONTINUE'}: {stop_reason}")

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
        step_id = self._create_or_update_step(s, task_id, "synthesize")

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
                gen_kwargs: dict = {
                    "temperature": prompt_data.get("temperature", 0.4),
                    "max_tokens": prompt_data.get("max_tokens", 1024),
                }
                thinking_cfg = prompt_data.get("thinking", {})
                if isinstance(thinking_cfg, dict) and thinking_cfg.get("enabled"):
                    gen_kwargs["thinking_override"] = True
                    gen_kwargs["reasoning_effort"] = thinking_cfg.get("effort", "high")
                resp = await generate_unified(llm, system_prompt=system_text, user_prompt=user_text,
                    expect_json=True, fallback_value=plan_json, **gen_kwargs)
                self._log_llm_response(task_id, "orchestrator_plan_response", resp, step_id=step_id or None)
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
            persona = await self._build_orchestrator_persona(objective, "research_synthesis")
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

        parsed_urls_list = []
        if self.step_result_repo:
            try:
                task_results = self.step_result_repo.get_by_task(task_id)
                seen_urls = set()
                for r in task_results:
                    url = r.get("source_url")
                    raw_content = r.get("raw_content")
                    if url and url not in seen_urls and raw_content is not None:
                        seen_urls.add(url)
                        title = r.get("source_title") or url
                        status = self._classify_source_status(raw_content)
                        parsed_urls_list.append({"url": url, "title": title, "status": status})
            except Exception as e:
                logger.warning("Failed to retrieve parsed URLs for synthesis: %s", e)

        formatted_urls, compressed_findings, _, _ = self._apply_unified_references(
            parsed_urls_list, all_findings
        )
        sources_legend_text = "\n".join(formatted_urls) or "(none)"
        accumulated_findings_text = (
            "Sources Legend:\n" + sources_legend_text + "\n\n" + "\n".join(compressed_findings)
        )

        # Format reflection / consolidation details
        try:
            s = self._get_state(task_id)
            reflection = s.get("last_reflection", {})
        except Exception:
            reflection = {}

        prev_refl_formatted = "(none)"
        if reflection and isinstance(reflection, dict):
            parts = []
            if reflection.get("reflection"):
                parts.append(f"Methodological Reflection:\n{reflection.get('reflection')}")
            if reflection.get("key_insights"):
                insights = [f"- {ins}" for ins in reflection.get("key_insights", [])]
                parts.append("Stabilized Key Insights:\n" + "\n".join(insights))
            if reflection.get("remaining_gaps"):
                gaps = [f"- {gap}" for gap in reflection.get("remaining_gaps", [])]
                parts.append("Remaining Gaps:\n" + "\n".join(gaps))
            if parts:
                prev_refl_formatted = "\n\n".join(parts)

        user_text = prompt_data.get("user", "").format(
            objective=objective, goal=goal,
            reflection=prev_refl_formatted,
            all_findings=accumulated_findings_text,
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
                    max_tokens=prompt_data.get("max_tokens", 4096))
                self._log_llm_response(task_id, "orchestrator_synthesize_response", resp, step_id=step_id or None)
                # Save LLM response to step_data
                if step_id:
                    self._save_llm_response_to_step_data(step_id, resp)
                result = resp.get("json_data") or resp.get("content") or {}
                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except Exception:
                        pass
                if isinstance(result, dict):
                    report = result.get("report_markdown")
                    if report:
                        return report
                    answer = result.get("answer", fallback)
                    confidence = result.get("confidence", 0)
                    return f"{answer}\n\n[confidence: {confidence:.0%}, sources: {sources_count}]"
        except Exception as e:
            logger.warning("Synthesis failed: %s", e)
        return fallback

    # ── Tools ───────────────────────────────────────────────────────

    async def _tool_parallel_parse_grouped(self, task_id, group_steps, search_results, plan_id) -> list[dict]:
        """Fetch all search result URLs in parallel, saving HTML to disk. Skips already-fetched URLs.
        Uses local DB cache lookup to avoid redundant network requests.
        """
        sem = self._get_semaphore()

        # Dedup: for each URL, check if we already have its content in the DB
        # (either from a scraped_asset record or a step_result).
        # If we do, reuse it so we avoid a redundant network fetch but still
        # pass the content into this cycle's digest step.
        new_urls = []
        reused = []
        for r in search_results:
            url = r.get("url", "")
            q_group = r.get("query_group", 1)
            step_id = group_steps.get(q_group) or (list(group_steps.values())[0] if group_steps else None)
            cached_content = None

            # Check the step_result table for existing raw_content for this URL in this task
            if self.step_result_repo:
                try:
                    task_results = self.step_result_repo.get_by_task(task_id)
                    for er in task_results:
                        if er.get("source_url") == url and er.get("raw_content") and not er["raw_content"].startswith("Error:"):
                            cached_content = er["raw_content"]
                            break
                except Exception:
                    pass

            if cached_content:
                # Content already in DB — create a new step_result row linked to THIS cycle's step_id
                logger.info("DB cache hit, reusing content for URL: %s", url[:80])
                if self.step_result_repo and step_id:
                    try:
                        result_id = str(uuid.uuid4())
                        self.step_result_repo.create({
                            "id": result_id, "step_id": step_id, "task_id": task_id,
                            "source_url": url, "source_title": r.get("title", url),
                            "raw_content": cached_content,
                            "raw_file_path": "",
                        })
                        reused.append({
                            "id": result_id, "url": url, "title": r.get("title", url),
                            "content": cached_content, "query_group": q_group,
                        })
                    except Exception as e:
                        logger.warning("Failed to create reused step_result for %s: %s", url[:80], e)
            else:
                new_urls.append(r)

        if reused:
            logger.info("Reused %d cached pages, fetching %d new URLs — %s",
                        len(reused), len(new_urls), self._log_context(task_id, "parsing"))

        # Fetch truly-new URLs in parallel
        async def fetch_one(url: str, title: str, q_group: int) -> Optional[dict]:
            step_id = group_steps.get(q_group)
            if not step_id:
                step_id = list(group_steps.values())[0]

            async with sem:
                try:
                    from backend.services.sensory_affordances import select_and_fetch, is_crawl4ai_available, fetch_via_crawl4ai
                    # Try Jina Reader first (cloud service, handles anti-bot better),
                    # then Crawl4AI as local fallback
                    content = await select_and_fetch(url_or_query=url, task_type="single_url",
                                                     config=self._state.config)
                    # If tiered gave empty content but Crawl4AI is available, try it directly
                    if not content and is_crawl4ai_available():
                        try:
                            content = await fetch_via_crawl4ai(url, config=self._state.config)
                        except RuntimeError:
                            pass
                    if not content:
                        logger.warning("All backends returned empty content for %s", url[:80])
                        if self.step_result_repo:
                            try:
                                self.step_result_repo.create({
                                    "id": str(uuid.uuid4()), "step_id": step_id, "task_id": task_id,
                                    "source_url": url, "source_title": title,
                                    "raw_content": "Error: Empty content returned from all backends",
                                    "raw_file_path": None,
                                })
                            except Exception as db_err:
                                logger.warning("Failed to save parse empty result to DB: %s", db_err)
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
                    return {"id": result_id, "url": url, "title": title, "content": content, "query_group": q_group}
                except Exception as e:
                    logger.warning("Fetch failed for %s: %s", url[:80], e)
                    if self.step_result_repo:
                        try:
                            self.step_result_repo.create({
                                "id": str(uuid.uuid4()), "step_id": step_id, "task_id": task_id,
                                "source_url": url, "source_title": title,
                                "raw_content": f"Error: Fetch failed: {str(e)[:300]}",
                                "raw_file_path": None,
                            })
                        except Exception as db_err:
                            logger.warning("Failed to save parse error result to DB: %s", db_err)
                    return None

        tasks = []
        seen_urls_in_batch = set()
        for r in new_urls:
            url = r["url"]
            if url not in seen_urls_in_batch:
                seen_urls_in_batch.add(url)
                tasks.append(fetch_one(url, r.get("title", url), r.get("query_group", 1)))

        gathered = await asyncio.gather(*tasks)
        fetched = [g for g in gathered if g is not None]
        return reused + fetched

    async def _tool_parallel_digest_grouped(self, task_id, group_steps, parsed_sources,
                                            queries, objective, depth, max_depth) -> list[dict]:
        """Analyze each parsed source concurrently via LLM, saving results under the correct step_id."""
        sem = self._get_semaphore()

        async def digest_one(source: dict) -> Optional[dict]:
            async with sem:
                try:
                    q_group = source.get("query_group", 1)
                    step_id = group_steps.get(q_group)
                    if not step_id:
                        step_id = list(group_steps.values())[0]

                    query_text = queries[q_group - 1] if (q_group - 1) < len(queries) else objective
                    
                    result = await self._analyze_source(
                        task_id, source["url"], source.get("title", ""),
                        source.get("content", ""), query_text, objective, depth, max_depth,
                        step_id=step_id,
                    )
                    # Update the step result with analysis — scope to the CURRENT step_id
                    # to avoid overwriting results from the same URL in previous cycles.
                    try:
                        parse_step_id = None
                        if self.step_repo:
                            steps = self.step_repo.get_by_task(task_id)
                            parse_step = next((s for s in steps if s.get("step_type") == "parallel_parse" and s.get("query_group") == q_group and self._get_step_depth(s) == depth), None)
                            if parse_step:
                                parse_step_id = parse_step.get("id")

                        target_step_id = parse_step_id or step_id
                        if target_step_id:
                            step_srcs = self.step_result_repo.get_by_step(target_step_id)
                        else:
                            step_srcs = self.step_result_repo.get_by_task(task_id)

                        for sr in step_srcs:
                            if sr["source_url"] == source["url"]:
                                self.step_result_repo.update_analysis(
                                    sr["id"], json.dumps(result, ensure_ascii=False),
                                )
                                break  # stop at first match within this step
                    except Exception as db_err:
                        logger.warning("Failed to update step result analysis for %s: %s", source["url"][:40], db_err)
                    return {"source_url": source["url"], "source_title": source.get("title"),
                            "result": result, "query_group": q_group}
                except Exception as e:
                    logger.warning("Digest failed for %s: %s", source.get("url", "")[:80], e)
                    return None

        tasks = [digest_one(s) for s in parsed_sources]
        gathered = await asyncio.gather(*tasks)
        return [g for g in gathered if g is not None]

    # Anti-bot / paywall / garbage patterns — skip these without LLM call
    _CONTENT_JUNK_PATTERNS: list[str] = [
        "Security check required",
        "Cloudflare",
        "Please complete the security check",
        "Enable JavaScript and cookies to continue",
    ]

    async def _analyze_source(self, task_id, url, title, content, query, goal, depth, max_depth, step_id: str = "") -> dict:
        """Analyze a single source via LLM (reuses node_analyzer prompt)."""
        # Skip obviously garbage content (anti-bot, paywalls, empty nav wrappers)
        content_stripped = (content or "").strip()
        if len(content_stripped) < 200:
            logger.info("Skipping short content (%d chars) for %s", len(content_stripped), url[:80])
            return {"learnings": [], "gaps": [f"Content too short ({len(content_stripped)} chars) — likely paywall or block"], "followups": [], "direct_urls": [], "diffractive_notes": []}
        for junk in self._CONTENT_JUNK_PATTERNS:
            if junk.lower() in content_stripped[:1000].lower():
                logger.info("Skipping junk content ('%s') for %s", junk, url[:80])
                return {"learnings": [], "gaps": [f"Blocked by anti-bot protection ('{junk}')"], "followups": [], "direct_urls": [url], "diffractive_notes": []}

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
            "system_prompt": system_text[:self._TRUNC_META_LOG],
            "user_prompt": user_text[:self._TRUNC_META_LOG],
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
            self._log_llm_response(task_id, "orchestrator_digest_response", resp, extra={
                "source_url": url,
                "learnings_count": len(result.get("learnings", [])) if isinstance(result, dict) else 0,
            }, step_id=step_id or None)
            return result if isinstance(result, dict) else fallback
        except Exception as e:
            logger.error("Source analysis failed: %s", e)
            self._log_meta(task_id, "orchestrator_digest_error", {"source_url": url, "error": str(e)}, step_id=step_id or None)
            return fallback

    async def _tool_reflect(self, task_id, objective, goal, depth, max_depth,
                             all_findings, previous_reflection,
                             digest_signals: dict = None,
                             step_id: str = "") -> dict:
        """Multi-round LLM reflection on accumulated findings.
        
        digest_signals: dict with keys followups, direct_urls, gaps — collected
        from all digest results in this cycle. Injected into prompt so the LLM
        can use concrete pointers when generating next_queries.
        """
        prompt_data = get_prompts_dict("research/orchestrator_reflect.yaml")

        # Try cache first for persona, system prompt, and user prompt (matching depth)
        cached = self._get_cached_phase(task_id, "reflecting")
        if (
            cached
            and cached.get("current_depth") == depth
            and cached.get("system_prompt")
            and cached.get("user_prompt")
        ):
            logger.info("Using cached preview prompts for reflecting phase (depth %d)", depth)
            system_text = cached["system_prompt"]
            user_text = cached["user_prompt"]
            
            self._log_meta(task_id, "orchestrator_reflect_prompt", {
                "system_prompt": system_text[:2000],
                "user_prompt": user_text[:2000],
            }, step_id=step_id or None)

            latest_result = {}
            try:
                from backend.modules.llm_client import generate_unified
                llm = getattr(self._state, "llm_provider", None)
                if llm:
                    resp = await generate_unified(llm, system_prompt=system_text, user_prompt=user_text,
                        expect_json=True,
                        fallback_value={"completeness_score": 0.5, "next_queries": [], "next_direct_urls": []},
                        temperature=prompt_data.get("temperature", 0.5),
                        max_tokens=prompt_data.get("max_tokens", 2048))
                    result = resp.get("json_data") or resp.get("content") or {}
                    if isinstance(result, str):
                        result = json.loads(result)
                    if isinstance(result, dict):
                        latest_result = result
                        self._log_llm_response(task_id, "orchestrator_reflect_response", resp, extra={
                            "completeness": result.get("completeness_score", 0),
                        }, step_id=step_id or None)
                        if step_id:
                            self._save_llm_response_to_step_data(step_id, resp)
            except Exception as e:
                logger.warning("Reflection failed with cached preview: %s", e)

            return latest_result or {"completeness_score": 0.3, "next_queries": [], "next_direct_urls": [], "reflection": "No reflection"}

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

        # Build digest signals block for prompt injection
        signals = digest_signals or {}

        parsed_urls_list = []
        if self.step_result_repo:
            try:
                task_results = self.step_result_repo.get_by_task(task_id)
                seen_urls = set()
                for r in task_results:
                    url = r.get("source_url")
                    raw_content = r.get("raw_content")
                    if url and url not in seen_urls and raw_content is not None:
                        seen_urls.add(url)
                        title = r.get("source_title") or url
                        status = self._classify_source_status(raw_content)
                        parsed_urls_list.append({"url": url, "title": title, "status": status})
            except Exception as e:
                logger.warning("Failed to retrieve parsed URLs: %s", e)

        # Extract findings of the current cycle from the DB
        current_cycle_findings = []
        if self.step_repo and self.step_result_repo:
            try:
                steps = self.step_repo.get_by_task(task_id)
                current_parse_steps = [
                    st for st in steps
                    if st.get("step_type") == "parallel_parse" and self._get_step_depth(st) == depth
                ]
                for ps in current_parse_steps:
                    db_results = self.step_result_repo.get_by_step(ps["id"])
                    for r in db_results:
                        if r.get("analyzed_json"):
                            try:
                                analysis = json.loads(r["analyzed_json"])
                                learnings = analysis.get("learnings", [])
                                title = r.get("source_title") or r.get("source_url", "")[:80]
                                for l in learnings:
                                    current_cycle_findings.append(f"[{title}]: {l}")
                            except Exception:
                                pass
            except Exception as e:
                logger.warning("Failed to retrieve current cycle findings: %s", e)

        # Fallback if DB fetch returned nothing
        if not current_cycle_findings:
            current_cycle_findings = all_findings

        # Compute historical findings
        historical_set = set(all_findings) - set(current_cycle_findings)
        historical_findings = [f for f in all_findings if f in historical_set]

        # Compress findings and extract sources map globally
        all_to_compress = current_cycle_findings + historical_findings
        formatted_urls, compressed_all, compressed_followups, compressed_gaps = self._apply_unified_references(
            parsed_urls_list,
            all_to_compress,
            signals.get("followups", []),
            signals.get("gaps", []),
        )
        
        parsed_urls_text = "\n".join(formatted_urls) or "(none)"
        compressed_current = compressed_all[:len(current_cycle_findings)]
        compressed_historical = compressed_all[len(current_cycle_findings):]

        if depth > 0:
            accumulated_findings_text = (
                f"### New Findings (Cycle {depth + 1}):\n" +
                ("\n".join(compressed_current) if compressed_current else "(none)")
            )
            if historical_findings:
                accumulated_findings_text += (
                    f"\n\n### Historical Findings (Cycle 1 to {depth}):\n" +
                    "\n".join(compressed_historical)
                )
        else:
            accumulated_findings_text = "\n".join(compressed_current)

        followups_text = "\n".join(f"- {f}" for f in compressed_followups) or "(none)"
        gaps_text = "\n".join(f"- {g}" for g in compressed_gaps) or "(none)"
        direct_urls_text = "\n".join(f"- {u}" for u in signals.get("direct_urls", [])) or "(none)"

        # Format previous_reflection as structured markdown
        prev_refl_formatted = "(none)"
        if previous_reflection and isinstance(previous_reflection, dict):
            parts = []
            if previous_reflection.get("reflection"):
                parts.append(f"Methodological Reflection (Cycle {depth}):\n{previous_reflection.get('reflection')}")
            if previous_reflection.get("key_insights"):
                insights = [f"- {ins}" for ins in previous_reflection.get("key_insights", [])]
                parts.append(f"Stabilized Key Insights (Cycle {depth} Anchor):\n" + "\n".join(insights))
            if previous_reflection.get("remaining_gaps"):
                gaps = [f"- {gap}" for gap in previous_reflection.get("remaining_gaps", [])]
                parts.append("Remaining Gaps from Previous Cycle:\n" + "\n".join(gaps))
            if parts:
                prev_refl_formatted = "\n\n".join(parts)

        user_text = prompt_data.get("user", "").format(
            objective=objective, goal=goal,
            current_depth=depth, max_depth=max_depth,
            parsed_urls=parsed_urls_text,
            accumulated_findings=accumulated_findings_text,
            previous_reflection=prev_refl_formatted,
            digest_followups=followups_text,
            digest_direct_urls=direct_urls_text,
            digest_gaps=gaps_text,
        )
        if prompt_data.get("anti_mastery"):
            user_text = self._anti_mastery(user_text)

        self._log_meta(task_id, "orchestrator_reflect_prompt", {
            "system_prompt": system_text[:2000],
            "user_prompt": user_text[:2000],
        }, step_id=step_id or None)

        latest_result = {}
        try:
            from backend.modules.llm_client import generate_unified
            llm = getattr(self._state, "llm_provider", None)
            if llm:
                resp = await generate_unified(llm, system_prompt=system_text, user_prompt=user_text,
                    expect_json=True,
                    fallback_value={"completeness_score": 0.5, "next_queries": [], "next_direct_urls": []},
                    temperature=prompt_data.get("temperature", 0.5),
                    max_tokens=prompt_data.get("max_tokens", 2048))
                result = resp.get("json_data") or resp.get("content") or {}
                if isinstance(result, str):
                    result = json.loads(result)
                if isinstance(result, dict):
                    latest_result = result
                    self._log_llm_response(task_id, "orchestrator_reflect_response", resp, extra={
                        "completeness": result.get("completeness_score", 0),
                    }, step_id=step_id or None)
                    if step_id:
                        self._save_llm_response_to_step_data(step_id, resp)
        except Exception as e:
            logger.warning("Reflection failed: %s", e)

        return latest_result or {"completeness_score": 0.3, "next_queries": [], "next_direct_urls": [], "reflection": "No reflection"}

    async def _tool_evaluate(
        self, task_id: str, step_id: str, objective: str,
        depth: int, max_depth: int, sources: int,
        reflection: dict, stagnation: int,
    ) -> tuple[bool, str]:
        """Check hard constraints first (no LLM); call LLM only in the borderline zone."""
        completeness = reflection.get("completeness_score", 0)

        # ── Hard constraints — fast, no LLM ──────────────────────────
        if depth >= max_depth:
            return True, f"depth limit reached ({depth}/{max_depth})"
        if stagnation >= 3:
            return True, f"stagnation ({stagnation} consecutive steps without new findings)"
        if completeness >= self.satisfaction_threshold:
            return True, f"satisfaction reached ({completeness:.2f} >= {self.satisfaction_threshold})"

        # ── Below borderline — continue without LLM call ──────────────
        if completeness < 0.4:
            return False, f"continuing — completeness too low ({completeness:.2f}), more depth needed"

        # ── Borderline zone (0.4 <= completeness < threshold) — LLM decides ──
        logger.info("Evaluate: borderline completeness %.2f — calling LLM evaluator", completeness)
        try:
            prompt_data = get_prompts_dict("research/orchestrator_evaluate.yaml")

            key_insights   = reflection.get("key_insights", [])
            remaining_gaps = reflection.get("remaining_gaps", [])
            next_queries   = reflection.get("next_queries", [])
            next_direct    = reflection.get("next_direct_urls", [])

            system_text = prompt_data.get("system", "")
            user_text = prompt_data.get("user", "").format(
                objective=objective,
                current_depth=depth,
                max_depth=max_depth,
                sources_analyzed=sources,
                completeness_score=f"{completeness:.2f}",
                key_insights   =  "\n".join(f"- {i}" for i in key_insights)    or "(none)",
                remaining_gaps =  "\n".join(f"- {g}" for g in remaining_gaps)  or "(none)",
                next_queries   =  "\n".join(f"- {q}" for q in next_queries)    or "(none)",
                next_direct_urls= "\n".join(f"- {u}" for u in next_direct)     or "(none)",
                depth_reached  = str(depth >= max_depth),
                stagnation_steps= stagnation,
                stagnated      = str(stagnation >= 3),
            )
            if prompt_data.get("anti_mastery"):
                system_text = self._anti_mastery(system_text)
                user_text   = self._anti_mastery(user_text)

            self._log_meta(task_id, "orchestrator_evaluate_prompt", {
                "system_prompt": system_text[:self._TRUNC_META_LOG],
                "user_prompt":   user_text[:self._TRUNC_META_LOG],
            }, step_id=step_id or None)

            from backend.modules.llm_client import generate_unified
            llm = getattr(self._state, "llm_provider", None)
            if not llm:
                raise RuntimeError("No LLM provider")

            resp = await generate_unified(
                llm,
                system_prompt=system_text,
                user_prompt=user_text,
                expect_json=True,
                fallback_value={"decision": "continue", "reason": "evaluation unavailable",
                                "completeness_assessment": completeness},
                temperature=prompt_data.get("temperature", 0.2),
                max_tokens=prompt_data.get("max_tokens", 1024),
            )
            self._log_llm_response(task_id, "orchestrator_evaluate_response", resp,
                                   step_id=step_id or None)
            if step_id:
                self._save_llm_response_to_step_data(step_id, resp)

            result = resp.get("json_data") or resp.get("content") or {}
            if isinstance(result, str):
                result = json.loads(result)
            if isinstance(result, dict):
                decision = result.get("decision", "continue").lower()
                reason   = result.get("reason", f"LLM completeness at {completeness:.2f}")
                return decision == "stop", reason

        except Exception as exc:
            logger.warning("LLM evaluate failed, defaulting to continue: %s", exc)

        return False, f"continuing (completeness {completeness:.2f} < {self.satisfaction_threshold}, LLM fallback)"

    def _classify_source_status(self, raw_content: str | None) -> str:
        if not raw_content or not raw_content.strip():
            return "empty"
        c = raw_content.strip()
        if c.startswith("Error:"):
            err = c[6:].strip().lower()
            if "timeout" in err:
                return "failed (timeout)"
            if "dns" in err or "resolve" in err:
                return "failed (dns error)"
            return f"failed ({err[:40]})"
        if len(c) < 200:
            return "too short"
        junk_patterns = ["security check required", "cloudflare", "enable javascript", "please complete the security check"]
        c_lower = c[:1000].lower()
        if any(p in c_lower for p in junk_patterns):
            return "blocked (anti-bot)"
        import re
        if re.match(r'^(skip|close|open navigation|sign in|sign up)', c[:100].strip(), re.IGNORECASE):
            return "paywall"
        return "ok"

    def _apply_unified_references(
        self, parsed_urls_list: list[dict], findings: list[str], followups: list[str] = None, gaps: list[str] = None
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        """
        Builds a unified source ID map (S1, S2, ...) from parsed_urls_list,
        then replaces the source titles in findings, followups, and gaps with [S1], [S2] etc.
        Returns:
            parsed_urls_formatted: list of formatted string lines with [S##] prefix.
            compressed_findings: list of findings with source titles replaced by [S##].
            compressed_followups: list of followups with source titles replaced by [S##].
            compressed_gaps: list of gaps with source titles replaced by [S##].
        """
        import re
        
        # If parsed_urls_list is empty (e.g. in final synthesize phase),
        # dynamically extract all source keys from the findings to build a basic list.
        if not parsed_urls_list:
            seen_srcs = []
            for f in findings:
                match = re.match(r"^\[(.*?)\]:\s*(.*)$", f)
                if match:
                    src_key = match.group(1)
                    if src_key not in seen_srcs:
                        seen_srcs.append(src_key)
            parsed_urls_list = [{"url": s, "title": s, "status": ""} for s in seen_srcs]

        # Build source mapping: title -> S##, url -> S##
        source_map = {}
        parsed_urls_formatted = []
        
        for idx, u in enumerate(parsed_urls_list, 1):
            sid = f"S{idx}"
            title = u.get("title") or u["url"]
            url = u["url"]
            status = u.get("status", "")
            
            # Map both title and url to sid for robust matching
            source_map[title] = sid
            source_map[url] = sid
            if len(title) > 80:
                source_map[title[:80]] = sid
            
            # Format: - [S1] [Title](URL) — Status
            status_suffix = f" — {status}" if status else ""
            if title and title != url:
                parsed_urls_formatted.append(f"- [{sid}] [{title}]({url}){status_suffix}")
            else:
                parsed_urls_formatted.append(f"- [{sid}] {url}{status_suffix}")

        def compress_item(item_str: str) -> str:
            # Matches pattern: ^\[(.*?)\]:\s*(.*)$
            match = re.match(r"^\[(.*?)\]:\s*(.*)$", item_str)
            if match:
                src_key = match.group(1)
                content = match.group(2)
                
                # Check for direct key match
                if src_key in source_map:
                    return f"[{source_map[src_key]}]: {content}"
                
                # Try prefix/substring match in case of minor mismatches/truncations
                for key, sid in source_map.items():
                    if src_key.startswith(key) or key.startswith(src_key):
                        return f"[{sid}]: {content}"
                        
            return item_str

        compressed_findings = [compress_item(f) for f in findings]
        compressed_followups = [compress_item(f) for f in (followups or [])]
        compressed_gaps = [compress_item(g) for g in (gaps or [])]
        
        return parsed_urls_formatted, compressed_findings, compressed_followups, compressed_gaps
