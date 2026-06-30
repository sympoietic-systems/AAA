import logging

from backend.services.research.steps.base import BaseResearchStep
from backend.services.research.task_state import ReflectPayload, StepEnvelope, StepOutput

logger = logging.getLogger("aaa.research_orchestrator")


class ReflectStep(BaseResearchStep):
    @property
    def step_type(self) -> str:
        return "reflect"

    async def execute(self, orch, envelope: StepEnvelope) -> StepOutput:
        task_id = envelope.task_id
        objective = envelope.objective
        current_depth = envelope.current_depth
        max_depth = envelope.max_depth
        all_findings = envelope.all_findings
        digest_signals = envelope.digest_signals

        payload: ReflectPayload = envelope.payload

        goal = objective
        state = orch._get_state(task_id)
        if state.get("plan") and isinstance(state["plan"], dict):
            goal = state["plan"].get("goal", objective)

        s = orch._get_state(task_id)
        step_id = orch._create_or_update_step(s, task_id, "reflect")

        reflection = await orch._tool_reflect(
            task_id, objective, goal,
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

        out_payload = ReflectPayload(
            last_reflection=reflection,
            completeness_score=completeness,
            key_insights=reflection.get("key_insights", []),
            remaining_gaps=reflection.get("remaining_gaps", []),
            next_queries=reflection.get("next_queries", []),
            next_direct_urls=reflection.get("next_direct_urls", [])
        )

        return StepOutput(
            status="completed",
            message=f"completeness score: {completeness:.2f}",
            payload=out_payload
        )
