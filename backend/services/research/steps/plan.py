import json
import uuid

from backend.services.research.steps.base import BaseResearchStep
from backend.services.research.task_state import StepEnvelope, StepOutput, PlanPayload
from backend.utils.research_logger import now_utc_str


class PlanStep(BaseResearchStep):
    @property
    def step_type(self) -> str:
        return "plan"

    async def execute(self, orch, envelope: StepEnvelope) -> StepOutput:
        task_id = envelope.task_id
        objective = envelope.objective
        current_depth = envelope.current_depth
        max_depth = envelope.max_depth
        budget = envelope.budget

        payload: PlanPayload = envelope.payload
        previous_context = payload.previous_context or ""
        inject_file_id = payload.inject_file_id

        step_id = str(uuid.uuid4())

        if inject_file_id and previous_context:
            previous_context = (
                "[Injected document will be digested against the objective "
                "in the next phase.]\n\n" + previous_context
            )

        from backend.services.research.phases import _phase_plan
        plan = await _phase_plan(
            orch, task_id, objective, max_depth, budget,
            previous_context=previous_context, step_id=step_id
        )

        # Save to database step log
        if orch.step_repo:
            orch.step_repo.create({
                "id": step_id,
                "task_id": task_id,
                "plan_id": plan["id"],
                "step_number": envelope.current_depth + 1,  # fallback tracking
                "step_type": "plan",
                "status": "completed",
                "started_at": now_utc_str(),
                "result_summary": f"{len(plan.get('search_queries', []))} queries planned",
                "step_data": json.dumps({"plan": plan, "depth": current_depth}, default=str, ensure_ascii=False),
            })

        orch._log_meta(task_id, "orchestrator_plan", {
            "plan": plan,
            "previous_context_injected": bool(previous_context),
            "previous_context_len": len(previous_context) if previous_context else 0,
            "max_depth": max_depth,
        }, step_id=step_id)

        out_payload = PlanPayload(
            previous_context=payload.previous_context,
            inject_file_id=payload.inject_file_id,
            goal=plan.get("goal", objective),
            search_queries=plan.get("search_queries", [objective]),
            n_results_per_query=plan.get("n_results_per_query", 3),
            estimated_depth=plan.get("estimated_depth", 1)
        )

        return StepOutput(
            status="completed",
            message=f"{len(plan.get('search_queries', []))} queries planned",
            payload=out_payload,
            signal_flags={"plan_id": plan["id"]},
            step_ids=[step_id],
            transition_rationale=f"Planned {len(plan.get('search_queries', []))} search queries for depth {current_depth}."
        )
