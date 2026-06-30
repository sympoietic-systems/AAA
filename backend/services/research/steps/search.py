import asyncio
import json
import logging
import re
import uuid

from backend.services.research.steps.base import BaseResearchStep
from backend.services.research.task_state import SearchPayload, StepEnvelope, StepOutput
from backend.services.research.search_tool import web_search
from backend.utils.research_logger import now_utc_str

logger = logging.getLogger("aaa.research_orchestrator")


class SearchStep(BaseResearchStep):
    @property
    def step_type(self) -> str:
        return "search"

    async def execute(self, orch, envelope: StepEnvelope) -> StepOutput:
        task_id = envelope.task_id
        current_depth = envelope.current_depth
        payload: SearchPayload = envelope.payload
        raw_queries = payload.queries

        def _clean_query_for_ddg(q: str) -> str:
            q = q.strip()
            # Strip outer double quotes if query is wrapped in quotes
            if q.startswith('"') and q.endswith('"'):
                if q.startswith('""') and q.endswith('""'):
                    q = q[1:-1]
                elif q.count('"') == 2:
                    q = q[1:-1]
            # Deduplicate internal double quotes
            while '""' in q:
                q = q.replace('""', '"')
            q = re.sub(r'\b(AND|OR|NOT)\b', ' ', q, flags=re.IGNORECASE)
            q = q.replace('(', ' ').replace(')', ' ')
            q = ' '.join(q.split())
            return q.strip()

        raw_queries = [_clean_query_for_ddg(str(q)) for q in raw_queries]

        search_queries = []
        direct_urls = []

        # Load direct URLs from payload
        for u in payload.direct_urls:
            if isinstance(u, str) and (u.startswith("http://") or u.startswith("https://")):
                if u not in direct_urls:
                    direct_urls.append(u)

        for q in raw_queries:
            if isinstance(q, str) and (q.startswith("http://") or q.startswith("https://")):
                if q not in direct_urls:
                    direct_urls.append(q)
            else:
                search_queries.append(q)

        direct_urls = direct_urls[:5]
        pending_queries = search_queries + (["Direct URL Parse Pointers"] if direct_urls else [])

        # Cache search inputs for re-use on rerun
        cache = orch._load_cache(task_id)
        cache["searching"] = {
            "phase": "searching",
            "pending_queries": pending_queries,
            "query_index": 0,
            "top_n": orch.default_top_n,
            "cached_at": now_utc_str(),
        }
        orch._save_cache(task_id, cache)

        s = orch._get_state(task_id)
        group_steps = {}

        for i, q in enumerate(search_queries):
            q_group = i + 1
            step_id = orch._create_or_update_step(s, task_id, "search",
                query_group=q_group, query_text=q[:300])
            group_steps[q_group] = step_id

        direct_group = len(search_queries) + 1 if direct_urls else None
        if direct_group:
            direct_label = f"Direct: {direct_urls[0][:60]}{'…' if len(direct_urls) > 1 else ''}"
            step_id = orch._create_or_update_step(s, task_id, "search",
                query_group=direct_group, query_text=direct_label)
            group_steps[direct_group] = step_id

        search_results_list = []
        for i, q in enumerate(search_queries):
            if i > 0:
                logger.info("Staggering search: sleeping 1.5s between requests...")
                await asyncio.sleep(1.5)
            res = await web_search(q, orch.default_top_n, orch._state.config)
            search_results_list.append(res)

        search_results = []
        for i, results in enumerate(search_results_list):
            q_group = i + 1
            step_id = group_steps[q_group]
            orch._log_meta(task_id, "orchestrator_search", {
                "query": search_queries[i], "results_count": len(results),
            }, step_id=step_id)
            
            if orch.step_repo:
                if not results:
                    orch.step_repo.update(step_id, status="completed", result_summary="no results")
                else:
                    orch.step_repo.update(step_id, status="completed",
                        result_summary=f"{len(results)} results")
                    
            for r in results:
                url = r.get("url")
                if url and orch.step_result_repo:
                    try:
                        orch.step_result_repo.create({
                            "id": str(uuid.uuid4()),
                            "step_id": step_id, "task_id": task_id,
                            "source_url": url,
                            "source_title": r.get("title", url[:100]),
                            "relevance_score": r.get("relevance", 0.0),
                            "novelty_score": r.get("novelty", 0.0),
                        })
                    except Exception as e:
                        logger.warning("Failed to save search step result to DB: %s", e)
                r_copy = dict(r)
                r_copy["query_group"] = q_group
                search_results.append(r_copy)

        if direct_group and direct_urls:
            step_id = group_steps[direct_group]
            orch._log_meta(task_id, "orchestrator_search", {
                "query": "direct_urls", "results_count": len(direct_urls), "urls": direct_urls,
            }, step_id=step_id)
            if orch.step_repo:
                orch.step_repo.update(step_id, status="completed",
                    result_summary=f"{len(direct_urls)} direct URL(s) queued")
            for url in direct_urls:
                if orch.step_result_repo:
                    try:
                        orch.step_result_repo.create({
                            "id": str(uuid.uuid4()),
                            "step_id": step_id, "task_id": task_id,
                            "source_url": url, "source_title": url[:100],
                            "relevance_score": 1.0, "novelty_score": 1.0,
                        })
                    except Exception as e:
                        logger.warning("Failed to save direct URL result: %s", e)
                search_results.append({
                    "url": url, "title": url[:100], "query_group": direct_group,
                })

        out_payload = SearchPayload(
            queries=payload.queries,
            direct_urls=payload.direct_urls,
            search_results=search_results
        )

        signal_flags = {"has_results": len(search_results) > 0}

        all_step_ids = list(group_steps.values())
        if search_results:
            rationale = f"Executed search queries at depth {current_depth}, retrieving {len(search_results)} search results."
        else:
            rationale = f"Executed search queries at depth {current_depth}, but no new search results were found."

        return StepOutput(
            status="completed",
            message=f"found {len(search_results)} results" if search_results else "no results found",
            payload=out_payload,
            signal_flags=signal_flags,
            step_ids=all_step_ids,
            transition_rationale=rationale
        )
