import json
import logging

from backend.services.research.steps.base import BaseResearchStep
from backend.services.research.task_state import EvaluatePayload, StepEnvelope, StepOutput
from backend.utils.prompt_loader import get_prompts_dict
from backend.utils.anti_mastery import apply_anti_mastery_filter
from backend.modules.llm_client import generate_unified

logger = logging.getLogger("aaa.research_orchestrator")


async def run_evaluation(orch, task_id: str, step_id: str, objective: str,
                         depth: int, max_depth: int, sources: int,
                         reflection: dict, stagnation: int) -> tuple[bool, str]:
    """Check hard constraints first (no LLM); call LLM only in the borderline zone.

    Migrated from legacy tools._tool_evaluate.
    """
    completeness = reflection.get("completeness_score", 0)

    # ── Hard constraints — fast, no LLM ──────────────────────────
    if depth >= max_depth:
        return True, f"depth limit reached ({depth}/{max_depth})"
    if stagnation >= 3:
        return True, f"stagnation ({stagnation} consecutive steps without new findings)"
    if completeness >= orch.satisfaction_threshold:
        return True, f"satisfaction reached ({completeness:.2f} >= {orch.satisfaction_threshold})"

    # ── Below borderline — continue without LLM call ──────────────
    if completeness < 0.4:
        return False, f"continuing — completeness too low ({completeness:.2f}), more depth needed"

    # ── Borderline zone (0.4 <= completeness < threshold) — LLM decides ──
    logger.info("Evaluate: borderline completeness %.2f — calling LLM evaluator", completeness)
    try:
        prompt_data = get_prompts_dict("research/orchestrator_evaluate.yaml")

        key_insights = reflection.get("key_insights", [])
        remaining_gaps = reflection.get("remaining_gaps", [])
        next_queries = reflection.get("next_queries", [])
        next_direct = reflection.get("next_direct_urls", [])

        system_text = prompt_data.get("system", "")
        user_text = prompt_data.get("user", "").format(
            objective=objective,
            current_depth=depth,
            max_depth=max_depth,
            sources_analyzed=sources,
            completeness_score=f"{completeness:.2f}",
            key_insights="\n".join(f"- {i}" for i in key_insights) or "(none)",
            remaining_gaps="\n".join(f"- {g}" for g in remaining_gaps) or "(none)",
            next_queries="\n".join(f"- {q}" for q in next_queries) or "(none)",
            next_direct_urls="\n".join(f"- {u}" for u in next_direct) or "(none)",
            depth_reached=str(depth >= max_depth),
            stagnation_steps=stagnation,
            stagnated=str(stagnation >= 3),
        )
        if prompt_data.get("anti_mastery"):
            system_text = apply_anti_mastery_filter(system_text)
            user_text = apply_anti_mastery_filter(user_text)

        orch._log_meta(task_id, "orchestrator_evaluate_prompt", {
            "system_prompt": system_text[:orch._TRUNC_META_LOG],
            "user_prompt": user_text[:orch._TRUNC_META_LOG],
        }, step_id=step_id or None)

        llm = getattr(orch._state, "llm_provider", None)
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
        orch._log_llm_response(task_id, "orchestrator_evaluate_response", resp,
                               step_id=step_id or None)
        if step_id:
            orch._save_llm_response_to_step_data(step_id, resp)

        result = resp.get("json_data") or resp.get("content") or {}
        if isinstance(result, str):
            result = json.loads(result)
        if isinstance(result, dict):
            decision = result.get("decision", "continue").lower()
            reason = result.get("reason", f"LLM completeness at {completeness:.2f}")
            return decision == "stop", reason

    except Exception as exc:
        logger.warning("LLM evaluate failed, defaulting to continue: %s", exc)

    return False, f"continuing (completeness {completeness:.2f} < {orch.satisfaction_threshold}, LLM fallback)"


class EvaluateStep(BaseResearchStep):
    @property
    def step_type(self) -> str:
        return "evaluate"

    async def execute(self, orch, envelope: StepEnvelope) -> StepOutput:
        task_id = envelope.task_id
        objective = envelope.objective
        current_depth = envelope.current_depth
        max_depth = envelope.max_depth

        payload: EvaluatePayload = envelope.payload

        s = orch._get_state(task_id)
        step_id = orch._create_or_update_step(s, task_id, "evaluate")

        should_stop, stop_reason = await run_evaluation(
            orch, task_id=task_id, step_id=step_id,
            objective=objective, depth=current_depth,
            max_depth=max_depth, sources=payload.sources_analyzed,
            reflection=payload.reflection, stagnation=payload.stagnation_counter,
        )

        orch._log_meta(task_id, "orchestrator_evaluate", {
            "decision": "stop" if should_stop else "continue",
            "reason": stop_reason, "depth": current_depth,
        }, step_id=step_id)

        if orch.step_repo:
            orch.step_repo.update(step_id, status="completed",
                result_summary=f"{'STOP' if should_stop else 'CONTINUE'}: {stop_reason}")

        out_payload = EvaluatePayload(
            stagnation_counter=payload.stagnation_counter,
            sources_analyzed=payload.sources_analyzed,
            reflection=payload.reflection,
            should_stop=should_stop,
            stop_reason=stop_reason
        )

        signal_flags = {"should_stop": should_stop}

        rationale = f"Evaluated research progress at depth {current_depth}: {'Synthesizing final findings' if should_stop else 'Proceeding to next depth level'} because: {stop_reason}."

        return StepOutput(
            status="completed",
            message=f"eval decision: {'stop' if should_stop else 'continue'} - {stop_reason}",
            payload=out_payload,
            signal_flags=signal_flags,
            step_ids=[step_id],
            transition_rationale=rationale
        )
