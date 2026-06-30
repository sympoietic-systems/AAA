import json
import logging

from backend.services.research.steps.base import BaseResearchStep
from backend.services.research.task_state import DigestPayload, StepEnvelope, StepOutput
from backend.utils.research_logger import now_utc_str

logger = logging.getLogger("aaa.research_orchestrator")


class DigestStep(BaseResearchStep):
    @property
    def step_type(self) -> str:
        return "digest"

    async def execute(self, orch, envelope: StepEnvelope) -> StepOutput:
        task_id = envelope.task_id
        objective = envelope.objective
        current_depth = envelope.current_depth
        max_depth = envelope.max_depth

        payload: DigestPayload = envelope.payload
        parsed_sources = payload.parsed_sources_cache

        # Reconstruct parsed sources from completed parallel_parse steps if empty
        if not parsed_sources and orch.step_repo and orch.step_result_repo:
            steps = orch.step_repo.get_by_task(task_id)
            parse_steps = [
                st for st in steps
                if st["step_type"] == "parallel_parse" and st["status"] == "completed"
                and orch._get_step_depth(st) == current_depth
            ]
            if parse_steps:
                parsed_sources = []
                for ps in parse_steps:
                    db_results = orch.step_result_repo.get_by_step(ps["id"])
                    for r in db_results:
                        parsed_sources.append({
                            "id": r["id"], "url": r["source_url"],
                            "title": r["source_title"], "content": r["raw_content"],
                            "query_group": ps.get("query_group", 1),
                        })

        query_groups = sorted(list(set(src.get("query_group", 1) for src in parsed_sources))) or [1]

        # Resolve queries
        plan_queries = []
        state = orch._get_state(task_id)
        if state.get("plan") and isinstance(state["plan"], dict):
            plan_queries = state["plan"].get("search_queries", [objective])
        else:
            plan_queries = [objective]

        last_refl = state.get("last_reflection") or {}
        queries = last_refl.get("next_queries") if (current_depth > 0 and last_refl.get("next_queries")) else plan_queries

        s = orch._get_state(task_id)
        group_steps = {}
        for q_group in query_groups:
            q_text = queries[q_group - 1] if (q_group - 1) < len(queries) else objective
            step_id = orch._create_or_update_step(s, task_id, "digest",
                query_group=q_group, query_text=q_text[:300])
            group_steps[q_group] = step_id

        digest_results = await orch._tool_parallel_digest_grouped(
            task_id, group_steps, parsed_sources,
            queries, objective, current_depth, max_depth,
        )

        if orch.step_repo:
            for q_group, step_id in group_steps.items():
                digested_for_group = [dr for dr in digest_results if dr.get("query_group") == q_group]
                orch.step_repo.update(step_id, status="completed",
                    result_summary=f"digested {len(digested_for_group)} sources")

        new_findings = []
        all_learnings = []
        followups = []
        gaps = []

        for dr in digest_results:
            r = dr.get("result", {})
            learnings = r.get("learnings", []) if isinstance(r, dict) else []
            all_learnings.extend(learnings)
            if learnings:
                new_findings.extend(
                    f"[{dr['source_title'] or dr['source_url'][:80]}]: " + l
                    for l in learnings
                )
            if isinstance(r, dict):
                followups.extend(r.get("followups", []))
                gaps.extend(r.get("gaps", []))

        out_payload = DigestPayload(
            parsed_sources_cache=parsed_sources,
            learnings=all_learnings,
            followups=followups,
            gaps=gaps
        )

        return StepOutput(
            status="completed",
            message=f"digested {len(parsed_sources)} sources, got {len(all_learnings)} learnings",
            payload=out_payload,
            new_findings=new_findings
        )
