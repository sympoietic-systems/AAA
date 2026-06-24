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

from backend.utils.research_logger import log_research_meta, now_utc_str
from backend.utils.concurrency import ensure_semaphore
from backend.utils.anti_mastery import apply_anti_mastery_filter
from backend.services.research.task_state import TaskStateManager
from backend.services.research.cache_manager import CacheManager
from backend.services.research.phases import ResearchPhases

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
        self._state_mgr = TaskStateManager(
            task_repo=app_state.research_task_repo,
            plan_repo=getattr(app_state, "research_plan_repo", None),
            step_repo=getattr(app_state, "research_step_repo", None),
            meta_log_repo=getattr(app_state, "research_meta_log_repo", None),
        )
        self._cache = CacheManager(task_repo=app_state.research_task_repo)

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
        return ensure_semaphore(self, '_semaphore', self.max_concurrent)

    @staticmethod
    def _format_reflection_markdown(reflection: dict, depth: int = 0, include_cycle: bool = False) -> str:
        if not reflection or not isinstance(reflection, dict):
            return "(none)"
        parts = []
        ref = reflection.get("reflection")
        if ref:
            prefix = f"Methodological Reflection (Cycle {depth}):\n" if include_cycle else "Methodological Reflection:\n"
            parts.append(f"{prefix}{ref}")
        insights = reflection.get("key_insights", [])
        if insights:
            prefix = f"Stabilized Key Insights (Cycle {depth} Anchor):\n" if include_cycle else "Stabilized Key Insights:\n"
            parts.append(prefix + "\n".join(f"- {ins}" for ins in insights))
        gaps = reflection.get("remaining_gaps", [])
        if gaps:
            prefix = "Remaining Gaps from Previous Cycle:\n" if include_cycle else "Remaining Gaps:\n"
            parts.append(prefix + "\n".join(f"- {gap}" for gap in gaps))
        if not parts:
            return "(none)"
        return "\n\n".join(parts)

    def _get_parsed_urls(self, task_id: str) -> list[dict]:
        result = []
        if not self.step_result_repo:
            return result
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
                    result.append({"url": url, "title": title, "status": status})
        except Exception as e:
            logger.warning("Failed to retrieve parsed URLs: %s", e)
        return result

    # ── Input cache ──────────────────────────────────────────────────

    def _load_cache(self, task_id: str) -> dict:
        return self._cache.load_cache(task_id)

    def _save_cache(self, task_id: str, cache: dict) -> None:
        self._cache.save_cache(task_id, cache)

    def _get_cached_phase(self, task_id: str, phase: str) -> Optional[dict]:
        return self._cache.get_cached_phase(task_id, phase)

    def reinitialize(self, task_id: str) -> None:
        self._cache.reinitialize(task_id)

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
        return apply_anti_mastery_filter(context)

    # ── Meta Logging ────────────────────────────────────────────────

    def _log_meta(self, task_id: str, event_type: str, data: dict, branch_id: Optional[str] = None, step_id: Optional[str] = None) -> None:
        log_research_meta(self._meta_log_repo, task_id, event_type, data, branch_id, step_id)

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
        return self._state_mgr.init_task(task_id)

    def resume_task(self, task_id: str) -> Optional[dict]:
        return self._state_mgr.resume_task(task_id)

    def set_phase(self, task_id: str, phase: str) -> None:
        self._state_mgr.set_phase(task_id, phase)

    def ensure_state(self, task_id: str) -> dict:
        return self._state_mgr.ensure_state(task_id)

    def _get_state(self, task_id: str) -> dict:
        return self._state_mgr.get_state(task_id)

    def get_task_phase(self, task_id: str) -> str:
        return self._state_mgr.get_task_phase(task_id)

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

        s = self._state_mgr.states.get(task_id)
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
                    "cached_at": now_utc_str(),
                }
            else:
                result = {"phase": "searching", "pending_queries": [task["objective"]], "query_index": 0,
                          "top_n": self.default_top_n, "cached_at": now_utc_str()}
        elif phase == "parsing":
            urls = []
            if s and s.get("search_results_cache"):
                urls = [{"url": r.get("url", ""), "title": r.get("title", r.get("url", "")), "query_group": r.get("query_group")} for r in s["search_results_cache"]]
            result = {
                "phase": "parsing",
                "urls_to_fetch": urls,
                "cached_at": now_utc_str(),
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
                            system_text = apply_anti_mastery_filter(system_text)
                            user_text = apply_anti_mastery_filter(user_text)
                            
                        try:
                            from backend.services.research.context_builder import ResearchContextBuilder
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
                "cached_at": now_utc_str(),
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
                system_prompt = apply_anti_mastery_filter(system_prompt)

            signals = s.get("digest_signals", {}) if s else {}
            followups_text = "\n".join(f"- {f}" for f in signals.get("followups", [])) or "(none)"
            direct_urls_text = "\n".join(f"- {u}" for u in signals.get("direct_urls", [])) or "(none)"
            gaps_text = "\n".join(f"- {g}" for g in signals.get("gaps", [])) or "(none)"
            all_findings = s.get("all_findings", []) if s else []

            parsed_urls_list = self._get_parsed_urls(task_id)
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
            prev_refl_formatted = self._format_reflection_markdown(previous_reflection, depth, include_cycle=True)

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
                user_text = apply_anti_mastery_filter(user_text)

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
                "cached_at": now_utc_str(),
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
                "cached_at": now_utc_str(),
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
                system_prompt = apply_anti_mastery_filter(system_prompt)
                
            # Compile findings with references
            all_findings = s.get("all_findings", []) if s else []
            sources_count = s.get("sources_analyzed", 0) if s else 0
            
            parsed_urls_list = self._get_parsed_urls(task_id)

            formatted_urls, compressed_findings, _, _ = self._apply_unified_references(
                parsed_urls_list, all_findings
            )
            sources_legend_text = "\n".join(formatted_urls) or "(none)"
            accumulated_findings_text = (
                "Sources Legend:\n" + sources_legend_text + "\n\n" + "\n".join(compressed_findings)
            )

            # Format reflection / consolidation details
            reflection = s.get("last_reflection", {}) if s else {}
            prev_refl_formatted = self._format_reflection_markdown(reflection)

            user_text = prompt_data.get("user", "").format(
                objective=task["objective"],
                goal=s["plan"].get("goal", task["objective"]) if (s and s.get("plan")) else task["objective"],
                reflection=prev_refl_formatted,
                all_findings=accumulated_findings_text,
            )
            if prompt_data.get("anti_mastery"):
                user_text = apply_anti_mastery_filter(user_text)

            result = {
                "phase": "synthesizing",
                "objective": task["objective"],
                "findings_count": len(all_findings),
                "sources_count": sources_count,
                "system_prompt": system_prompt,
                "user_prompt": user_text,
                "sources": parsed_urls_list,
                "findings": all_findings,
                "reflection": reflection,
                "cached_at": now_utc_str(),
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
            system_text = apply_anti_mastery_filter(system_text)
            user_text = apply_anti_mastery_filter(user_text)

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
            "cached_at": now_utc_str(),
        }

    # ── State persistence ───────────────────────────────────────────

    def _persist_state(self, task_id: str) -> None:
        self._state_mgr._persist_state(task_id)

    def _load_state(self, task_id: str) -> Optional[dict]:
        return self._state_mgr._load_state(task_id)

    # ── Step record helpers ─────────────────────────────────────────

    def _create_or_update_step(self, s: dict, task_id: str, step_type: str,
                                query_group: int = 0, query_text: str = "") -> str:
        """Create a new step, or update an existing one in-place for reruns."""
        rerun_id = s.pop("_rerun_step_id", None)
        if rerun_id:
            # Update depth in step_data for the rerun step
            step_data = json.dumps({"depth": s.get("current_depth", 0)})
            self.step_repo.update(rerun_id, status="running",
                started_at=now_utc_str(), query_text=query_text, step_data=step_data)
            return rerun_id
        s["step_number"] += 1
        step_id = str(uuid.uuid4())
        step_data = json.dumps({"depth": s.get("current_depth", 0)})
        self.step_repo.create({
            "id": step_id, "task_id": task_id, "plan_id": s["plan_id"],
            "step_number": s["step_number"], "step_type": step_type,
            "step_data": step_data,
            "status": "running", "started_at": now_utc_str(),
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
        if task_id not in self._state_mgr.locks:
            self._state_mgr.locks[task_id] = asyncio.Lock()

        async with self._state_mgr.locks[task_id]:
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
                        result.update(await ResearchPhases.step_plan(self, task_id, s))
                    elif phase == "searching":
                        result.update(await ResearchPhases.step_search(self, task_id, s))
                    elif phase == "parsing":
                        result.update(await ResearchPhases.step_parse(self, task_id, s))
                    elif phase == "digesting":
                        result.update(await ResearchPhases.step_digest(self, task_id, s))
                    elif phase == "reflecting":
                        result.update(await ResearchPhases.step_reflect(self, task_id, s))
                    elif phase == "evaluating":
                        result.update(await ResearchPhases.step_evaluate(self, task_id, s))
                    elif phase == "synthesizing":
                        result.update(await ResearchPhases.step_synthesize(self, task_id, s))

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
        return await ResearchPhases.step_plan(self, task_id, s)

    async def _step_search(self, task_id: str, s: dict) -> dict:
        return await ResearchPhases.step_search(self, task_id, s)

    async def _step_parse(self, task_id: str, s: dict) -> dict:
        return await ResearchPhases.step_parse(self, task_id, s)

    async def _step_digest(self, task_id: str, s: dict) -> dict:
        return await ResearchPhases.step_digest(self, task_id, s)

    async def _step_reflect(self, task_id: str, s: dict) -> dict:
        return await ResearchPhases.step_reflect(self, task_id, s)

    async def _step_evaluate(self, task_id: str, s: dict) -> dict:
        return await ResearchPhases.step_evaluate(self, task_id, s)

    async def _step_synthesize(self, task_id: str, s: dict) -> dict:
        return await ResearchPhases.step_synthesize(self, task_id, s)

    async def execute(self, task_id: str) -> dict:
        """Execute a complete research task via the orchestrator pipeline (auto mode)."""
        task = self.task_repo.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        self.init_task(task_id)
        s = self._state_mgr.states[task_id]

        logger.info("Orchestrator (auto) starting — %s: %s", self._log_context(task_id, "auto"), task.get("title", "")[:80])
        self._log_meta(task_id, "orchestrator_start", {
            "objective": s["objective"],
            "max_depth": s["max_depth"],
            "budget": s["budget"],
            "mode": "auto",
        })

        while s["phase"] != "complete":
            await self.execute_step(task_id)

        s = self._state_mgr.states.pop(task_id, {})
        return {
            "task_id": task_id,
            "branches_created": s.get("step_number", 0),
            "assets_harvested": s.get("sources_analyzed", 0),
            "lateral_flights": 0,
            "result_summary": s.get("result_summary", ""),
        }

    # ── Phase 1: PLAN ───────────────────────────────────────────────

    async def _phase_plan(self, task_id, objective, max_depth, budget,
                          previous_context: str = "", step_id: str = "") -> dict:
        from backend.services.research.phases import _phase_plan
        return await _phase_plan(self, task_id, objective, max_depth, budget,
                                 previous_context, step_id)

    async def _phase_synthesize(self, task_id, objective, goal, all_findings, sources_count, step_id: str = "") -> str:
        from backend.services.research.phases import _phase_synthesize
        return await _phase_synthesize(self, task_id, objective, goal, all_findings, sources_count, step_id)

    async def _tool_parallel_parse_grouped(self, task_id, group_steps, search_results, plan_id) -> list[dict]:
        from backend.services.research.tools import _tool_parallel_parse_grouped
        return await _tool_parallel_parse_grouped(self, task_id, group_steps, search_results, plan_id)

    async def _tool_parallel_digest_grouped(self, task_id, group_steps, parsed_sources,
                                            queries, objective, depth, max_depth) -> list[dict]:
        from backend.services.research.tools import _tool_parallel_digest_grouped
        return await _tool_parallel_digest_grouped(self, task_id, group_steps, parsed_sources, queries, objective, depth, max_depth)

    async def _analyze_source(self, task_id, url, title, content, query, goal, depth, max_depth, step_id: str = "") -> dict:
        from backend.services.research.tools import _analyze_source
        return await _analyze_source(self, task_id, url, title, content, query, goal, depth, max_depth, step_id)

    async def _tool_reflect(self, task_id, objective, goal, depth, max_depth,
                             all_findings, previous_reflection,
                             digest_signals: dict = None,
                             step_id: str = "") -> dict:
        from backend.services.research.tools import _tool_reflect
        return await _tool_reflect(self, task_id, objective, goal, depth, max_depth, all_findings, previous_reflection, digest_signals, step_id)

    async def _tool_evaluate(
        self, task_id: str, step_id: str, objective: str,
        depth: int, max_depth: int, sources: int,
        reflection: dict, stagnation: int,
    ) -> tuple[bool, str]:
        from backend.services.research.tools import _tool_evaluate
        return await _tool_evaluate(self, task_id, step_id, objective, depth, max_depth, sources, reflection, stagnation)

    def _classify_source_status(self, raw_content: str | None) -> str:
        from backend.services.research.tools import _classify_source_status
        return _classify_source_status(self, raw_content)

    def _apply_unified_references(
        self, parsed_urls_list: list[dict], findings: list[str], followups: list[str] = None, gaps: list[str] = None
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        from backend.services.research.tools import _apply_unified_references
        return _apply_unified_references(self, parsed_urls_list, findings, followups, gaps)
