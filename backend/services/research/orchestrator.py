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
from backend.modules.structural_engine import LexiconScorer
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
from backend.services.research.steps.source_utils import classify_source_status, apply_unified_references

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
        PipelineTransition(target_phase="evaluating")
    ],
    "evaluating": [
        PipelineTransition(
            target_phase="synthesizing",
            condition=lambda out, env: out.signal_flags.get("should_stop", False)
        ),
        PipelineTransition(
            target_phase="planning",
            condition=lambda out, env: out.signal_flags.get("GLITCH_FIDELITY_LOW", False) or out.signal_flags.get("BIAS_DETECTED", False)
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
        self._lexicon = LexiconScorer()
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
        
        # Extract nested content from llm_response if present
        if "llm_response" in reflection and isinstance(reflection["llm_response"], dict):
            llm_resp = reflection["llm_response"]
            content = llm_resp.get("content") or llm_resp.get("json_data")
            if isinstance(content, str):
                try:
                    reflection = json.loads(content)
                except Exception:
                    pass
            elif isinstance(content, dict):
                reflection = content

        parts = []
        
        # Methodological notes / core reflection
        ref = reflection.get("reflection_notes") or reflection.get("reflection")
        if ref:
            prefix = f"Methodological Reflection (Cycle {depth}):\n" if include_cycle else "Methodological Reflection:\n"
            parts.append(f"{prefix}{ref}")
            
        # Key insights / findings
        insights = reflection.get("key_insights", [])
        if insights:
            prefix = f"Stabilized Key Insights (Cycle {depth} Anchor):\n" if include_cycle else "Stabilized Key Insights:\n"
            parts.append(prefix + "\n".join(f"- {ins}" for ins in insights))
            
        # Biases
        biases = reflection.get("detected_biases", [])
        if biases:
            parts.append("Detected Biases:\n" + "\n".join(f"- {b}" for b in biases))
            
        # Gaps
        gaps = reflection.get("knowledge_gaps", []) or reflection.get("remaining_gaps", [])
        if gaps:
            prefix = f"Remaining Gaps (Cycle {depth}):\n" if include_cycle else "Remaining Gaps:\n"
            parts.append(prefix + "\n".join(f"- {gap}" for gap in gaps))
            
        # Metrics
        metrics = []
        for metric_name in ("glitch_fidelity", "contradiction_density", "source_entropy", "revised_confidence"):
            if metric_name in reflection:
                val = reflection[metric_name]
                if isinstance(val, float):
                    metrics.append(f"- {metric_name.replace('_', ' ').title()}: {val:.4f}")
                else:
                    metrics.append(f"- {metric_name.replace('_', ' ').title()}: {val}")
        if metrics:
            parts.append("Cognitive Metrics:\n" + "\n".join(metrics))
            
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
                    status = classify_source_status(raw_content)
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
        state = self._state_mgr.init_task(task_id)
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

        envelope = self.reconstruct_step_input(task_id, s, phase)
        try:
            step_obj = ResearchStepRegistry.get_step(phase)
            result = await step_obj.preview(self, envelope, s)
        except Exception as e:
            logger.error("Failed to get step preview for %s: %s", phase, e)
            result = {"phase": phase, "note": f"inputs available after previous step completes ({e})"}

        # Cache and return (except placeholder notes)
        if "note" not in result:
            cache = self._load_cache(task_id)
            cache[phase] = result
            self._save_cache(task_id, cache)

        return result

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

    async def _metabolize_step(self, task_id: str, phase: str, findings: list[str]) -> None:
        """Feed research findings into the belief system for nucleation/accretion.

        Runs after each research step that produces conceptual findings.
        Computes a 16D structural signature from the findings text and feeds
        it through the belief metabolism pipeline, updating existing beliefs
        and nucleating new proto-beliefs for truly novel concepts.
        """
        if not findings:
            return

        belief_metabolism = getattr(self._state, "belief_metabolism", None)
        if not belief_metabolism:
            return

        # Only metabolize phases that produce meaningful conceptual content
        _metabolism_phases = {
            "document_digestion", "digesting", "consolidating",
            "reflection", "synthesizing",
        }
        if phase not in _metabolism_phases:
            return

        try:
            findings_text = " | ".join(findings[-10:])[:4000]
            sig_vec = self._lexicon.score(findings_text)
            source_id = f"research:{task_id[:8]}:{phase}"

            await belief_metabolism.metabolize_perception(
                conversation_id="",
                source_id=source_id,
                source_type="research_step",
                structural_signature=sig_vec,
                perturbation=1.0,
            )
            logger.info("Research metabolism: phase=%s task=%s findings=%d chars=%d",
                        phase, task_id[:8], len(findings), len(findings_text))
        except Exception as e:
            logger.error("Research metabolism failed for phase=%s task=%s: %s",
                        phase, task_id[:8], e)

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
            logger.info("execute_step: phase=%s, depth=%s, step_number=%s",
                        phase, s.get('current_depth'), s.get('step_number'))

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
                # Safety: force-complete the DB task if it's still stuck at "active"
                try:
                    db_task = self.task_repo.get(task_id)
                    if db_task and db_task.get("status") == "active":
                        logger.warning(
                            "execute_step called with phase=complete but task %s still active — "
                            "force-transitioning to completed to break stuck loop",
                            task_id[:8],
                        )
                        self.task_repo.transition_status(task_id, "completed")
                        result_summary = s.get("result_summary") or db_task.get("result_summary") or ""
                        self.task_repo.update(task_id, result_summary=result_summary)
                except Exception as e:
                    logger.warning("Failed to force-complete stuck task %s: %s", task_id[:8], e)
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

                # Metabolize research findings into belief system
                await self._metabolize_step(
                    task_id, phase, output.new_findings or []
                )

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
                    if phase == "evaluating":
                        s["query_index"] = 0
                        logger.info("Transitioning from evaluating back to planning. current_depth is %d", s["current_depth"])
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

                # Mark running steps as failed so they're visible in the UI for rerun
                if self.step_repo:
                    try:
                        all_steps = self.step_repo.get_by_task(task_id) or []
                        for st in all_steps:
                            if st["status"] == "running":
                                self.step_repo.update(st["id"], status="failed",
                                    result_summary=f"Step failed: {e}")
                    except Exception:
                        pass

                # Force phase to complete so the while-loop exits.
                # But preserve the failing phase name so the caller knows which step failed.
                s["phase"] = "complete"
                s["_failed_phase"] = phase
                result.update({
                    "status": "error",
                    "message": f"Step '{phase}' failed: {e}",
                    "failed_phase": phase,
                })
                self.task_repo.update(task_id, status="failed",
                    result_summary=f"Step '{phase}' failed: {e}")

            result["next_phase"] = s["phase"]
            result["accumulated_findings"] = len(s.get("all_findings", []))

            # Persist state to DB after every step
            self._persist_state(task_id)

            return result

    # ── Sedimentation Crystallization ──────────────────────────────────

    def _push_sedimentation_packet(self, task_id: str, phase: str,
                                    trigger_thresholds: dict,
                                    raw_context: str,
                                    proposed_node_type: str,
                                    confidence: float = 0.0) -> None:
        """Push a sedimentation packet to the task's persistent queue.

        Packets are stored in orchestrator_state and raked asynchronously
        by the daemon's consolidation cycle.
        See: docs/decisions/ADR-060-research-memory-integration.md
        """
        from backend.utils.research_logger import now_utc_str
        s = self._state_mgr.ensure_state(task_id)
        packet = {
            "phase": phase,
            "trigger_thresholds": trigger_thresholds,
            "raw_context": raw_context[:8000],
            "proposed_node_type": proposed_node_type,
            "confidence": confidence,
            "pushed_at": now_utc_str(),
        }
        s.setdefault("sedimentation_queue", []).append(packet)
        self._persist_state(task_id)
        logger.info("Sedimentation packet pushed: task=%s phase=%s type=%s",
                     task_id[:8], phase, proposed_node_type)

    def _pending_sedimentation_packets(self, task_id: str) -> list[dict]:
        """Return all unraked sedimentation packets for a task (non-destructive)."""
        s = self._state_mgr.get_state(task_id)
        return list(s.get("sedimentation_queue", []))

    def _clear_sedimentation_queue(self, task_id: str) -> int:
        """Clear all packets from the queue after successful rake. Returns count cleared."""
        s = self._state_mgr.get_state(task_id)
        count = len(s.get("sedimentation_queue", []))
        s["sedimentation_queue"] = []
        self._persist_state(task_id)
        return count


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

        max_iterations = max(s.get("max_depth", 3) * 15, 200)
        iteration_count = 0
        while s["phase"] != "complete":
            iteration_count += 1
            if iteration_count > max_iterations:
                reason = f"iteration limit exceeded ({iteration_count}/{max_iterations}) — phase stuck at: {s['phase']}"
                logger.error("Orchestrator circuit breaker: %s", reason)
                self._log_meta(task_id, "orchestrator_circuit_breaker", {
                    "iteration_count": iteration_count, "max_iterations": max_iterations,
                    "stuck_phase": s["phase"], "depth": s.get("current_depth"),
                })
                self.task_repo.transition_status(task_id, "failed")
                self.task_repo.update(task_id, result_summary=f"FAILED: {reason}")
                self._state_mgr.states.pop(task_id, None)
                return {
                    "task_id": task_id,
                    "branches_created": s.get("step_number", 0),
                    "assets_harvested": s.get("sources_analyzed", 0),
                    "lateral_flights": 0,
                    "result_summary": f"FAILED: {reason}",
                }
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

