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
from backend.services.research.task_state import (
    TaskStateManager,
    StepEnvelope,
    StepOutput,
    PlanPayload,
    SearchPayload,
    ParsePayload,
    DigestPayload,
    ConsolidatePayload,
    ReflectionPayload,
    EvaluatePayload,
    SynthesizePayload,
    DocDigestPayload,
)
from backend.services.research.cache_manager import CacheManager
from backend.services.research.steps.base import ResearchStepRegistry
import backend.services.research.steps

logger = logging.getLogger("aaa.research_orchestrator")


# ── Declarative Routing Graph ───────────────────────────────────────

class PipelineTransition:
    def __init__(self, target_phase: str, condition: Optional[Any] = None):
        self.target_phase = target_phase
        self.condition = condition or (lambda out, env: True)


PIPELINE_GRAPH = {
    "planning": [
        PipelineTransition(
            target_phase="document_digestion",
            condition=lambda out, env: env.inject_file_id is not None and not env.document_digested
        ),
        PipelineTransition(target_phase="searching")
    ],
    "document_digestion": [
        PipelineTransition(target_phase="searching")
    ],
    "searching": [
        PipelineTransition(
            target_phase="parsing",
            condition=lambda out, env: out.signal_flags.get("has_results", False)
        ),
        PipelineTransition(target_phase="consolidating")
    ],
    "parsing": [
        PipelineTransition(
            target_phase="digesting",
            condition=lambda out, env: out.signal_flags.get("has_parsed_content", False)
        ),
        PipelineTransition(target_phase="consolidating")
    ],
    "digesting": [
        PipelineTransition(target_phase="consolidating")
    ],
    "consolidating": [
        PipelineTransition(target_phase="reflection")
    ],
    "reflection": [
        PipelineTransition(
            target_phase="planning",
            condition=lambda out, env: out.signal_flags.get("GLITCH_FIDELITY_LOW", False) or out.signal_flags.get("BIAS_DETECTED", False)
        ),
        PipelineTransition(target_phase="evaluating")
    ],
    "evaluating": [
        PipelineTransition(
            target_phase="synthesizing",
            condition=lambda out, env: out.signal_flags.get("should_stop", False)
        ),
        PipelineTransition(target_phase="searching")
    ],
    "synthesizing": [
        PipelineTransition(target_phase="complete")
    ]
}

PHASE_ORDER = [
    "planning",
    "document_digestion",
    "searching",
    "parsing",
    "digesting",
    "consolidating",
    "reflection",
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
        from backend.services.research.context_builder import ResearchContextBuilder
        builder = ResearchContextBuilder(self._state)
        return await builder.build_orchestration_context(objective, context_key)

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
        import sys
        print(f">>> orchestrator.init_task CALLED for {task_id[:8]}", flush=True)
        state = self._state_mgr.init_task(task_id)
        print(f">>> orchestrator.init_task DONE: step_number={state.get('step_number')}, current_depth={state.get('current_depth')}, phase={state.get('phase')}", flush=True)
        logger.info("INIT_TASK called: task=%s step_number=%s current_depth=%s phase=%s",
                     task_id[:8], state.get("step_number"), state.get("current_depth"), state.get("phase"))
        return state

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
        elif phase == "document_digestion":
            inject_file_id = s.get("inject_file_id") if s else None
            doc_mode = s.get("document_mode", "chunks") if s else "chunks"
            chunk_limit = s.get("document_chunk_limit", 5) if s else 5
            doc_summary = ""
            doc_chunks: list[dict] = []

            if inject_file_id and s:
                conversation_id = None
                task_row = self.task_repo.get(task_id)
                if task_row:
                    conversation_id = task_row.get("conversation_id")
                effective_conv_id = s.get("inject_conversation_id") or conversation_id

                perception_repo = getattr(self._state, "perception_repo", None)
                if perception_repo and effective_conv_id:
                    try:
                        db_chunks = perception_repo.get_by_file(effective_conv_id, inject_file_id)
                        doc_chunks = [{"content": c.chunk_text, "sim": 0} for c in db_chunks if c.chunk_text]
                        file_info = perception_repo.find_file_by_name(inject_file_id)
                        if file_info and file_info.get("summary"):
                            doc_summary = f"[Document: {inject_file_id}]\n{file_info['summary']}"
                    except Exception as e:
                        logger.warning("Document chunk preview retrieval failed: %s", e)

                if doc_mode == "chunks":
                    doc_chunks = doc_chunks[:chunk_limit]

            result = {
                "phase": "document_digestion",
                "file_id": inject_file_id,
                "mode": doc_mode,
                "chunk_limit": chunk_limit if doc_mode == "chunks" else None,
                "document_digested": s.get("document_digested", False) if s else False,
                "objective": task.get("objective", ""),
                "doc_summary": doc_summary,
                "doc_chunks": doc_chunks,
                "cached_at": now_utc_str(),
            }
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
        elif phase == "consolidating":
            prompt_data = get_prompts_dict("research/orchestrator_reflect.yaml")
            system_text = prompt_data.get("system", "")
            
            # Use cached persona or build it
            cached = self._get_cached_phase(task_id, "consolidating")
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
                        if st.get("step_type") in ("parallel_parse", "document_digestion") and self._get_step_depth(st) == depth
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
                if historical_findings:
                    accumulated_findings_text += (
                        "\n\n### Digested Document/Other Findings:\n" +
                        "\n".join(compressed_historical)
                    )

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
                "phase": "consolidating",
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
        elif phase == "reflection":
            from urllib.parse import urlparse
            import math

            # Calculate Glitch Fidelity
            glitches_detected = 0
            glitches_addressed = 0
            steps = self.step_repo.get_by_task(task_id) if self.step_repo else []
            for i, step in enumerate(steps):
                if step.get("step_type") == "searching":
                    results = self.step_result_repo.get_by_step(step["id"]) if self.step_result_repo else []
                    if not results or all(not r.get("source_url") for r in results):
                        glitches_detected += 1
                        if any(st.get("step_type") == "planning" for st in steps[i+1:]):
                            glitches_addressed += 1
                elif step.get("step_type") == "parsing":
                    results = self.step_result_repo.get_by_step(step["id"]) if self.step_result_repo else []
                    for r in results:
                        raw_c = r.get("raw_content") or ""
                        if not raw_c or "error" in raw_c.lower() or raw_c.startswith("Error:"):
                            glitches_detected += 1
                            if any(st.get("step_type") in ("searching", "planning") for st in steps[i+1:]):
                                glitches_addressed += 1
                                break

            glitch_fidelity = (glitches_addressed / glitches_detected) if glitches_detected > 0 else 1.0

            # Calculate Source Entropy
            parsed_urls_list = self._get_parsed_urls(task_id)
            domains = []
            for u in parsed_urls_list:
                url_str = u.get("url") or u.get("source_url")
                if url_str:
                    try:
                        domain = urlparse(url_str).netloc
                        if domain:
                            domains.append(domain)
                    except Exception:
                        pass

            if not domains:
                source_entropy = 0.0
            else:
                counts = {}
                for d in domains:
                    counts[d] = counts.get(d, 0) + 1
                n = len(domains)
                source_entropy = -sum((count / n) * math.log2(count / n) for count in counts.values())

            # Calculate Contradiction Density
            all_findings = s.get("all_findings", []) if s else []
            contradiction_density = 0.0
            if all_findings:
                tension_keywords = ["conflict", "contradict", "disagree", "oppose", "tension", "clash", "versus", "vs", "difference"]
                matches = 0
                for f in all_findings:
                    if any(kw in f.lower() for kw in tension_keywords):
                        matches += 1
                contradiction_density = matches / len(all_findings)

            prompt_data = get_prompts_dict("research/orchestrator_reflection.yaml")
            
            # Use cached persona or build it
            cached = self._get_cached_phase(task_id, "reflection")
            if cached and cached.get("persona"):
                persona = cached["persona"]
            else:
                persona = await self._build_orchestrator_persona(task["objective"])
                
            system_prompt = persona + "\n\n" + prompt_data.get("system", "")
            if prompt_data.get("anti_mastery"):
                system_prompt = apply_anti_mastery_filter(system_prompt)

            depth = s.get("current_depth", 0) if s else 0

            # Format visited urls list
            formatted_urls = []
            for i, u in enumerate(parsed_urls_list):
                url_str = u.get("url") or u.get("source_url") or ""
                title = u.get("title") or u.get("source_title") or f"Source {i+1}"
                formatted_urls.append(f"- [{title}]({url_str})")
            parsed_urls_text = "\n".join(formatted_urls) or "(none)"

            # Format findings list
            accumulated_findings_text = "\n".join(f"- {f}" for f in all_findings) or "(none)"

            user_text = prompt_data.get("user", "").format(
                objective=task["objective"],
                current_depth=depth,
                max_depth=task["max_depth"],
                parsed_urls=parsed_urls_text,
                accumulated_findings=accumulated_findings_text,
                glitch_fidelity=f"{glitch_fidelity:.2f}",
                contradiction_density=f"{contradiction_density:.2f}",
                source_entropy=f"{source_entropy:.2f}"
            )
            if prompt_data.get("anti_mastery"):
                user_text = apply_anti_mastery_filter(user_text)

            result = {
                "phase": "reflection",
                "objective": task["objective"],
                "current_depth": depth,
                "max_depth": task["max_depth"],
                "glitch_fidelity": glitch_fidelity,
                "contradiction_density": contradiction_density,
                "source_entropy": source_entropy,
                "system_prompt": system_prompt,
                "user_prompt": user_text,
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

    def _delete_downstream(self, task_id: str, after_step_number: int, exclude_types: tuple[str, ...] = ()) -> int:
        """Delete all steps with step_number > after_step_number (for rerun)."""
        if not self.step_repo:
            return 0
        return self.step_repo.delete_downstream(task_id, after_step_number, exclude_types)

    # ── Input/Output reconstruction and mapping ────────────────────

    def reconstruct_step_input(self, task_id: str, task_state: dict, phase: str) -> StepEnvelope:
        """Constructs the clean, typed StepEnvelope for the current phase using task state."""
        envelope_data = {
            "task_id": task_id,
            "objective": task_state["objective"],
            "current_depth": task_state.get("current_depth", 0),
            "max_depth": task_state.get("max_depth", 3),
            "budget": task_state.get("budget", 0.50),
            "all_findings": task_state.get("all_findings") or [],
            "digest_signals": task_state.get("digest_signals") or {},
            "inject_file_id": task_state.get("inject_file_id"),
            "document_digested": task_state.get("document_digested", False),
            "plan_id": task_state.get("plan_id"),
        }

        # Build step-specific payload
        if phase == "planning":
            payload = PlanPayload(
                previous_context=task_state.get("previous_context"),
                inject_file_id=task_state.get("inject_file_id")
            )
        elif phase == "document_digestion":
            payload = DocDigestPayload(
                inject_file_id=task_state.get("inject_file_id") or "",
                inject_conversation_id=task_state.get("inject_conversation_id"),
                document_mode=task_state.get("document_mode", "chunks"),
                document_chunk_limit=task_state.get("document_chunk_limit", 5)
            )
        elif phase == "searching":
            plan_queries = []
            if task_state.get("plan") and isinstance(task_state["plan"], dict):
                plan_queries = task_state["plan"].get("search_queries", [task_state["objective"]])

            last_refl = task_state.get("last_reflection") or {}
            queries = last_refl.get("next_queries") if (task_state.get("current_depth", 0) > 0 and last_refl.get("next_queries")) else plan_queries
            direct_urls = last_refl.get("next_direct_urls", []) if task_state.get("current_depth", 0) > 0 else []

            payload = SearchPayload(queries=queries, direct_urls=direct_urls)
        elif phase == "parsing":
            search_results = task_state.get("search_results_cache") or []
            payload = ParsePayload(search_results_cache=search_results)
        elif phase == "digesting":
            parsed_sources = task_state.get("parsed_sources_cache") or []
            payload = DigestPayload(parsed_sources_cache=parsed_sources)
        elif phase == "consolidating":
            payload = ConsolidatePayload(last_reflection=task_state.get("last_reflection") or {})
        elif phase == "reflection":
            payload = ReflectionPayload(
                reflection_notes=task_state.get("reflection_notes", ""),
                detected_biases=task_state.get("detected_biases", []),
                knowledge_gaps=task_state.get("knowledge_gaps", []),
                glitch_fidelity=task_state.get("glitch_fidelity", 1.0),
                contradiction_density=task_state.get("contradiction_density", 0.0),
                source_entropy=task_state.get("source_entropy", 0.0),
                signal_flags=task_state.get("signal_flags", []),
                refined_queries=task_state.get("refined_queries", []),
                revised_confidence=task_state.get("revised_confidence", 0.5),
                monologue_trace=task_state.get("monologue_trace", [])
            )
        elif phase == "evaluating":
            payload = EvaluatePayload(
                stagnation_counter=task_state.get("stagnation_counter", 0),
                sources_analyzed=task_state.get("sources_analyzed", 0),
                reflection=task_state.get("last_reflection") or {}
            )
        elif phase == "synthesizing":
            payload = SynthesizePayload(sources_analyzed=task_state.get("sources_analyzed", 0))
        else:
            raise ValueError(f"Unknown phase payload reconstruction: {phase}")

        return StepEnvelope(payload=payload, **envelope_data)

    def apply_step_output(self, task_state: dict, phase: str, output: StepOutput) -> None:
        """Applies a StepOutput's payload back to the legacy task state dictionary."""
        payload = output.payload
        if phase == "planning" and isinstance(payload, PlanPayload):
            task_state["plan"] = {
                "goal": payload.goal or task_state["objective"],
                "search_queries": payload.search_queries,
                "n_results_per_query": payload.n_results_per_query,
                "estimated_depth": payload.estimated_depth,
            }
            if output.signal_flags.get("plan_id"):
                task_state["plan_id"] = output.signal_flags["plan_id"]
        elif phase == "document_digestion" and isinstance(payload, DocDigestPayload):
            task_state["document_digested"] = True
            task_state["document_learnings"] = payload.learnings
            # Merge digest signals
            existing_signals = task_state.get("digest_signals") or {}
            task_state["digest_signals"] = {
                "followups": (existing_signals.get("followups") or []) + payload.followups,
                "direct_urls": existing_signals.get("direct_urls") or [],
                "gaps": (existing_signals.get("gaps") or []) + payload.gaps,
            }
            task_state["sources_analyzed"] = task_state.get("sources_analyzed", 0) + 1
        elif phase == "searching" and isinstance(payload, SearchPayload):
            task_state["search_results_cache"] = payload.search_results
            task_state["parsed_sources_cache"] = []
        elif phase == "parsing" and isinstance(payload, ParsePayload):
            task_state["parsed_sources_cache"] = payload.parsed_sources
        elif phase == "digesting" and isinstance(payload, DigestPayload):
            task_state["sources_analyzed"] = task_state.get("sources_analyzed", 0) + len(payload.parsed_sources_cache)
            if not payload.learnings:
                task_state["stagnation_counter"] = task_state.get("stagnation_counter", 0) + 1
            else:
                task_state["stagnation_counter"] = 0
            # Merge followups/gaps
            task_state["digest_signals"] = {
                "followups": payload.followups,
                "direct_urls": [],
                "gaps": payload.gaps,
            }
        elif phase == "consolidating" and isinstance(payload, ConsolidatePayload):
            task_state["last_reflection"] = {
                "completeness_score": payload.completeness_score,
                "key_insights": payload.key_insights,
                "remaining_gaps": payload.remaining_gaps,
                "next_queries": payload.next_queries,
                "next_direct_urls": payload.next_direct_urls,
            }
        elif phase == "reflection" and isinstance(payload, ReflectionPayload):
            task_state["reflection_notes"] = payload.reflection_notes
            task_state["detected_biases"] = payload.detected_biases
            task_state["knowledge_gaps"] = payload.knowledge_gaps
            task_state["glitch_fidelity"] = payload.glitch_fidelity
            task_state["contradiction_density"] = payload.contradiction_density
            task_state["source_entropy"] = payload.source_entropy
            task_state["signal_flags"] = payload.signal_flags
            task_state["refined_queries"] = payload.refined_queries
            task_state["revised_confidence"] = payload.revised_confidence
            task_state["monologue_trace"] = payload.monologue_trace
        elif phase == "evaluating" and isinstance(payload, EvaluatePayload):
            task_state["should_stop"] = payload.should_stop
            task_state["stop_reason"] = payload.stop_reason
            if not payload.should_stop:
                task_state["current_depth"] = task_state.get("current_depth", 0) + 1
                task_state["query_index"] = 0
        elif phase == "synthesizing" and isinstance(payload, SynthesizePayload):
            # Persist result_summary into state so auto-mode execute() can retrieve it
            task_state["result_summary"] = payload.result_summary

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
            import sys
            print(f">>> execute_step: phase={phase}, depth={s.get('current_depth')}, step_number={s.get('step_number')}", flush=True)

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
                    deleted = self._delete_downstream(task_id, min_step_num - 1, exclude_types=("document_digestion",))
                    if deleted:
                        logger.info("Rerun: deleted %d downstream steps starting from step %d — %s",
                                     deleted, min_step_num, self._log_context(task_id, "rerun"))
                    s["step_number"] = min_step_num - 1

            if phase == "complete":
                return {
                    "task_id": task_id,
                    "phase": phase,
                    "message": "already complete",
                    "next_phase": "complete"
                }

            # 1. Reconstruct clean typed StepEnvelope
            envelope = self.reconstruct_step_input(task_id, s, phase)

            result: dict = {
                "task_id": task_id,
                "phase": phase,
                "query_index": s.get("query_index", 0),
                "current_depth": s.get("current_depth", 0),
            }

            try:
                # 2. Retrieve step from ResearchStepRegistry and execute
                step_processor = ResearchStepRegistry.get_step(phase)
                logger.info("Executing modular step: %s", phase)
                output: StepOutput = await step_processor.execute(self, envelope)

                s["step_number"] += 1

                # Merge findings
                if output.new_findings:
                    s["all_findings"].extend(output.new_findings)

                # Apply output payloads back to legacy task state dict
                self.apply_step_output(s, phase, output)

                result.update({
                    "status": output.status,
                    "message": output.message,
                })
                if hasattr(output.payload, "result_summary") and getattr(output.payload, "result_summary"):
                    result["result_summary"] = getattr(output.payload, "result_summary")

                # Determine next phase via Declarative Membrane (PIPELINE_GRAPH)
                next_phase = "complete"
                for transition in PIPELINE_GRAPH.get(phase, []):
                    if transition.condition(output, envelope):
                        next_phase = transition.target_phase
                        break
                s["phase"] = next_phase

                if next_phase == "planning":
                    try:
                        cache = self._load_cache(task_id)
                        if "planning" in cache:
                            del cache["planning"]
                            self._save_cache(task_id, cache)
                            logger.info("Cleared planning cache for task %s to force fresh replan.", task_id[:8])
                    except Exception as e:
                        logger.warning("Failed to clear planning cache for task %s: %s", task_id[:8], e)

                # Save transition rationale and next phase to step_data JSON
                if self.step_repo and hasattr(output, "step_ids") and output.step_ids:
                    rationale = getattr(output, "transition_rationale", None) or f"Transitioning from {phase} to {next_phase}."
                    for sid in output.step_ids:
                        try:
                            db_step = self.step_repo.get(sid)
                            if db_step:
                                step_data = {}
                                if db_step.get("step_data"):
                                    try:
                                        step_data = json.loads(db_step["step_data"]) if isinstance(db_step["step_data"], str) else db_step["step_data"]
                                    except Exception:
                                        pass
                                step_data["transition_rationale"] = rationale
                                step_data["next_phase"] = next_phase
                                self.step_repo.update(sid, step_data=json.dumps(step_data, default=str, ensure_ascii=False))
                        except Exception as ex:
                            logger.warning("Failed to update transition rationale for step %s: %s", sid, ex)

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
        # result_summary is written directly to the DB by SynthesizeStep;
        # read it back from DB so the auto-mode caller gets the real content.
        result_summary = s.get("result_summary", "")
        if not result_summary:
            fresh = self.task_repo.get(task_id)
            result_summary = (fresh or {}).get("result_summary", "") or ""
        return {
            "task_id": task_id,
            "branches_created": s.get("step_number", 0),
            "assets_harvested": s.get("sources_analyzed", 0),
            "lateral_flights": 0,
            "result_summary": result_summary,
        }

    # ── Phase 1: PLAN ───────────────────────────────────────────────

    async def _phase_plan(self, task_id, objective, max_depth, budget,
                          previous_context: str = "", step_id: str = "") -> dict:
        from backend.services.research.steps.plan import run_plan_generation
        return await run_plan_generation(self, task_id, objective, max_depth, budget,
                                         previous_context, step_id)

    async def _tool_reflection(self, orch, task_id, objective, depth, max_depth,
                               all_findings, digest_signals: dict = None,
                               step_id: str = "") -> dict:
        from backend.services.research.steps.reflect import run_deep_reflection
        return await run_deep_reflection(self, task_id, objective, depth, max_depth, all_findings, digest_signals, step_id)


    async def _phase_synthesize(self, task_id, objective, goal, all_findings, sources_count, step_id: str = "") -> str:
        from backend.services.research.steps.synthesize import run_synthesis
        return await run_synthesis(self, task_id, objective, goal, all_findings, sources_count, step_id)

    async def _tool_parallel_parse_grouped(self, task_id, group_steps, search_results, plan_id) -> list[dict]:
        from backend.services.research.steps.parse_helper import parallel_parse_grouped
        return await parallel_parse_grouped(self, task_id, group_steps, search_results, plan_id)

    async def _tool_parallel_digest_grouped(self, task_id, group_steps, parsed_sources,
                                            queries, objective, depth, max_depth) -> list[dict]:
        from backend.services.research.steps.digest_helper import parallel_digest_grouped
        return await parallel_digest_grouped(self, task_id, group_steps, parsed_sources, queries, objective, depth, max_depth)

    async def _analyze_source(self, task_id, url, title, content, query, goal, depth, max_depth, step_id: str = "") -> dict:
        from backend.services.research.steps.digest_helper import analyze_source_content
        return await analyze_source_content(self, task_id, url, title, content, query, goal, depth, max_depth, step_id)

    async def _tool_reflect(self, task_id, objective, goal, depth, max_depth,
                             all_findings, previous_reflection,
                             digest_signals: dict = None,
                             step_id: str = "") -> dict:
        from backend.services.research.steps.consolidate import run_consolidation
        return await run_consolidation(self, task_id, objective, goal, depth, max_depth, all_findings, previous_reflection, digest_signals, step_id)

    async def _tool_evaluate(
        self, task_id: str, step_id: str, objective: str,
        depth: int, max_depth: int, sources: int,
        reflection: dict, stagnation: int,
    ) -> tuple[bool, str]:
        from backend.services.research.steps.evaluate import run_evaluation
        return await run_evaluation(self, task_id, step_id, objective, depth, max_depth, sources, reflection, stagnation)

    def _classify_source_status(self, raw_content: str | None) -> str:
        from backend.services.research.steps.source_utils import classify_source_status
        return classify_source_status(raw_content)

    def _apply_unified_references(
        self, parsed_urls_list: list[dict], findings: list[str], followups: list[str] = None, gaps: list[str] = None
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        from backend.services.research.steps.source_utils import apply_unified_references
        return apply_unified_references(parsed_urls_list, findings, followups, gaps)
