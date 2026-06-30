import asyncio
import json
import logging
from typing import Optional

from backend.utils.prompt_loader import get_prompts_dict
from backend.utils.anti_mastery import apply_anti_mastery_filter
from backend.modules.llm_client import generate_unified

logger = logging.getLogger("aaa.research_orchestrator")

# Anti-bot / paywall / garbage patterns -- skip these without LLM call
_CONTENT_JUNK_PATTERNS: list[str] = [
    "Security check required",
    "Cloudflare",
    "Please complete the security check",
    "Enable JavaScript and cookies to continue",
]


async def analyze_source_content(orch, task_id: str, url: str, title: str, content: str,
                                 query: str, goal: str, depth: int, max_depth: int,
                                 step_id: str = "") -> dict:
    """Analyze a single source via LLM (migrated from legacy tools.py)."""
    # Skip obviously garbage content (anti-bot, paywalls, empty nav wrappers)
    content_stripped = (content or "").strip()
    if len(content_stripped) < 200:
        logger.info("Skipping short content (%d chars) for %s", len(content_stripped), url[:80])
        return {
            "learnings": [],
            "gaps": [f"Content too short ({len(content_stripped)} chars) — likely paywall or block"],
            "followups": [],
            "direct_urls": [],
            "diffractive_notes": []
        }
    for junk in _CONTENT_JUNK_PATTERNS:
        if junk.lower() in content_stripped[:1000].lower():
            logger.info("Skipping junk content ('%s') for %s", junk, url[:80])
            return {
                "learnings": [],
                "gaps": [f"Blocked by anti-bot protection ('{junk}')"],
                "followups": [],
                "direct_urls": [url],
                "diffractive_notes": []
            }

    prompt_data = get_prompts_dict("research/node_analyzer.yaml")
    system_text = prompt_data.get("system", "")
    trunc_limit = getattr(orch, "_TRUNC_LLM_CONTENT", 16000)
    user_text = prompt_data.get("user", "").format(
        query=query, goal=goal, depth=depth, max_depth=max_depth,
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
    orch._log_meta(task_id, "orchestrator_digest_prompt", {
        "source_url": url, "source_title": title,
        "system_prompt": system_text[:trunc_meta_log],
        "user_prompt": user_text[:trunc_meta_log],
    }, step_id=step_id or None)

    fallback = {"learnings": [], "gaps": [], "followups": [], "direct_urls": [], "diffractive_notes": []}
    try:
        llm = getattr(orch._state, "llm_provider", None)
        if not llm:
            return fallback
        resp = await generate_unified(llm, system_prompt=system_text, user_prompt=user_text,
            expect_json=True, fallback_value=fallback,
            temperature=prompt_data.get("temperature", 0.3),
            max_tokens=prompt_data.get("max_tokens", 2048))
        result = resp.get("json_data") or resp.get("content") or {}
        if isinstance(result, str):
            result = json.loads(result)
        # Log response
        orch._log_llm_response(task_id, "orchestrator_digest_response", resp, extra={
            "source_url": url,
            "learnings_count": len(result.get("learnings", [])) if isinstance(result, dict) else 0,
        }, step_id=step_id or None)
        return result if isinstance(result, dict) else fallback
    except Exception as e:
        logger.error("Source analysis failed: %s", e)
        orch._log_meta(task_id, "orchestrator_digest_error", {"source_url": url, "error": str(e)}, step_id=step_id or None)
        return fallback


async def parallel_digest_grouped(orch, task_id: str, group_steps: dict,
                                  parsed_sources: list[dict], queries: list[str],
                                  objective: str, depth: int, max_depth: int) -> list[dict]:
    """Analyze each parsed source concurrently via LLM.

    Migrated from legacy tools._tool_parallel_digest_grouped.
    """
    sem = orch._get_semaphore()

    async def digest_one(source: dict) -> Optional[dict]:
        async with sem:
            try:
                q_group = source.get("query_group", 1)
                step_id = group_steps.get(q_group) or list(group_steps.values())[0]
                query_text = queries[q_group - 1] if (q_group - 1) < len(queries) else objective

                result = await analyze_source_content(
                    orch, task_id, source["url"], source.get("title", ""),
                    source.get("content", ""), query_text, objective, depth, max_depth,
                    step_id=step_id,
                )

                # Update the step_result row with analysis results
                try:
                    parse_step_id = None
                    if orch.step_repo:
                        steps = orch.step_repo.get_by_task(task_id)
                        parse_step = next(
                            (s for s in steps
                             if s.get("step_type") == "parallel_parse"
                             and s.get("query_group") == q_group
                             and orch._get_step_depth(s) == depth),
                            None
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
                                sr["id"], json.dumps(result, ensure_ascii=False),
                            )
                            break
                except Exception as db_err:
                    logger.warning("Failed to update step result analysis for %s: %s",
                                   source["url"][:40], db_err)

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
