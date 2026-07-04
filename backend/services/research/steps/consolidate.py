import json
import logging

from backend.services.research.steps.base import BaseResearchStep
from backend.services.research.task_state import ConsolidatePayload, StepEnvelope, StepOutput
from backend.utils.prompt_loader import get_prompts_dict
from backend.utils.anti_mastery import apply_anti_mastery_filter
from backend.modules.llm_client import generate_unified
from backend.utils.research_logger import now_utc_str

logger = logging.getLogger("aaa.research_orchestrator")


async def run_consolidation(orch, task_id: str, objective: str, goal: str,
                            depth: int, max_depth: int, all_findings: list[str],
                            previous_reflection: dict, digest_signals: dict = None,
                            step_id: str = "") -> dict:
    """Multi-round LLM reflection on accumulated findings.

    Migrated from legacy tools._tool_reflect.
    digest_signals: dict with keys followups, direct_urls, gaps — from digest results.
    """
    from backend.services.research.steps.source_utils import apply_unified_references

    prompt_data = get_prompts_dict("research/orchestrator_reflect.yaml")

    # Try cache first for persona, system prompt, and user prompt (matching depth)
    cached = orch._get_cached_phase(task_id, "consolidating")
    if (
        cached
        and cached.get("current_depth") == depth
        and cached.get("system_prompt")
        and cached.get("user_prompt")
    ):
        logger.info("Using cached preview prompts for consolidating phase (depth %d)", depth)
        system_text = cached["system_prompt"]
        user_text = cached["user_prompt"]

        orch._log_meta(task_id, "orchestrator_reflect_prompt", {
            "system_prompt": system_text[:2000],
            "user_prompt": user_text[:2000],
        }, step_id=step_id or None)

        latest_result = {}
        try:
            llm = getattr(orch._state, "llm_provider", None)
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
                    orch._log_llm_response(task_id, "orchestrator_reflect_response", resp, extra={
                        "completeness": result.get("completeness_score", 0),
                    }, step_id=step_id or None)
                    if step_id:
                        orch._save_llm_response_to_step_data(step_id, resp)
        except Exception as e:
            logger.warning("Reflection failed with cached preview: %s", e)

        return latest_result or {"completeness_score": 0.3, "next_queries": [], "next_direct_urls": [], "reflection": "No reflection"}

    if cached and cached.get("persona") and cached.get("system_prompt"):
        persona = cached["persona"]
        system_text = cached["system_prompt"]
    else:
        persona = await orch._build_orchestrator_persona(objective)
        system_text = persona + "\n\n" + prompt_data.get("system", "")
        if prompt_data.get("anti_mastery"):
            system_text = apply_anti_mastery_filter(system_text)
        cache = orch._load_cache(task_id)
        cache["consolidating"] = {
            "phase": "consolidating",
            "persona": persona,
            "objective": objective,
            "goal": goal,
            "system_prompt": system_text,
            "cached_at": now_utc_str(),
        }
        orch._save_cache(task_id, cache)

    signals = digest_signals or {}
    parsed_urls_list = orch._get_parsed_urls(task_id)

    # Extract findings from the current cycle via DB
    current_cycle_findings = []
    if orch.step_repo and orch.step_result_repo:
        try:
            steps = orch.step_repo.get_by_task(task_id)
            current_parse_steps = [
                st for st in steps
                if st.get("step_type") in ("parallel_parse", "document_digestion")
                and orch._get_step_depth(st) == depth
            ]
            for ps in current_parse_steps:
                db_results = orch.step_result_repo.get_by_step(ps["id"])
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

    if not current_cycle_findings:
        current_cycle_findings = all_findings

    historical_set = set(all_findings) - set(current_cycle_findings)
    historical_findings = [f for f in all_findings if f in historical_set]

    all_to_compress = current_cycle_findings + historical_findings
    formatted_urls, compressed_all, compressed_followups, compressed_gaps = apply_unified_references(
        parsed_urls_list, all_to_compress,
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

    prev_refl_formatted = orch._format_reflection_markdown(previous_reflection, depth, include_cycle=True)

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
        user_text = apply_anti_mastery_filter(user_text)

    orch._log_meta(task_id, "orchestrator_reflect_prompt", {
        "system_prompt": system_text[:2000],
        "user_prompt": user_text[:2000],
    }, step_id=step_id or None)

    latest_result = {}
    try:
        llm = getattr(orch._state, "llm_provider", None)
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
                orch._log_llm_response(task_id, "orchestrator_reflect_response", resp, extra={
                    "completeness": result.get("completeness_score", 0),
                }, step_id=step_id or None)
                if step_id:
                    orch._save_llm_response_to_step_data(step_id, resp)
    except Exception as e:
        logger.warning("Reflection failed: %s", e)

    return latest_result or {"completeness_score": 0.3, "next_queries": [], "next_direct_urls": [], "reflection": "No reflection"}


class ConsolidateStep(BaseResearchStep):
    @property
    def step_type(self) -> str:
        return "reflect"

    async def preview(self, orch, envelope: StepEnvelope, state: dict) -> dict:
        task_id = envelope.task_id
        objective = envelope.objective
        depth = envelope.current_depth
        max_depth = envelope.max_depth
        all_findings = envelope.all_findings
        digest_signals = envelope.digest_signals

        prompt_data = get_prompts_dict("research/orchestrator_reflect.yaml")
        try:
            from backend.services.research.context_builder import ResearchContextBuilder
            builder = ResearchContextBuilder(orch._state)
            persona = await builder.build_reflection_context(objective, depth)
        except Exception:
            persona = await orch._build_orchestrator_persona(objective)

        system_prompt = persona + "\n\n" + prompt_data.get("system", "")
        if prompt_data.get("anti_mastery"):
            system_prompt = apply_anti_mastery_filter(system_prompt)

        signals = digest_signals or {}
        all_findings = all_findings or []

        parsed_urls_list = orch._get_parsed_urls(task_id)

        # Extract findings of the current cycle from the DB
        current_cycle_findings = []
        if orch.step_repo and orch.step_result_repo:
            try:
                steps = orch.step_repo.get_by_task(task_id)
                current_parse_steps = [
                    st for st in steps
                    if st.get("step_type") in ("parallel_parse", "document_digestion") and orch._get_step_depth(st) == depth
                ]
                for ps in current_parse_steps:
                    db_results = orch.step_result_repo.get_by_step(ps["id"])
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
        from backend.services.research.steps.source_utils import apply_unified_references
        all_to_compress = current_cycle_findings + historical_findings
        formatted_urls, compressed_all, compressed_followups, compressed_gaps = apply_unified_references(
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

        previous_reflection = state.get("last_reflection", {})
        prev_refl_formatted = orch._format_reflection_markdown(previous_reflection, depth, include_cycle=True)

        goal = objective
        if state.get("plan") and isinstance(state["plan"], dict):
            goal = state["plan"].get("goal", objective)

        user_prompt = prompt_data.get("user", "").format(
            objective=objective,
            goal=goal,
            current_depth=depth,
            max_depth=max_depth,
            parsed_urls=parsed_urls_text,
            accumulated_findings=accumulated_findings_text,
            previous_reflection=prev_refl_formatted,
            digest_followups=followups_text,
            digest_direct_urls=direct_urls_text,
            digest_gaps=gaps_text,
        )

        if prompt_data.get("anti_mastery"):
            user_prompt = apply_anti_mastery_filter(user_prompt)

        return {
            "phase": "consolidating",
            "objective": objective,
            "current_depth": depth,
            "max_depth": max_depth,
            "max_rounds": getattr(orch, "max_reflect_rounds", 3),
            "findings_count": len(all_findings),
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "accumulated_findings": all_findings,
            "digest_signals": signals,
            "parsed_urls": parsed_urls_list,
            "cached_at": now_utc_str(),
        }

    async def execute(self, orch, envelope: StepEnvelope) -> StepOutput:
        task_id = envelope.task_id
        objective = envelope.objective
        current_depth = envelope.current_depth
        max_depth = envelope.max_depth
        all_findings = envelope.all_findings
        digest_signals = envelope.digest_signals

        payload: ConsolidatePayload = envelope.payload

        goal = objective
        state = orch._get_state(task_id)
        if state.get("plan") and isinstance(state["plan"], dict):
            goal = state["plan"].get("goal", objective)

        s = orch._get_state(task_id)
        step_id = orch._create_or_update_step(s, task_id, "reflect")

        reflection = await run_consolidation(
            orch, task_id, objective, goal,
            current_depth, max_depth,
            all_findings, payload.last_reflection,
            digest_signals=digest_signals, step_id=step_id,
        )

        completeness = reflection.get("completeness_score", 0.0)

        if orch.step_repo:
            orch.step_repo.update(step_id, status="completed",
                result_summary=f"completeness: {completeness:.2f}")

        orch._log_meta(task_id, "orchestrator_reflect", {
            "depth": current_depth, "completeness": completeness,
            "total_findings": len(all_findings),
        }, step_id=step_id)

        key_insights = reflection.get("key_insights", [])

        # ── Sedimentation: push pattern packet if completeness threshold met ──
        if completeness > 0.7 and key_insights:
            orch._push_sedimentation_packet(
                task_id=task_id,
                phase="consolidate",
                trigger_thresholds={"completeness_score": completeness},
                raw_context=json.dumps(key_insights)[:8000],
                proposed_node_type="pattern",
                confidence=completeness,
            )

        out_payload = ConsolidatePayload(
            last_reflection=reflection,
            completeness_score=completeness,
            key_insights=reflection.get("key_insights", []),
            remaining_gaps=reflection.get("remaining_gaps", []),
            next_queries=reflection.get("next_queries", []),
            next_direct_urls=reflection.get("next_direct_urls", [])
        )

        rationale = f"Evaluated research completeness ({completeness * 100:.1f}%). Identified {len(reflection.get('remaining_gaps', []))} remaining gaps and planned {len(reflection.get('next_queries', []))} follow-up queries."

        return StepOutput(
            status="completed",
            message=f"completeness score: {completeness:.2f}",
            payload=out_payload,
            step_ids=[step_id],
            transition_rationale=rationale
        )
