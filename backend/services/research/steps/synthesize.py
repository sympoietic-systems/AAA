import json
import logging

from backend.services.research.steps.base import BaseResearchStep
from backend.services.research.task_state import SynthesizePayload, StepEnvelope, StepOutput
from backend.utils.prompt_loader import get_prompts_dict
from backend.utils.anti_mastery import apply_anti_mastery_filter
from backend.modules.llm_client import generate_unified
from backend.utils.research_logger import now_utc_str

logger = logging.getLogger("aaa.research_orchestrator")



async def run_synthesis(orch, task_id: str, objective: str, goal: str,
                        all_findings: list[str], sources_count: int,
                        step_id: str = "") -> str:
    """Core synthesis logic — migrated from legacy phases._phase_synthesize."""
    prompt_data = get_prompts_dict("research/orchestrator_synthesize.yaml")

    # Try cache first for persona + system prompt
    cached = orch._get_cached_phase(task_id, "synthesizing")
    if cached and cached.get("persona") and cached.get("system_prompt"):
        persona = cached["persona"]
        system_text = cached["system_prompt"]
    else:
        persona = await orch._build_orchestrator_persona(objective, "research_synthesis")
        system_text = persona + "\n\n" + prompt_data.get("system", "")
        if prompt_data.get("anti_mastery"):
            system_text = apply_anti_mastery_filter(system_text)
        cache = orch._load_cache(task_id)
        cache["synthesizing"] = {
            "phase": "synthesizing",
            "persona": persona,
            "objective": objective,
            "goal": goal,
            "system_prompt": system_text,
            "sources_count": sources_count,
            "findings_count": len(all_findings),
            "cached_at": now_utc_str(),
        }
        orch._save_cache(task_id, cache)

    parsed_urls_list = orch._get_parsed_urls(task_id)
    from backend.services.research.steps.source_utils import apply_unified_references
    formatted_urls, compressed_findings, _, _ = apply_unified_references(
        parsed_urls_list, all_findings
    )
    sources_legend_text = "\n".join(formatted_urls) or "(none)"
    accumulated_findings_text = (
        "Sources Legend:\n" + sources_legend_text + "\n\n" + "\n".join(compressed_findings)
    )

    try:
        s = orch._get_state(task_id)
        reflection = s.get("last_reflection", {})
    except Exception:
        reflection = {}

    prev_refl_formatted = orch._format_reflection_markdown(reflection)

    user_text = prompt_data.get("user", "").format(
        objective=objective, goal=goal,
        reflection=prev_refl_formatted,
        all_findings=accumulated_findings_text,
    )
    if prompt_data.get("anti_mastery"):
        user_text = apply_anti_mastery_filter(user_text)

    fallback = f"Research complete. {sources_count} sources analyzed, {len(all_findings)} findings."
    try:
        llm = getattr(orch._state, "llm_provider", None)
        if llm:
            orch._log_meta(task_id, "orchestrator_synthesize_prompt", {
                "system_prompt": system_text[:orch._TRUNC_META_LOG],
                "user_prompt": user_text[:orch._TRUNC_META_LOG],
            }, step_id=step_id or None)
            resp = await generate_unified(llm, system_prompt=system_text, user_prompt=user_text,
                expect_json=True, fallback_value={"answer": fallback},
                temperature=prompt_data.get("temperature", 0.4),
                max_tokens=prompt_data.get("max_tokens", 4096))
            orch._log_llm_response(task_id, "orchestrator_synthesize_response", resp, step_id=step_id or None)
            if step_id:
                orch._save_llm_response_to_step_data(step_id, resp)
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


class SynthesizeStep(BaseResearchStep):
    @property
    def step_type(self) -> str:
        return "synthesize"

    async def execute(self, orch, envelope: StepEnvelope) -> StepOutput:
        task_id = envelope.task_id
        objective = envelope.objective
        current_depth = envelope.current_depth
        all_findings = envelope.all_findings

        payload: SynthesizePayload = envelope.payload
        sources_analyzed = payload.sources_analyzed

        s = orch._get_state(task_id)
        step_id = orch._create_or_update_step(s, task_id, "synthesize")

        orch._log_meta(task_id, "orchestrator_synthesize_start", {
            "total_findings": len(all_findings),
            "sources": sources_analyzed,
            "depth": current_depth,
        }, step_id=step_id)

        goal = objective
        state = orch._get_state(task_id)
        if state.get("plan") and isinstance(state["plan"], dict):
            goal = state["plan"].get("goal", objective)

        result_summary = await run_synthesis(
            orch, task_id, objective, goal,
            all_findings, sources_analyzed, step_id=step_id,
        )

        step_number = state.get("step_number", current_depth + 2)

        if orch.task_repo:
            orch.task_repo.update(task_id,
                branches_created=step_number,
                assets_harvested=sources_analyzed,
                result_summary=result_summary,
            )

        if orch.step_repo:
            existing_data = {}
            try:
                existing = orch.step_repo.get(step_id)
                if existing and existing.get("step_data"):
                    existing_data = json.loads(existing["step_data"]) if isinstance(existing["step_data"], str) else existing["step_data"]
            except Exception:
                pass
            existing_data["report_markdown"] = result_summary
            existing_data["depth"] = current_depth

            orch.step_repo.update(step_id, status="completed",
                result_summary=f"{sources_analyzed} sources, {len(all_findings)} findings",
                step_data=json.dumps(existing_data, default=str, ensure_ascii=False))

        orch._log_meta(task_id, "orchestrator_complete", {
            "steps": step_number,
            "sources": sources_analyzed,
            "findings": len(all_findings),
            "depth": current_depth,
        }, step_id=step_id)

        out_payload = SynthesizePayload(
            sources_analyzed=sources_analyzed,
            result_summary=result_summary
        )

        rationale = f"Synthesized findings from {sources_analyzed} sources into the final synthesis report."

        return StepOutput(
            status="completed",
            message="synthesis complete",
            payload=out_payload,
            step_ids=[step_id],
            transition_rationale=rationale
        )
