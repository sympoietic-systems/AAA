"""PureReflectionStep — standalone pure reflection step.

Calculates diffractive Glitch Fidelity, ingests compact structural envelope metadata,
runs multi-cycle reflection, and emits signal flags (GLITCH_FIDELITY_LOW, BIAS_DETECTED, GAP_CRITICAL).
"""

import logging
from backend.services.research.steps.base import BaseResearchStep, ResearchStepRegistry
from backend.services.research.steps.reflect import ReflectionStep
from backend.services.research.task_state import StepEnvelope, StepOutput

logger = logging.getLogger("aaa.research_orchestrator")


class PureReflectionStep(ReflectionStep):
    """Pure reflection step that acts on the complete StepEnvelope state."""

    @property
    def step_type(self) -> str:
        return "pure_reflection"

    async def execute(self, orch, envelope: StepEnvelope) -> StepOutput:
        # Call parent ReflectionStep execution
        output: StepOutput = await super().execute(orch, envelope)

        # Enhance signal flags on StepOutput payload based on metrics
        payload = output.payload
        flags = list(payload.signal_flags) if hasattr(payload, "signal_flags") and payload.signal_flags else []

        fidelity = getattr(payload, "glitch_fidelity", 1.0)
        biases = getattr(payload, "detected_biases", [])
        gaps = getattr(payload, "knowledge_gaps", [])

        if fidelity < 0.60 and "GLITCH_FIDELITY_LOW" not in flags:
            flags.append("GLITCH_FIDELITY_LOW")
        if len(biases) > 0 and "BIAS_DETECTED" not in flags:
            flags.append("BIAS_DETECTED")
        if len(gaps) >= 3 and "GAP_CRITICAL" not in flags:
            flags.append("GAP_CRITICAL")

        payload.signal_flags = flags
        signal_flags_dict = dict.fromkeys(flags, True)

        return StepOutput(
            status=output.status,
            message=output.message,
            payload=payload,
            signal_flags=signal_flags_dict,
            step_ids=output.step_ids,
            transition_rationale=output.transition_rationale,
        )


ResearchStepRegistry.register("pure_reflection", PureReflectionStep)
