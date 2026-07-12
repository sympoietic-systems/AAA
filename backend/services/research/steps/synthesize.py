import contextlib
import json
import logging
import re

from backend.modules.llm_client import generate_unified
from backend.services.research.steps.base import BaseResearchStep
from backend.services.research.task_state import StepEnvelope, StepOutput, SynthesizePayload
from backend.utils.anti_mastery import apply_anti_mastery_filter
from backend.utils.prompt_loader import get_prompts_dict
from backend.utils.research_logger import now_utc_str

logger = logging.getLogger("aaa.research_orchestrator")


async def run_synthesis(
    orch, task_id: str, objective: str, goal: str, all_findings: list[str], sources_count: int, step_id: str = ""
) -> str:
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

    formatted_urls, compressed_findings, _, _ = apply_unified_references(parsed_urls_list, all_findings)
    sources_legend_text = "\n".join(formatted_urls) or "(none)"
    accumulated_findings_text = "Sources Legend:\n" + sources_legend_text + "\n\n" + "\n".join(compressed_findings)

    reflections_history = []
    if orch.step_repo:
        try:
            steps = orch.step_repo.get_by_task(task_id)
            refl_steps = [
                st
                for st in steps
                if st.get("step_type") in ("reflect", "reflection") and st.get("status") == "completed"
            ]
            refl_steps.sort(key=lambda st: st.get("step_number", 0))
            for step_item in refl_steps:
                step_data = json.loads(step_item.get("step_data") or "{}")
                depth_val = step_data.get("depth", 0)
                formatted = orch._format_reflection_markdown(step_data, depth=depth_val + 1, include_cycle=True)
                if formatted and formatted != "(none)":
                    reflections_history.append(formatted)
        except Exception as e:
            logger.warning("Failed to fetch reflection steps history: %s", e)

    if reflections_history:
        prev_refl_formatted = "\n\n---\n\n".join(reflections_history)
    else:
        try:
            s = orch._get_state(task_id)
            reflection = s.get("last_reflection", {})
        except Exception:
            reflection = {}
        prev_refl_formatted = orch._format_reflection_markdown(reflection)

    user_text = prompt_data.get("user", "").format(
        objective=objective,
        goal=goal,
        reflection=prev_refl_formatted,
        all_findings=accumulated_findings_text,
    )
    if prompt_data.get("anti_mastery"):
        user_text = apply_anti_mastery_filter(user_text)

    fallback = f"Research complete. {sources_count} sources analyzed, {len(all_findings)} findings."
    try:
        llm = getattr(orch._state, "llm_provider", None)
        if llm:
            orch._log_meta(
                task_id,
                "orchestrator_synthesize_prompt",
                {
                    "system_prompt": system_text[: orch._TRUNC_META_LOG],
                    "user_prompt": user_text[: orch._TRUNC_META_LOG],
                },
                step_id=step_id or None,
            )
            resp = await generate_unified(
                llm,
                system_prompt=system_text,
                user_prompt=user_text,
                expect_json=True,
                fallback_value={"answer": fallback},
                temperature=prompt_data.get("temperature", 0.4),
                max_tokens=prompt_data.get("max_tokens", 4096),
            )
            orch._log_llm_response(task_id, "orchestrator_synthesize_response", resp, step_id=step_id or None)
            if step_id:
                orch._save_llm_response_to_step_data(step_id, resp)
            result = resp.get("json_data") or resp.get("content") or {}
            if isinstance(result, str):
                with contextlib.suppress(Exception):
                    result = json.loads(result)
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

    async def preview(self, orch, envelope: StepEnvelope, state: dict) -> dict:
        task_id = envelope.task_id
        objective = envelope.objective
        all_findings = envelope.all_findings

        goal = objective
        if state.get("plan") and isinstance(state["plan"], dict):
            goal = state["plan"].get("goal", objective)

        prompt_data = get_prompts_dict("research/orchestrator_synthesize.yaml")
        try:
            from backend.services.research.context_builder import ResearchContextBuilder

            builder = ResearchContextBuilder(orch._state)
            persona = await builder.build_synthesis_context(objective)
            system_prompt = persona + "\n\n" + prompt_data.get("system", "")
        except Exception:
            system_prompt = (
                await orch._build_orchestrator_persona(objective, "research_synthesis")
                + "\n\n"
                + prompt_data.get("system", "")
            )

        parsed_urls_list = orch._get_parsed_urls(task_id)
        from backend.services.research.steps.source_utils import apply_unified_references

        formatted_urls, compressed_findings, _, _ = apply_unified_references(parsed_urls_list, all_findings)
        sources_legend_text = "\n".join(formatted_urls) or "(none)"
        accumulated_findings_text = "Sources Legend:\n" + sources_legend_text + "\n\n" + "\n".join(compressed_findings)

        reflections_history = []
        if orch.step_repo:
            try:
                steps = orch.step_repo.get_by_task(task_id)
                refl_steps = [
                    st
                    for st in steps
                    if st.get("step_type") in ("reflect", "reflection") and st.get("status") == "completed"
                ]
                refl_steps.sort(key=lambda st: st.get("step_number", 0))
                for step_item in refl_steps:
                    step_data = json.loads(step_item.get("step_data") or "{}")
                    depth_val = step_data.get("depth", 0)
                    formatted = orch._format_reflection_markdown(step_data, depth=depth_val + 1, include_cycle=True)
                    if formatted and formatted != "(none)":
                        reflections_history.append(formatted)
            except Exception:
                pass

        if reflections_history:
            prev_refl_formatted = "\n\n---\n\n".join(reflections_history)
        else:
            reflection = state.get("last_reflection", {})
            prev_refl_formatted = orch._format_reflection_markdown(reflection)

        user_prompt = prompt_data.get("user", "").format(
            objective=objective,
            goal=goal,
            reflection=prev_refl_formatted,
            all_findings=accumulated_findings_text,
        )

        if prompt_data.get("anti_mastery"):
            system_prompt = apply_anti_mastery_filter(system_prompt)
            user_prompt = apply_anti_mastery_filter(user_prompt)

        return {
            "phase": "synthesizing",
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "model": getattr(orch._state, "llm_provider", None)
            and getattr(orch._state.llm_provider, "model_id", "(auto)")
            or "(auto)",
            "temperature": prompt_data.get("temperature", 0.4),
            "max_tokens": prompt_data.get("max_tokens", 4096),
            "cached_at": now_utc_str(),
        }

    async def execute(self, orch, envelope: StepEnvelope) -> StepOutput:
        task_id = envelope.task_id
        objective = envelope.objective
        current_depth = envelope.current_depth
        all_findings = envelope.all_findings

        payload: SynthesizePayload = envelope.payload
        sources_analyzed = payload.sources_analyzed

        s = orch._get_state(task_id)
        step_id = orch._create_or_update_step(s, task_id, "synthesize")

        orch._log_meta(
            task_id,
            "orchestrator_synthesize_start",
            {
                "total_findings": len(all_findings),
                "sources": sources_analyzed,
                "depth": current_depth,
            },
            step_id=step_id,
        )

        goal = objective
        state = orch._get_state(task_id)
        if state.get("plan") and isinstance(state["plan"], dict):
            goal = state["plan"].get("goal", objective)

        result_summary = await run_synthesis(
            orch,
            task_id,
            objective,
            goal,
            all_findings,
            sources_analyzed,
            step_id=step_id,
        )

        branch_count = state.get("phase_group", current_depth + 2)

        if orch.task_repo:
            orch.task_repo.update(
                task_id,
                branches_created=branch_count,
                assets_harvested=sources_analyzed,
                result_summary=result_summary,
            )

        if orch.step_repo:
            existing_data = {}
            try:
                existing = orch.step_repo.get(step_id)
                if existing and existing.get("step_data"):
                    existing_data = (
                        json.loads(existing["step_data"])
                        if isinstance(existing["step_data"], str)
                        else existing["step_data"]
                    )
            except Exception:
                pass
            existing_data["report_markdown"] = result_summary
            existing_data["depth"] = current_depth

            orch.step_repo.update(
                step_id,
                status="completed",
                result_summary=f"{sources_analyzed} sources, {len(all_findings)} findings",
                step_data=json.dumps(existing_data, default=str, ensure_ascii=False),
            )

        orch._log_meta(
            task_id,
            "orchestrator_complete",
            {
                "steps": branch_count,
                "sources": sources_analyzed,
                "findings": len(all_findings),
                "depth": current_depth,
            },
            step_id=step_id,
        )

        # ── Sedimentation: push concept + belief_seed packets ──
        if result_summary and sources_analyzed > 0:
            # Compute stability_delta — compare with prior cycle synthesis if exists
            try:
                from backend.modules.embedder import generate_embedding

                current_emb = generate_embedding(result_summary[:2000])
                prior_emb = None
                if orch.step_repo and current_depth > 0:
                    steps = orch.step_repo.get_by_task(task_id)
                    prior_synth_steps = [
                        st
                        for st in steps
                        if st.get("step_type") == "synthesize"
                        and st.get("status") == "completed"
                        and st.get("id") != step_id
                    ]
                    if prior_synth_steps:
                        prior_data = json.loads(prior_synth_steps[-1].get("step_data") or "{}")
                        prior_report = prior_data.get("report_markdown", "")
                        if prior_report:
                            prior_emb = generate_embedding(prior_report[:2000])
                stability_delta = 0.0
                if prior_emb is not None and current_emb is not None:
                    import numpy as np

                    cos_sim = float(
                        np.dot(current_emb, prior_emb)
                        / (np.linalg.norm(current_emb) * np.linalg.norm(prior_emb) + 1e-10)
                    )
                    stability_delta = 1.0 - cos_sim
            except Exception as e:
                logger.debug("stability_delta computation skipped: %s", e)
                stability_delta = 0.0

            if stability_delta > 0.2:
                orch._push_sedimentation_packet(
                    task_id=task_id,
                    phase="synthesize",
                    trigger_thresholds={"stability_delta": stability_delta},
                    raw_context=result_summary[:8000],
                    proposed_node_type="concept",
                    confidence=min(stability_delta * 2.0, 1.0),
                )

            # Extract confidence from result_summary for belief_seed
            conf_match = None
            with contextlib.suppress(Exception):
                conf_match = re.search(r"confidence:\s*(\d+(?:\.\d+)?)%", result_summary)
            synth_confidence = float(conf_match.group(1)) / 100.0 if conf_match else 0.0

            if synth_confidence > 0.8:
                orch._push_sedimentation_packet(
                    task_id=task_id,
                    phase="synthesize",
                    trigger_thresholds={"confidence": synth_confidence},
                    raw_context=result_summary[:8000],
                    proposed_node_type="belief_seed",
                    confidence=synth_confidence,
                )

        out_payload = SynthesizePayload(sources_analyzed=sources_analyzed, result_summary=result_summary)

        rationale = f"Synthesized findings from {sources_analyzed} sources into the final synthesis report."

        return StepOutput(
            status="completed",
            message="synthesis complete",
            payload=out_payload,
            step_ids=[step_id],
            transition_rationale=rationale,
        )
