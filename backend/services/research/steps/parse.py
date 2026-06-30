import logging

from backend.services.research.steps.base import BaseResearchStep
from backend.services.research.task_state import ParsePayload, StepEnvelope, StepOutput
from backend.utils.research_logger import now_utc_str

logger = logging.getLogger("aaa.research_orchestrator")


class ParseStep(BaseResearchStep):
    @property
    def step_type(self) -> str:
        return "parse"

    async def execute(self, orch, envelope: StepEnvelope) -> StepOutput:
        task_id = envelope.task_id
        current_depth = envelope.current_depth
        plan_id = envelope.plan_id

        payload: ParsePayload = envelope.payload
        search_cache = payload.search_results_cache

        query_groups = sorted(list(set(r.get("query_group", 1) for r in search_cache))) or [1]

        s = orch._get_state(task_id)
        group_steps = {}

        for q_group in query_groups:
            step_id = orch._create_or_update_step(s, task_id, "parallel_parse",
                query_group=q_group, query_text="")
            group_steps[q_group] = step_id

        parsed = await orch._tool_parallel_parse_grouped(
            task_id, group_steps, search_cache, plan_id,
        )

        if orch.step_repo:
            for q_group, step_id in group_steps.items():
                parsed_for_group = [p for p in parsed if p.get("query_group") == q_group]
                orch.step_repo.update(step_id, status="completed",
                    result_summary=f"parsed {len(parsed_for_group)} sources")

        urls = [{"url": p["url"], "title": p.get("title", p["url"]), "query_group": p.get("query_group")} for p in parsed]

        cache = orch._load_cache(task_id)
        cache["parsing"] = {"phase": "parsing", "urls": urls, "cached_at": now_utc_str()}
        orch._save_cache(task_id, cache)

        out_payload = ParsePayload(
            search_results_cache=search_cache,
            parsed_sources=parsed
        )

        signal_flags = {"has_parsed_content": len(parsed) > 0}

        return StepOutput(
            status="completed",
            message=f"parsed {len(parsed)} sources",
            payload=out_payload,
            signal_flags=signal_flags
        )
