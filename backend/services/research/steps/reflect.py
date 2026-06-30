import logging

from backend.services.research.steps.base import BaseResearchStep
from backend.services.research.task_state import ReflectionPayload, StepEnvelope, StepOutput

logger = logging.getLogger("aaa.research_orchestrator")


class ReflectionStep(BaseResearchStep):
    @property
    def step_type(self) -> str:
        return "reflection"

    async def execute(self, orch, envelope: StepEnvelope) -> StepOutput:
        task_id = envelope.task_id
        objective = envelope.objective
        current_depth = envelope.current_depth
        max_depth = envelope.max_depth
        all_findings = envelope.all_findings
        digest_signals = envelope.digest_signals

        s = orch._get_state(task_id)
        step_id = orch._create_or_update_step(s, task_id, "reflection")

        # Call the reflection tool to get deep first-person monologue and metrics
        reflection = await orch._tool_reflection(
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

        # Merge the generated refined queries and signal flags to the active state so subsequent steps can see them
        s["digest_signals"] = s.get("digest_signals", {})
        if out_payload.refined_queries:
            # Let the planning loop or search query generator have these
            s["digest_signals"]["refined_queries"] = out_payload.refined_queries
        
        # Propagate signal flags
        signal_flags = {}
        for flag in out_payload.signal_flags:
            signal_flags[flag] = True

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
