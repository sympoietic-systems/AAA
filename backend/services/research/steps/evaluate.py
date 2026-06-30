import logging

from backend.services.research.steps.base import BaseResearchStep
from backend.services.research.task_state import EvaluatePayload, StepEnvelope, StepOutput

logger = logging.getLogger("aaa.research_orchestrator")


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

        should_stop, stop_reason = await orch._tool_evaluate(
            task_id=task_id, step_id=step_id,
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
