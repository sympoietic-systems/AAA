import json
import logging
import uuid
from typing import List, Dict, Any, Optional

from backend.services.research.steps.base import BaseResearchStep
from backend.services.research.task_state import StepEnvelope, StepOutput, PlanPayload
from backend.utils.research_logger import now_utc_str
from backend.utils.prompt_loader import get_prompts_dict
from backend.utils.anti_mastery import apply_anti_mastery_filter
from backend.modules.llm_client import generate_unified

logger = logging.getLogger("aaa.research_orchestrator")


def _build_reflection_hints(state: dict) -> List[str]:
    """Extracts and formats all meta-cognitive reflection details (notes, traces, critique logs) into helpful context hints for the planner."""
    hints = []
    
    # 1. Refined queries
    digest_signals = state.get("digest_signals") or {}
    refined_queries = digest_signals.get("refined_queries")
    if refined_queries:
        hints.append("Refined search queries proposed by meta-reflection:\n" + "\n".join(f"- {q}" for q in refined_queries))
        
    # 2. Detected Biases, Knowledge Gaps, Signal Flags
    active_flags = []
    for key in ("detected_biases", "knowledge_gaps"):
        val = state.get(key)
        if val:
            if isinstance(val, list):
                active_flags.append(f"{key}:\n" + "\n".join(f"  - {item}" for item in val))
            else:
                active_flags.append(f"{key}: {val}")
                
    flags = state.get("signal_flags")
    if flags:
        if isinstance(flags, list):
            active_flags.append("signal_flags:\n" + "\n".join(f"  - {f}" for f in flags))
        else:
            active_flags.append(f"signal_flags: {flags}")
            
    if active_flags:
        hints.append("Active Meta-Cognitive Signal Flags:\n" + "\n".join(active_flags))
        
    # 3. Vitality & Confidence Metrics
    metrics = []
    for key in ("glitch_fidelity", "contradiction_density", "source_entropy", "revised_confidence"):
        val = state.get(key)
        if val is not None:
            metrics.append(f"- {key}: {val}")
    if metrics:
        hints.append("Vitality & Confidence Metrics:\n" + "\n".join(metrics))
        
    # 4. Epistemic Reflection Notes
    notes = state.get("reflection_notes")
    if notes:
        hints.append(f"Epistemic Reflection Notes:\n{notes}")
        
    # 5. Monologue Trace
    monologue = state.get("monologue_trace")
    if monologue and isinstance(monologue, list):
        trace_lines = []
        for entry in monologue:
            if isinstance(entry, dict):
                reg = entry.get("register") or entry.get("channel") or "unknown"
                utt = entry.get("utterance") or entry.get("content") or entry.get("thought") or ""
                if utt:
                    trace_lines.append(f"↳ [ {reg} ]\n{utt.strip()}")
        if trace_lines:
            hints.append("Agent Monologue Trace (Meta-Cognitive Flow):\n" + "\n".join(trace_lines))
            
    # 6. Critique Log (The Scar)
    critique = state.get("critique_log")
    if critique and isinstance(critique, list):
        critique_lines = []
        for item in critique:
            if isinstance(item, dict):
                reg = item.get("register") or "unknown"
                severity = item.get("severity") or "unknown"
                fail = item.get("failure_description") or ""
                sugg = item.get("suggestion") or ""
                critique_lines.append(f"- {reg} ({severity}):\n  Failure: {fail}\n  Suggestion: {sugg}")
        if critique_lines:
            hints.append("Diffractive Audit & Critique Log (The Scar):\n" + "\n".join(critique_lines))
            
    # 7. Diffractive Audit Summary
    diff_audit = state.get("diffractive_audit")
    diff_desc = state.get("diffractive_audit_description")
    if diff_audit or diff_desc:
        audit_text = f"Diffractive Audit: {diff_audit or 'N/A'}"
        if diff_desc:
            audit_text += f"\nDescription: {diff_desc}"
        hints.append(audit_text)
        
    return hints


async def run_plan_generation(orch, task_id: str, objective: str, max_depth: int, budget: float,
                          previous_context: str = "", step_id: str = "") -> dict:
    """Core plan generation logic migrated from legacy phases.py."""
    prompt_data = get_prompts_dict("research/orchestrator_planner.yaml")
    cached = orch._get_cached_phase(task_id, "planning")
    if cached and cached.get("persona") and cached.get("system_prompt") and cached.get("user_prompt"):
        persona = cached["persona"]
        system_text = cached["system_prompt"]
        user_text = cached["user_prompt"]
    else:
        # Standardized prompt construction via ResearchContextBuilder
        try:
            from backend.services.research.context_builder import ResearchContextBuilder
            builder = ResearchContextBuilder(orch._state)
            persona = await builder.build_orchestration_context(objective)
        except Exception:
            logger.warning("Failed to build orchestration context via builder, falling back to legacy persona.")
            persona = await orch._build_orchestrator_persona(objective)

        system_text = persona + "\n\n" + prompt_data.get("system", "")
        fmt = {"objective": objective, "max_depth": max_depth, "budget_limit_usd": budget}
        user_template = prompt_data.get("user", "")
        
        s = orch._get_state(task_id)
        reflection_hints = _build_reflection_hints(s)
            
        combined_context = previous_context
        if reflection_hints:
            hints_text = "\n\n### Meta-Cognitive Feedback:\n" + "\n\n".join(reflection_hints)
            combined_context = (combined_context + hints_text) if combined_context else hints_text.strip()
            
        if combined_context:
            fmt["previous_context"] = combined_context
            user_template = prompt_data.get("user_with_context", user_template)
            
        user_text = user_template.format(**fmt)
        if prompt_data.get("anti_mastery"):
            system_text = apply_anti_mastery_filter(system_text)
            user_text = apply_anti_mastery_filter(user_text)
        cache = orch._load_cache(task_id)
        cache["planning"] = {
            "phase": "planning", "persona": persona, "objective": objective,
            "max_depth": max_depth, "budget_limit_usd": budget,
            "system_prompt": system_text, "user_prompt": user_text,
            "temperature": prompt_data.get("temperature", 0.4),
            "max_tokens": prompt_data.get("max_tokens", 1024),
            "cached_at": now_utc_str(),
        }
        orch._save_cache(task_id, cache)

    plan_json = {"goal": objective, "search_queries": [objective], "n_results_per_query": 3, "estimated_depth": 1}
    try:
        llm = getattr(orch._state, "llm_provider", None)
        if llm:
            orch._log_meta(task_id, "orchestrator_plan_prompt", {
                "system_prompt": system_text[:8000], "user_prompt": user_text[:8000],
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
            orch._log_llm_response(task_id, "orchestrator_plan_response", resp, step_id=step_id or None)
            result = resp.get("json_data") or resp.get("content") or {}
            if isinstance(result, str):
                result = json.loads(result)
            if isinstance(result, dict) and result.get("search_queries"):
                config_orchestrator = orch._state.config.get("research_orchestrator") or {}
                max_queries = config_orchestrator.get("max_queries", 4)
                if len(result["search_queries"]) > max_queries:
                    logger.info("Enforcing a maximum of %d planned search queries. Truncating from %d.", max_queries, len(result["search_queries"]))
                    result["search_queries"] = result["search_queries"][:max_queries]
                plan_json = result
    except Exception as e:
        logger.warning("Plan generation failed, using default: %s", e)

    plan_id = str(uuid.uuid4())
    orch.plan_repo.create({
        "id": plan_id, "task_id": task_id,
        "plan_json": json.dumps(plan_json, ensure_ascii=False),
        "status": "active",
    })
    return {"id": plan_id, **plan_json}


class PlanStep(BaseResearchStep):
    @property
    def step_type(self) -> str:
        return "plan"

    async def preview(self, orch, envelope: StepEnvelope, state: dict) -> dict:
        task_id = envelope.task_id
        objective = envelope.objective
        max_depth = envelope.max_depth
        budget = envelope.budget

        payload: PlanPayload = envelope.payload
        previous_context = payload.previous_context or ""
        inject_file_id = payload.inject_file_id

        if inject_file_id and previous_context:
            previous_context = (
                "[Injected document will be digested against the objective "
                "in the next phase.]\n\n" + previous_context
            )

        prompt_data = get_prompts_dict("research/orchestrator_planner.yaml")

        try:
            from backend.services.research.context_builder import ResearchContextBuilder
            builder = ResearchContextBuilder(orch._state)
            persona = await builder.build_orchestration_context(objective)
        except Exception:
            logger.warning("Failed to build orchestration context via builder, falling back to legacy persona.")
            persona = await orch._build_orchestrator_persona(objective)

        system_text = persona + "\n\n" + prompt_data.get("system", "")
        fmt = {"objective": objective, "max_depth": max_depth, "budget_limit_usd": budget}
        user_template = prompt_data.get("user", "")

        reflection_hints = _build_reflection_hints(state)

        combined_context = previous_context
        if reflection_hints:
            hints_text = "\n\n### Meta-Cognitive Feedback:\n" + "\n\n".join(reflection_hints)
            combined_context = (combined_context + hints_text) if combined_context else hints_text.strip()

        if combined_context:
            fmt["previous_context"] = combined_context
            user_template = prompt_data.get("user_with_context", user_template)

        user_text = user_template.format(**fmt)
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
            "model": getattr(orch._state, "llm_provider", None) and getattr(orch._state.llm_provider, "model_id", "(auto)") or "(auto)",
            "temperature": prompt_data.get("temperature", 0.4),
            "max_tokens": prompt_data.get("max_tokens", 1024),
            "cached_at": now_utc_str(),
        }

    async def execute(self, orch, envelope: StepEnvelope) -> StepOutput:
        task_id = envelope.task_id
        objective = envelope.objective
        current_depth = envelope.current_depth
        max_depth = envelope.max_depth
        budget = envelope.budget

        payload: PlanPayload = envelope.payload
        previous_context = payload.previous_context or ""
        inject_file_id = payload.inject_file_id

        step_id = str(uuid.uuid4())

        if inject_file_id and previous_context:
            previous_context = (
                "[Injected document will be digested against the objective "
                "in the next phase.]\n\n" + previous_context
            )

        plan = await run_plan_generation(
            orch, task_id, objective, max_depth, budget,
            previous_context=previous_context, step_id=step_id
        )

        # Save to database step log
        if orch.step_repo:
            orch.step_repo.create({
                "id": step_id,
                "task_id": task_id,
                "plan_id": plan["id"],
                "step_number": envelope.current_depth + 1,  # fallback tracking
                "step_type": "plan",
                "status": "completed",
                "started_at": now_utc_str(),
                "result_summary": f"{len(plan.get('search_queries', []))} queries planned",
                "step_data": json.dumps({"plan": plan, "depth": current_depth}, default=str, ensure_ascii=False),
            })

        orch._log_meta(task_id, "orchestrator_plan", {
            "plan": plan,
            "previous_context_injected": bool(previous_context),
            "previous_context_len": len(previous_context) if previous_context else 0,
            "max_depth": max_depth,
        }, step_id=step_id)

        out_payload = PlanPayload(
            previous_context=payload.previous_context,
            inject_file_id=payload.inject_file_id,
            goal=plan.get("goal", objective),
            search_queries=plan.get("search_queries", [objective]),
            n_results_per_query=plan.get("n_results_per_query", 3),
            estimated_depth=plan.get("estimated_depth", 1)
        )

        return StepOutput(
            status="completed",
            message=f"{len(plan.get('search_queries', []))} queries planned",
            payload=out_payload,
            signal_flags={"plan_id": plan["id"]},
            step_ids=[step_id],
            transition_rationale=f"Planned {len(plan.get('search_queries', []))} search queries for depth {current_depth}."
        )
