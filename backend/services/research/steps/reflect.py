import json
import logging
import math
from urllib.parse import urlparse

from backend.services.research.steps.base import BaseResearchStep
from backend.services.research.task_state import ReflectionPayload, StepEnvelope, StepOutput
from backend.utils.prompt_loader import get_prompts_dict
from backend.utils.anti_mastery import apply_anti_mastery_filter
from backend.modules.llm_client import generate_unified
from backend.utils.research_logger import now_utc_str

logger = logging.getLogger("aaa.research_orchestrator")


async def run_deep_reflection(orch, task_id: str, objective: str,
                              depth: int, max_depth: int, all_findings: list[str],
                              digest_signals: dict = None, step_id: str = "") -> dict:
    """Deep meta-reflection — three-cycle self-critique loop.

    - Cycle 1: Generate initial critique and Monologue Trace from findings.
    - Cycle 2: Critical Self-Critique of Cycle 1's monologue (strict register audit).
    - Cycle 3: Synthesized final meta-reflection JSON with critique_log (the scar).

    Migrated from legacy tools._tool_reflection.
    """
    # ── Calculate Glitch Fidelity ──
    glitches_detected = 0
    glitches_addressed = 0
    steps = orch.step_repo.get_by_task(task_id) if orch.step_repo else []
    for i, step in enumerate(steps):
        if step.get("step_type") == "searching":
            results = orch.step_result_repo.get_by_step(step["id"]) if orch.step_result_repo else []
            if not results or all(not r.get("source_url") for r in results):
                glitches_detected += 1
                if any(s.get("step_type") == "planning" for s in steps[i + 1:]):
                    glitches_addressed += 1
        elif step.get("step_type") == "parsing":
            results = orch.step_result_repo.get_by_step(step["id"]) if orch.step_result_repo else []
            for r in results:
                raw_c = r.get("raw_content") or ""
                if not raw_c or "error" in raw_c.lower() or raw_c.startswith("Error:"):
                    glitches_detected += 1
                    if any(s.get("step_type") in ("searching", "planning") for s in steps[i + 1:]):
                        glitches_addressed += 1
                        break

    glitch_fidelity = (glitches_addressed / glitches_detected) if glitches_detected > 0 else 1.0

    # ── Calculate Source Entropy (Shannon entropy on domains) ──
    parsed_urls = orch._get_parsed_urls(task_id)
    domains = []
    for u in parsed_urls:
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
        counts: dict[str, int] = {}
        for d in domains:
            counts[d] = counts.get(d, 0) + 1
        n = len(domains)
        source_entropy = -sum((count / n) * math.log2(count / n) for count in counts.values())

    # ── Calculate Contradiction Density ──
    contradiction_density = 0.0
    if all_findings:
        tension_keywords = ["conflict", "contradict", "disagree", "oppose", "tension",
                            "clash", "versus", "vs", "difference"]
        matches = sum(1 for f in all_findings if any(kw in f.lower() for kw in tension_keywords))
        contradiction_density = matches / len(all_findings)

    prompt_data = get_prompts_dict("research/orchestrator_reflection.yaml")
    persona = await orch._build_orchestrator_persona(objective)

    # Format visited URLs list
    formatted_urls = [
        f"- [{u.get('title') or u.get('source_title') or f'Source {i+1}'}]({u.get('url') or u.get('source_url', '')})"
        for i, u in enumerate(parsed_urls)
    ]
    parsed_urls_text = "\n".join(formatted_urls) or "(none)"
    accumulated_findings_text = "\n".join(f"- {f}" for f in all_findings) or "(none)"

    fallback = {
        "reflection_notes": "Reflection fallback: failed to run monologue.",
        "glitch_fidelity": glitch_fidelity,
        "contradiction_density": contradiction_density,
        "source_entropy": source_entropy,
        "signal_flags": [],
        "refined_queries": [],
        "revised_confidence": 0.5,
        "monologue_trace": [],
        "critique_log": []
    }

    llm = getattr(orch._state, "llm_provider", None)
    if not llm:
        logger.warning("No LLM provider available for Reflection. Using fallback.")
        return fallback

    # Cache initial Persona & System Prompt for preview
    system_text_c1 = persona + "\n\n" + prompt_data.get("system", "")
    cache = orch._load_cache(task_id)
    cache["reflection"] = {
        "phase": "reflection",
        "persona": persona,
        "system_prompt": system_text_c1,
        "cached_at": now_utc_str(),
    }
    orch._save_cache(task_id, cache)

    try:
        # ── CYCLE 1: INITIAL REFLECTION GENERATION ──
        user_text_c1 = prompt_data.get("user", "").format(
            objective=objective,
            current_depth=depth,
            max_depth=max_depth,
            parsed_urls=parsed_urls_text,
            accumulated_findings=accumulated_findings_text,
            glitch_fidelity=f"{glitch_fidelity:.2f}",
            contradiction_density=f"{contradiction_density:.2f}",
            source_entropy=f"{source_entropy:.2f}"
        )
        if prompt_data.get("anti_mastery"):
            system_text_c1 = apply_anti_mastery_filter(system_text_c1)
            user_text_c1 = apply_anti_mastery_filter(user_text_c1)

        orch._log_meta(task_id, "orchestrator_reflection_prompt_c1", {
            "system_prompt": system_text_c1[:2000],
            "user_prompt": user_text_c1[:2000],
        }, step_id=step_id or None)

        resp_c1 = await generate_unified(llm, system_prompt=system_text_c1, user_prompt=user_text_c1,
            expect_json=True, fallback_value=fallback,
            temperature=prompt_data.get("temperature", 0.7),
            max_tokens=prompt_data.get("max_tokens", 8192))

        result_c1 = resp_c1.get("json_data") or resp_c1.get("content") or {}
        if isinstance(result_c1, str):
            result_c1 = json.loads(result_c1)
        if not isinstance(result_c1, dict):
            result_c1 = fallback

        orch._log_llm_response(task_id, "orchestrator_reflection_response_c1", resp_c1, extra={
            "revised_confidence": result_c1.get("revised_confidence", 0.5),
        }, step_id=step_id or None)

        # ── CYCLE 2: STRICT SELF-CRITIQUE AUDIT ──
        system_text_c2 = persona + "\n\n" + prompt_data.get("system_cycle2", "")
        user_text_c2 = prompt_data.get("user_cycle2", "").format(
            cycle1_reflection_notes=result_c1.get("reflection_notes", ""),
            cycle1_monologue_trace=json.dumps(result_c1.get("monologue_trace", []), ensure_ascii=False),
            cycle1_detected_biases=json.dumps(result_c1.get("detected_biases", []), ensure_ascii=False),
            cycle1_knowledge_gaps=json.dumps(result_c1.get("knowledge_gaps", []), ensure_ascii=False),
            cycle1_refined_queries=json.dumps(result_c1.get("refined_queries", []), ensure_ascii=False),
            cycle1_glitch_fidelity=f"{result_c1.get('glitch_fidelity', glitch_fidelity):.2f}",
            cycle1_contradiction_density=f"{result_c1.get('contradiction_density', contradiction_density):.2f}",
            cycle1_source_entropy=f"{result_c1.get('source_entropy', source_entropy):.2f}"
        )
        if prompt_data.get("anti_mastery"):
            system_text_c2 = apply_anti_mastery_filter(system_text_c2)
            user_text_c2 = apply_anti_mastery_filter(user_text_c2)

        orch._log_meta(task_id, "orchestrator_reflection_prompt_c2", {
            "system_prompt": system_text_c2[:2000],
            "user_prompt": user_text_c2[:2000],
        }, step_id=step_id or None)

        fallback_c2 = {
            "critique_log": [
                {"register": r, "severity": "MISSING",
                 "failure_description": "Failed to run critique cycle.",
                 "suggestion": "Ensure LLM completes successfully."}
                for r in ["framing_provenance", "contradictions", "source_apparatus",
                          "glitch_voice", "confidence_check"]
            ],
            "diffractive_audit": "CEREMONIAL",
            "diffractive_audit_description": "Failed to run critique cycle."
        }

        resp_c2 = await generate_unified(llm, system_prompt=system_text_c2, user_prompt=user_text_c2,
            expect_json=True, fallback_value=fallback_c2,
            temperature=prompt_data.get("temperature", 0.7),
            max_tokens=prompt_data.get("max_tokens", 8192))

        result_c2 = resp_c2.get("json_data") or resp_c2.get("content") or {}
        if isinstance(result_c2, str):
            result_c2 = json.loads(result_c2)
        if not isinstance(result_c2, dict):
            result_c2 = fallback_c2

        orch._log_llm_response(task_id, "orchestrator_reflection_response_c2", resp_c2, extra={
            "diffractive_audit": result_c2.get("diffractive_audit", "CEREMONIAL"),
        }, step_id=step_id or None)

        # ── CYCLE 3: FINAL SYNTHESIS & DEEPENING (THE SCAR) ──
        system_text_c3 = persona + "\n\n" + prompt_data.get("system_cycle3", "")
        user_text_c3 = prompt_data.get("user_cycle3", "").format(
            cycle1_json=json.dumps(result_c1, ensure_ascii=False),
            cycle2_json=json.dumps(result_c2, ensure_ascii=False),
            glitch_fidelity=f"{glitch_fidelity:.2f}",
            contradiction_density=f"{contradiction_density:.2f}",
            source_entropy=f"{source_entropy:.2f}"
        )
        if prompt_data.get("anti_mastery"):
            system_text_c3 = apply_anti_mastery_filter(system_text_c3)
            user_text_c3 = apply_anti_mastery_filter(user_text_c3)

        orch._log_meta(task_id, "orchestrator_reflection_prompt_c3", {
            "system_prompt": system_text_c3[:2000],
            "user_prompt": user_text_c3[:2000],
        }, step_id=step_id or None)

        resp_c3 = await generate_unified(llm, system_prompt=system_text_c3, user_prompt=user_text_c3,
            expect_json=True, fallback_value=result_c1,
            temperature=prompt_data.get("temperature", 0.7),
            max_tokens=prompt_data.get("max_tokens", 8192))

        result_c3 = resp_c3.get("json_data") or resp_c3.get("content") or {}
        if isinstance(result_c3, str):
            result_c3 = json.loads(result_c3)
        if not isinstance(result_c3, dict):
            result_c3 = result_c1

        # Enforce metrics remain immutable as calculated
        result_c3["glitch_fidelity"] = glitch_fidelity
        result_c3["contradiction_density"] = contradiction_density
        result_c3["source_entropy"] = source_entropy

        # Inject critique log as the scar
        result_c3["critique_log"] = result_c2.get("critique_log", [])
        result_c3["diffractive_audit"] = result_c2.get("diffractive_audit", "CEREMONIAL")
        result_c3["diffractive_audit_description"] = result_c2.get("diffractive_audit_description", "")

        orch._log_llm_response(task_id, "orchestrator_reflection_response_c3", resp_c3, extra={
            "revised_confidence": result_c3.get("revised_confidence", 0.5),
            "signal_flags": result_c3.get("signal_flags", []),
        }, step_id=step_id or None)

        if step_id:
            orch._save_llm_response_to_step_data(step_id, resp_c3)

        return result_c3

    except Exception as e:
        logger.warning("Deep multi-cycle reflection failed: %s", e, exc_info=True)
        return fallback


class ReflectionStep(BaseResearchStep):
    @property
    def step_type(self) -> str:
        return "reflection"

    async def preview(self, orch, envelope: StepEnvelope, state: dict) -> dict:
        task_id = envelope.task_id
        objective = envelope.objective
        depth = envelope.current_depth
        max_depth = envelope.max_depth

        payload: ReflectionPayload = envelope.payload
        all_findings = envelope.all_findings or []

        # ── Calculate Glitch Fidelity ──
        glitches_detected = 0
        glitches_addressed = 0
        steps = orch.step_repo.get_by_task(task_id) if orch.step_repo else []
        for i, step in enumerate(steps):
            if step.get("step_type") == "searching":
                results = orch.step_result_repo.get_by_step(step["id"]) if orch.step_result_repo else []
                if not results or all(not r.get("source_url") for r in results):
                    glitches_detected += 1
                    if any(s.get("step_type") == "planning" for s in steps[i + 1:]):
                        glitches_addressed += 1
            elif step.get("step_type") == "parsing":
                results = orch.step_result_repo.get_by_step(step["id"]) if orch.step_result_repo else []
                for r in results:
                    raw_c = r.get("raw_content") or ""
                    if not raw_c or "error" in raw_c.lower() or raw_c.startswith("Error:"):
                        glitches_detected += 1
                        if any(s.get("step_type") in ("searching", "planning") for s in steps[i + 1:]):
                            glitches_addressed += 1
                            break

        glitch_fidelity = (glitches_addressed / glitches_detected) if glitches_detected > 0 else 1.0

        # ── Calculate Source Entropy (Shannon entropy on domains) ──
        parsed_urls = orch._get_parsed_urls(task_id)
        domains = []
        for u in parsed_urls:
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
            counts: dict[str, int] = {}
            for d in domains:
                counts[d] = counts.get(d, 0) + 1
            n = len(domains)
            source_entropy = -sum((count / n) * math.log2(count / n) for count in counts.values())

        # ── Calculate Contradiction Density ──
        contradiction_density = 0.0
        if all_findings:
            tension_keywords = ["conflict", "contradict", "disagree", "oppose", "tension",
                                "clash", "versus", "vs", "difference"]
            matches = sum(1 for f in all_findings if any(kw in f.lower() for kw in tension_keywords))
            contradiction_density = matches / len(all_findings)

        prompt_data = get_prompts_dict("research/orchestrator_reflection.yaml")
        try:
            from backend.services.research.context_builder import ResearchContextBuilder
            builder = ResearchContextBuilder(orch._state)
            persona = await builder.build_reflection_context(objective, depth)
        except Exception:
            persona = await orch._build_orchestrator_persona(objective)

        system_prompt = persona + "\n\n" + prompt_data.get("system", "")

        formatted_urls = [
            f"- [{u.get('title') or u.get('source_title') or f'Source {i+1}'}]({u.get('url') or u.get('source_url', '')})"
            for i, u in enumerate(parsed_urls)
        ]
        parsed_urls_text = "\n".join(formatted_urls) or "(none)"
        accumulated_findings_text = "\n".join(f"- {f}" for f in all_findings) or "(none)"

        user_prompt = prompt_data.get("user", "").format(
            objective=objective,
            current_depth=depth,
            max_depth=max_depth,
            parsed_urls=parsed_urls_text,
            accumulated_findings=accumulated_findings_text,
            glitch_fidelity=f"{glitch_fidelity:.2f}",
            contradiction_density=f"{contradiction_density:.2f}",
            source_entropy=f"{source_entropy:.2f}"
        )

        if prompt_data.get("anti_mastery"):
            system_prompt = apply_anti_mastery_filter(system_prompt)
            user_prompt = apply_anti_mastery_filter(user_prompt)

        return {
            "phase": "reflection",
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "model": getattr(orch._state, "llm_provider", None) and getattr(orch._state.llm_provider, "model_id", "(auto)") or "(auto)",
            "temperature": prompt_data.get("temperature", 0.7),
            "max_tokens": prompt_data.get("max_tokens", 8192),
            "cached_at": now_utc_str(),
        }

    async def execute(self, orch, envelope: StepEnvelope) -> StepOutput:
        task_id = envelope.task_id
        objective = envelope.objective
        current_depth = envelope.current_depth
        max_depth = envelope.max_depth
        all_findings = envelope.all_findings
        digest_signals = envelope.digest_signals

        s = orch._get_state(task_id)
        step_id = orch._create_or_update_step(s, task_id, "reflection")

        reflection = await run_deep_reflection(
            orch, task_id, objective,
            current_depth, max_depth,
            all_findings, digest_signals=digest_signals,
            step_id=step_id,
        )

        fidelity = reflection.get("glitch_fidelity", 1.0)
        density = reflection.get("contradiction_density", 0.0)
        entropy = reflection.get("source_entropy", 0.0)
        confidence = reflection.get("revised_confidence", 0.5)

        if orch.step_repo:
            orch.step_repo.update(step_id, status="completed",
                result_summary=f"Fidelity: {fidelity:.2f} | Contradictions: {density:.2f} | Entropy: {entropy:.2f}")

        orch._log_meta(task_id, "orchestrator_reflection", {
            "depth": current_depth,
            "glitch_fidelity": fidelity,
            "contradiction_density": density,
            "source_entropy": entropy,
            "revised_confidence": confidence
        }, step_id=step_id)

        out_payload = ReflectionPayload(
            reflection_notes=reflection.get("reflection_notes", ""),
            detected_biases=reflection.get("detected_biases", []),
            knowledge_gaps=reflection.get("knowledge_gaps", []),
            glitch_fidelity=fidelity,
            contradiction_density=density,
            source_entropy=entropy,
            signal_flags=reflection.get("signal_flags", []),
            refined_queries=reflection.get("refined_queries", []),
            revised_confidence=confidence,
            monologue_trace=reflection.get("monologue_trace", []),
            critique_log=reflection.get("critique_log", []),
            diffractive_audit=reflection.get("diffractive_audit", "CEREMONIAL"),
            diffractive_audit_description=reflection.get("diffractive_audit_description", "")
        )

        # Merge refined queries and signal flags into state for subsequent steps
        s["digest_signals"] = s.get("digest_signals", {})
        if out_payload.refined_queries:
            s["digest_signals"]["refined_queries"] = out_payload.refined_queries

        # ── Sedimentation: push tension packet if thresholds trip ──
        if density > 0.3 or fidelity < 0.7:
            critique_context = json.dumps({
                "phase": "reflection",
                "critique_log": reflection.get("critique_log", []),
                "reflection_notes": reflection.get("reflection_notes", ""),
                "contradiction_density": density,
                "glitch_fidelity": fidelity,
            })
            orch._push_sedimentation_packet(
                task_id=task_id,
                phase="reflection",
                trigger_thresholds={
                    "contradiction_density": density,
                    "glitch_fidelity": fidelity,
                },
                raw_context=critique_context,
                proposed_node_type="tension",
                confidence=max(density, 1.0 - fidelity),
            )

        signal_flags = {flag: True for flag in out_payload.signal_flags}

        rationale = (
            f"Conducted a deep meta-reflection on research findings. "
            f"Fidelity score: {fidelity:.2f}, Contradiction score: {density:.2f}. "
            f"Revised confidence: {confidence * 100:.1f}%. "
            f"Generated {len(out_payload.refined_queries)} refined critical query probes."
        )

        return StepOutput(
            status="completed",
            message=f"Deep reflection completed (Fidelity: {fidelity:.2f})",
            payload=out_payload,
            signal_flags=signal_flags,
            step_ids=[step_id],
            transition_rationale=rationale
        )
