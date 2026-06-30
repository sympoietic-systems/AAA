import logging

from backend.services.research.steps.base import BaseResearchStep
from backend.services.research.task_state import SynthesizePayload, StepEnvelope, StepOutput

logger = logging.getLogger("aaa.research_orchestrator")


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

        result_summary = await orch._phase_synthesize(
            task_id, objective, goal,
            all_findings, sources_analyzed, step_id=step_id,
        )

        # Get step_number for backwards compatibility updates
        step_number = state.get("step_number", current_depth + 2)

        if orch.task_repo:
            orch.task_repo.update(task_id,
                branches_created=step_number,
                assets_harvested=sources_analyzed,
                result_summary=result_summary,
            )

        if orch.step_repo:
            orch.step_repo.update(step_id, status="completed",
                result_summary=f"{sources_analyzed} sources, {len(all_findings)} findings")

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

        return StepOutput(
            status="completed",
            message="synthesis complete",
            payload=out_payload
        )
