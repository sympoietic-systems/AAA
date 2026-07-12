import asyncio
import json
import logging

from backend.modules.llm_client import generate_unified
from backend.services.research.steps.base import BaseResearchStep
from backend.services.research.task_state import DigestPayload, StepEnvelope, StepOutput
from backend.utils.anti_mastery import apply_anti_mastery_filter
from backend.utils.prompt_loader import get_prompts_dict
from backend.utils.research_logger import now_utc_str

logger = logging.getLogger("aaa.research_orchestrator")

# Anti-bot / paywall / garbage patterns -- skip these without LLM call
_CONTENT_JUNK_PATTERNS: list[str] = [
    "Security check required",
    "Cloudflare",
    "Please complete the security check",
    "Enable JavaScript and cookies to continue",
]


async def analyze_source_content(
    orch,
    task_id: str,
    url: str,
    title: str,
    content: str,
    query: str,
    goal: str,
    depth: int,
    max_depth: int,
    step_id: str = "",
) -> dict:
    """Analyze a single source via LLM.

    Migrated from legacy tools._analyze_source.
    """
    # Skip obviously garbage content (anti-bot, paywalls, empty nav wrappers)
    content_stripped = (content or "").strip()
    if len(content_stripped) < 200:
        logger.info("Skipping short content (%d chars) for %s", len(content_stripped), url[:80])
        return {
            "learnings": [],
            "gaps": [f"Content too short ({len(content_stripped)} chars) — likely paywall or block"],
            "followups": [],
            "direct_urls": [],
            "diffractive_notes": [],
        }
    for junk in _CONTENT_JUNK_PATTERNS:
        if junk.lower() in content_stripped[:1000].lower():
            logger.info("Skipping junk content ('%s') for %s", junk, url[:80])
            return {
                "learnings": [],
                "gaps": [f"Blocked by anti-bot protection ('{junk}')"],
                "followups": [],
                "direct_urls": [url],
                "diffractive_notes": [],
            }

    prompt_data = get_prompts_dict("research/node_analyzer.yaml")
    system_text = prompt_data.get("system", "")
    trunc_limit = getattr(orch, "_TRUNC_LLM_CONTENT", 16000)
    user_text = prompt_data.get("user", "").format(
        query=query,
        goal=goal,
        depth=depth,
        max_depth=max_depth,
        parent_findings="(orchestrator — multi-source analysis)",
        scraped_content=content[:trunc_limit],
    )
    if prompt_data.get("anti_mastery"):
        system_text = apply_anti_mastery_filter(system_text)
        user_text = apply_anti_mastery_filter(user_text)

    # Build persona context
    try:
        from backend.services.research.context_builder import ResearchContextBuilder

        builder = ResearchContextBuilder(orch._state)
        persona = await builder.build_node_context(node_query=query, node_goal=goal, depth=depth)
        if persona:
            system_text = persona + "\n\n" + system_text
    except Exception:
        logger.warning("Failed to build research context persona for node digest")
        pass

    # Log prompt
    trunc_meta_log = getattr(orch, "_TRUNC_META_LOG", 2000)
    orch._log_meta(
        task_id,
        "orchestrator_digest_prompt",
        {
            "source_url": url,
            "source_title": title,
            "system_prompt": system_text[:trunc_meta_log],
            "user_prompt": user_text[:trunc_meta_log],
        },
        step_id=step_id or None,
    )

    fallback = {"learnings": [], "gaps": [], "followups": [], "direct_urls": [], "diffractive_notes": []}
    try:
        llm = getattr(orch._state, "llm_provider", None)
        if not llm:
            return fallback
        resp = await generate_unified(
            llm,
            system_prompt=system_text,
            user_prompt=user_text,
            expect_json=True,
            fallback_value=fallback,
            temperature=prompt_data.get("temperature", 0.3),
            max_tokens=prompt_data.get("max_tokens", 2048),
        )
        result = resp.get("json_data") or resp.get("content") or {}
        if isinstance(result, str):
            result = json.loads(result)
        # Log response
        orch._log_llm_response(
            task_id,
            "orchestrator_digest_response",
            resp,
            extra={
                "source_url": url,
                "learnings_count": len(result.get("learnings", [])) if isinstance(result, dict) else 0,
            },
            step_id=step_id or None,
        )
        return result if isinstance(result, dict) else fallback
    except Exception as e:
        logger.error("Source analysis failed: %s", e)
        orch._log_meta(
            task_id, "orchestrator_digest_error", {"source_url": url, "error": str(e)}, step_id=step_id or None
        )
        return fallback


async def parallel_digest_grouped(
    orch,
    task_id: str,
    group_steps: dict,
    parsed_sources: list[dict],
    queries: list[str],
    objective: str,
    depth: int,
    max_depth: int,
) -> list[dict]:
    """Analyze each parsed source concurrently via LLM.

    Migrated from legacy tools._tool_parallel_digest_grouped.
    """
    sem = orch._get_semaphore()

    async def digest_one(source: dict) -> dict | None:
        async with sem:
            try:
                q_group = source.get("query_group", 1)
                step_id = group_steps.get(q_group) or list(group_steps.values())[0]
                query_text = queries[q_group - 1] if (q_group - 1) < len(queries) else objective

                result = await analyze_source_content(
                    orch,
                    task_id,
                    source["url"],
                    source.get("title", ""),
                    source.get("content", ""),
                    query_text,
                    objective,
                    depth,
                    max_depth,
                    step_id=step_id,
                )

                # Update the step_result row with analysis results
                try:
                    parse_step_id = None
                    if orch.step_repo:
                        steps = orch.step_repo.get_by_task(task_id)
                        parse_step = next(
                            (
                                s
                                for s in steps
                                if s.get("step_type") == "parallel_parse"
                                and s.get("query_group") == q_group
                                and orch._get_step_depth(s) == depth
                            ),
                            None,
                        )
                        if parse_step:
                            parse_step_id = parse_step.get("id")

                    target_step_id = parse_step_id or step_id
                    if target_step_id:
                        step_srcs = orch.step_result_repo.get_by_step(target_step_id)
                    else:
                        step_srcs = orch.step_result_repo.get_by_task(task_id)

                    for sr in step_srcs:
                        if sr["source_url"] == source["url"]:
                            orch.step_result_repo.update_analysis(
                                sr["id"],
                                json.dumps(result, ensure_ascii=False),
                            )
                            break
                except Exception as db_err:
                    logger.warning("Failed to update step result analysis for %s: %s", source["url"][:40], db_err)

                return {
                    "source_url": source["url"],
                    "source_title": source.get("title"),
                    "result": result,
                    "query_group": q_group,
                }
            except Exception as e:
                logger.warning("Digest failed for %s: %s", source.get("url", "")[:80], e)
                return None

    tasks = [digest_one(s) for s in parsed_sources]
    gathered = await asyncio.gather(*tasks)
    return [g for g in gathered if g is not None]


class DigestStep(BaseResearchStep):
    @property
    def step_type(self) -> str:
        return "digest"

    async def preview(self, orch, envelope: StepEnvelope, state: dict) -> dict:
        task_id = envelope.task_id
        objective = envelope.objective
        current_depth = envelope.current_depth
        max_depth = envelope.max_depth

        payload: DigestPayload = envelope.payload
        parsed_sources = payload.parsed_sources_cache or []

        # Re-hydrate parsed_sources_cache from database if empty
        if not parsed_sources and orch.step_repo and orch.step_result_repo:
            steps = orch.step_repo.get_by_task(task_id)
            parse_steps = [
                st
                for st in steps
                if st["step_type"] == "parallel_parse"
                and st["status"] == "completed"
                and orch._get_step_depth(st) == current_depth
            ]
            if parse_steps:
                parsed_sources = []
                for ps in parse_steps:
                    db_results = orch.step_result_repo.get_by_step(ps["id"])
                    for r in db_results:
                        parsed_sources.append(
                            {
                                "id": r["id"],
                                "url": r["source_url"],
                                "title": r["source_title"],
                                "content": r["raw_content"],
                                "query_group": ps.get("query_group", 1),
                            }
                        )

        sources = [
            {
                "url": src["url"],
                "title": src.get("title", ""),
                "snippet": src.get("content", "")[:300] + "...",
                "query_group": src.get("query_group"),
            }
            for src in parsed_sources
        ]

        system_prompt = ""
        user_prompt = ""

        if parsed_sources:
            try:
                first_src = parsed_sources[0]
                prompt_data = get_prompts_dict("research/node_analyzer.yaml")
                system_prompt = prompt_data.get("system", "")

                q_group = first_src.get("query_group", 1)
                q_text = objective
                if state and state.get("plan") and state["plan"].get("search_queries"):
                    sq = state["plan"]["search_queries"]
                    if isinstance(sq, list) and 0 <= (q_group - 1) < len(sq):
                        q_text = sq[q_group - 1]

                user_prompt = prompt_data.get("user", "").format(
                    query=q_text,
                    goal=objective,
                    depth=current_depth,
                    max_depth=max_depth,
                    parent_findings="(orchestrator — multi-source analysis)",
                    scraped_content=first_src.get("content", "")[:3000] + "\n[Content Truncated for Preview]",
                )

                if prompt_data.get("anti_mastery"):
                    system_prompt = apply_anti_mastery_filter(system_prompt)
                    user_prompt = apply_anti_mastery_filter(user_prompt)

                try:
                    from backend.services.research.context_builder import ResearchContextBuilder

                    builder = ResearchContextBuilder(orch._state)
                    persona = await builder.build_node_context(
                        node_query=q_text, node_goal=objective, depth=current_depth
                    )
                    if persona:
                        system_prompt = persona + "\n\n" + system_prompt
                except Exception:
                    logger.warning("Failed to build research context persona for node digest preview")
                    pass
            except Exception as e:
                logger.warning("Failed to prepare digest prompt preview: %s", e)

        return {
            "phase": "digesting",
            "sources": sources,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "model": getattr(orch._state, "llm_provider", None)
            and getattr(orch._state.llm_provider, "model_id", "(auto)")
            or "(auto)",
            "temperature": 0.3,
            "max_tokens": 2048,
            "cached_at": now_utc_str(),
        }

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
                st
                for st in steps
                if st["step_type"] == "parallel_parse"
                and st["status"] == "completed"
                and orch._get_step_depth(st) == current_depth
            ]
            if parse_steps:
                parsed_sources = []
                for ps in parse_steps:
                    db_results = orch.step_result_repo.get_by_step(ps["id"])
                    for r in db_results:
                        parsed_sources.append(
                            {
                                "id": r["id"],
                                "url": r["source_url"],
                                "title": r["source_title"],
                                "content": r["raw_content"],
                                "query_group": ps.get("query_group", 1),
                            }
                        )

        query_groups = sorted({src.get("query_group", 1) for src in parsed_sources}) or [1]

        # Resolve queries
        plan_queries = []
        state = orch._get_state(task_id)
        if state.get("plan") and isinstance(state["plan"], dict):
            plan_queries = state["plan"].get("search_queries", [objective])
        else:
            plan_queries = [objective]

        last_refl = state.get("last_reflection") or {}
        queries = (
            last_refl.get("next_queries") if (current_depth > 0 and last_refl.get("next_queries")) else plan_queries
        )

        s = orch._get_state(task_id)
        group_steps = {}
        for q_group in query_groups:
            q_text = queries[q_group - 1] if (q_group - 1) < len(queries) else objective
            step_id = orch._create_or_update_step(s, task_id, "digest", query_group=q_group, query_text=q_text[:300])
            group_steps[q_group] = step_id

        # Call local parallel_digest_grouped directly rather than through orch delegate
        digest_results = await parallel_digest_grouped(
            orch,
            task_id,
            group_steps,
            parsed_sources,
            queries,
            objective,
            current_depth,
            max_depth,
        )

        if orch.step_repo:
            for q_group, step_id in group_steps.items():
                digested_for_group = [dr for dr in digest_results if dr.get("query_group") == q_group]
                orch.step_repo.update(
                    step_id, status="completed", result_summary=f"digested {len(digested_for_group)} sources"
                )

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
                    f"[{dr['source_title'] or dr['source_url'][:80]}]: " + learning for learning in learnings
                )
            if isinstance(r, dict):
                followups.extend(r.get("followups", []))
                gaps.extend(r.get("gaps", []))

        out_payload = DigestPayload(
            parsed_sources_cache=parsed_sources, learnings=all_learnings, followups=followups, gaps=gaps
        )

        all_step_ids = list(group_steps.values())
        if all_learnings:
            rationale = f"Successfully digested content and extracted {len(all_learnings)} key learnings, identifying {len(gaps)} remaining information gaps."
        else:
            rationale = "Digested the extracted text content, but no significant new learnings could be found."

        return StepOutput(
            status="completed",
            message=f"digested {len(parsed_sources)} sources, got {len(all_learnings)} learnings",
            payload=out_payload,
            new_findings=new_findings,
            step_ids=all_step_ids,
            transition_rationale=rationale,
        )
