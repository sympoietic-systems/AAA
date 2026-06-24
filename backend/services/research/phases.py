"""Research phase implementations extracted from SomaticResearchOrchestrator.

Each method receives the orchestrator instance as its first argument ('orch')
so it has full access to state, repos, and utilities.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.modules.llm_client import generate_unified
from backend.services.research.search_tool import web_search
from backend.utils.prompt_loader import get_prompts_dict
from backend.utils.anti_mastery import apply_anti_mastery_filter
from backend.services.research.context_builder import ResearchContextBuilder
from backend.utils.research_logger import now_utc_str

logger = logging.getLogger("aaa.research_orchestrator")


class ResearchPhases:
    @staticmethod
    async def step_plan(orch, task_id: str, s: dict) -> dict:
        logger.info("Step: PLANNING — %s", ResearchPhases._lc(orch, task_id, "planning"))
        s["step_number"] += 1
        step_id = str(uuid.uuid4())

        plan = await _phase_plan(orch, task_id, s["objective"], s["max_depth"], s["budget"], step_id=step_id)
        s["plan"] = plan
        s["plan_id"] = plan["id"]

        orch.step_repo.create({
            "id": step_id, "task_id": task_id, "plan_id": plan["id"],
            "step_number": s["step_number"], "step_type": "plan",
            "status": "completed", "started_at": now_utc_str(),
            "result_summary": f"{len(plan.get('search_queries',[]))} queries planned",
        })
        try:
            orch.step_repo.update(step_id, step_data=json.dumps(
                {"plan": plan, "depth": 0}, default=str, ensure_ascii=False))
        except Exception:
            pass
        orch._log_meta(task_id, "orchestrator_plan", {"plan": plan}, step_id=step_id)
        s["phase"] = "searching"
        return {"plan": plan, "plan_id": plan["id"], "step_id": step_id}

    @staticmethod
    async def step_search(orch, task_id: str, s: dict) -> dict:
        raw_queries = s["plan"].get("search_queries", [s["objective"]])
        if s["current_depth"] > 0 and s["last_reflection"].get("next_queries"):
            raw_queries = s["last_reflection"]["next_queries"]

        search_queries = []
        direct_urls = []

        if s.get("last_reflection") and isinstance(s["last_reflection"], dict):
            for u in s["last_reflection"].get("next_direct_urls", []):
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

        logger.info("Step: SEARCHING %d queries in parallel — %s", len(pending_queries),
                     ResearchPhases._lc(orch, task_id, "searching"))

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

        tasks_list = [web_search(q, orch.default_top_n, orch._state.config) for q in search_queries]
        search_results_list = await asyncio.gather(*tasks_list)

        search_results = []
        for i, results in enumerate(search_results_list):
            q_group = i + 1
            step_id = group_steps[q_group]
            orch._log_meta(task_id, "orchestrator_search", {
                "query": search_queries[i], "results_count": len(results),
            }, step_id=step_id)
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

        s["search_results_cache"] = search_results
        s["parsed_sources_cache"] = []
        s["phase"] = "parsing"
        if not search_results:
            s["phase"] = "reflecting"

        return {
            "queries": pending_queries,
            "results_count": len(search_results),
            "urls": [{"url": r.get("url", ""), "title": r.get("title", r.get("url", "")),
                      "query_group": r.get("query_group")} for r in search_results],
        }

    @staticmethod
    async def step_parse(orch, task_id: str, s: dict) -> dict:
        logger.info("Step: PARSING — %s", ResearchPhases._lc(orch, task_id, "parsing"))
        search_cache = s.get("search_results_cache", [])
        query_groups = sorted(list(set(r.get("query_group", 1) for r in search_cache))) or [1]

        group_steps = {}
        for q_group in query_groups:
            step_id = orch._create_or_update_step(s, task_id, "parallel_parse",
                query_group=q_group, query_text="")
            group_steps[q_group] = step_id

        parsed = await orch._tool_parallel_parse_grouped(
            task_id, group_steps, search_cache, s["plan_id"],
        )
        for q_group, step_id in group_steps.items():
            parsed_for_group = [p for p in parsed if p.get("query_group") == q_group]
            orch.step_repo.update(step_id, status="completed",
                result_summary=f"parsed {len(parsed_for_group)} sources")

        s["parsed_sources_cache"] = parsed
        s["phase"] = "digesting" if parsed else "reflecting"

        urls = [{"url": p["url"], "title": p.get("title", p["url"]), "query_group": p.get("query_group")} for p in parsed]
        cache = orch._load_cache(task_id)
        cache["parsing"] = {"phase": "parsing", "urls": urls, "cached_at": now_utc_str()}
        orch._save_cache(task_id, cache)

        return {"parsed_count": len(parsed), "parsed_urls": urls}

    @staticmethod
    async def step_digest(orch, task_id: str, s: dict) -> dict:
        logger.info("Step: DIGESTING — %s", ResearchPhases._lc(orch, task_id, "digesting"))

        if not s.get("parsed_sources_cache") and orch.step_repo and orch.step_result_repo:
            steps = orch.step_repo.get_by_task(task_id)
            current_depth = s.get("current_depth", 0)
            parse_steps = [
                st for st in steps
                if st["step_type"] == "parallel_parse" and st["status"] == "completed"
                and orch._get_step_depth(st) == current_depth
            ]
            if parse_steps:
                s["parsed_sources_cache"] = []
                for ps in parse_steps:
                    db_results = orch.step_result_repo.get_by_step(ps["id"])
                    for r in db_results:
                        s["parsed_sources_cache"].append({
                            "id": r["id"], "url": r["source_url"],
                            "title": r["source_title"], "content": r["raw_content"],
                            "query_group": ps.get("query_group", 1),
                        })

        parsed_sources = s.get("parsed_sources_cache", [])
        query_groups = sorted(list(set(src.get("query_group", 1) for src in parsed_sources))) or [1]

        group_steps = {}
        queries = s["plan"].get("search_queries", [s["objective"]])
        if s["current_depth"] > 0 and s["last_reflection"].get("next_queries"):
            queries = s["last_reflection"]["next_queries"]

        for q_group in query_groups:
            q_text = queries[q_group - 1] if (q_group - 1) < len(queries) else s["objective"]
            step_id = orch._create_or_update_step(s, task_id, "digest",
                query_group=q_group, query_text=q_text[:300])
            group_steps[q_group] = step_id

        digest_results = await orch._tool_parallel_digest_grouped(
            task_id, group_steps, parsed_sources,
            queries, s["objective"], s["current_depth"], s["max_depth"],
        )
        for q_group, step_id in group_steps.items():
            digested_for_group = [dr for dr in digest_results if dr.get("query_group") == q_group]
            orch.step_repo.update(step_id, status="completed",
                result_summary=f"digested {len(digested_for_group)} sources")

        new_learnings = 0
        for dr in digest_results:
            r = dr.get("result", {})
            learnings = r.get("learnings", []) if isinstance(r, dict) else []
            if learnings:
                new_learnings += len(learnings)
                s["all_findings"].extend(
                    f"[{dr['source_title'] or dr['source_url'][:80]}]: " + l
                    for l in learnings
                )
            s["sources_analyzed"] += 1

        if new_learnings == 0:
            s["stagnation_counter"] += 1
        else:
            s["stagnation_counter"] = 0

        cycle_followups, cycle_direct_urls, cycle_gaps, seen_signals = [], [], [], set()
        for dr in digest_results:
            r = dr.get("result", {})
            if not isinstance(r, dict):
                continue
            source_info = dr.get("source_title") or dr.get("source_url", "")[:80]
            for item in r.get("followups", []):
                if item and item not in seen_signals:
                    seen_signals.add(item)
                    cycle_followups.append(f"[{source_info}]: {item}")
            for item in r.get("direct_urls", []):
                if item and item not in seen_signals:
                    seen_signals.add(item)
                    cycle_direct_urls.append(item)
            for item in r.get("gaps", []):
                if item and item not in seen_signals:
                    seen_signals.add(item)
                    cycle_gaps.append(f"[{source_info}]: {item}")
        s["digest_signals"] = {
            "followups": cycle_followups,
            "direct_urls": cycle_direct_urls,
            "gaps": cycle_gaps,
        }

        s["phase"] = "reflecting"

        source_urls = [src.get("url", "") for src in parsed_sources]
        cache = orch._load_cache(task_id)
        cache["digesting"] = {
            "phase": "digesting", "query": ", ".join(queries),
            "objective": s["objective"], "depth": s["current_depth"],
            "max_depth": s["max_depth"], "source_urls": source_urls,
            "cached_at": now_utc_str(),
        }
        orch._save_cache(task_id, cache)

        return {
            "digested_count": len(digest_results),
            "new_learnings": new_learnings,
            "total_learnings": len(s["all_findings"]),
            "sources_analyzed": s["sources_analyzed"],
        }

    @staticmethod
    async def step_reflect(orch, task_id: str, s: dict) -> dict:
        logger.info("Step: REFLECTING — %s", ResearchPhases._lc(orch, task_id, "reflecting"))
        step_id = orch._create_or_update_step(s, task_id, "reflect")
        reflection = await orch._tool_reflect(
            task_id, s["objective"], s["plan"].get("goal", s["objective"]),
            s["current_depth"], s["max_depth"],
            s["all_findings"], s["last_reflection"],
            digest_signals=s.get("digest_signals", {}), step_id=step_id,
        )
        s["last_reflection"] = reflection
        completeness = reflection.get("completeness_score", 0)
        orch.step_repo.update(step_id, status="completed",
            result_summary=f"completeness: {completeness:.2f}")
        orch._log_meta(task_id, "orchestrator_reflect", {
            "depth": s["current_depth"], "completeness": completeness,
            "total_findings": len(s["all_findings"]),
        }, step_id=step_id)
        s["phase"] = "evaluating"
        return {"completeness": completeness, "step_id": step_id}

    @staticmethod
    async def step_evaluate(orch, task_id: str, s: dict) -> dict:
        logger.info("Step: EVALUATING — %s", ResearchPhases._lc(orch, task_id, "evaluating"))
        step_id = orch._create_or_update_step(s, task_id, "evaluate")
        should_stop, stop_reason = await orch._tool_evaluate(
            task_id=task_id, step_id=step_id,
            objective=s["objective"], depth=s["current_depth"],
            max_depth=s["max_depth"], sources=s["sources_analyzed"],
            reflection=s["last_reflection"], stagnation=s["stagnation_counter"],
        )
        orch._log_meta(task_id, "orchestrator_evaluate", {
            "decision": "stop" if should_stop else "continue",
            "reason": stop_reason, "depth": s["current_depth"],
        }, step_id=step_id)
        orch.step_repo.update(step_id, status="completed",
            result_summary=f"{'STOP' if should_stop else 'CONTINUE'}: {stop_reason}")
        if should_stop:
            s["phase"] = "synthesizing"
        else:
            s["current_depth"] += 1
            s["query_index"] = 0
            s["phase"] = "searching"
        return {"should_stop": should_stop, "reason": stop_reason,
                "current_depth": s["current_depth"], "step_id": step_id}

    @staticmethod
    async def step_synthesize(orch, task_id: str, s: dict) -> dict:
        logger.info("Step: SYNTHESIZING — %s", ResearchPhases._lc(orch, task_id, "synthesizing"))
        step_id = orch._create_or_update_step(s, task_id, "synthesize")
        orch._log_meta(task_id, "orchestrator_synthesize_start", {
            "total_findings": len(s["all_findings"]),
            "sources": s["sources_analyzed"], "depth": s["current_depth"],
        }, step_id=step_id)
        result_summary = await orch._phase_synthesize(
            task_id, s["objective"],
            s["plan"].get("goal", s["objective"]) if s["plan"] else s["objective"],
            s["all_findings"], s["sources_analyzed"], step_id=step_id,
        )
        orch.task_repo.update(task_id,
            branches_created=s["step_number"],
            assets_harvested=s["sources_analyzed"],
            result_summary=result_summary,
        )
        orch.step_repo.update(step_id, status="completed",
            result_summary=f"{s['sources_analyzed']} sources, {len(s['all_findings'])} findings")
        orch._log_meta(task_id, "orchestrator_complete", {
            "steps": s["step_number"], "sources": s["sources_analyzed"],
            "findings": len(s["all_findings"]), "depth": s["current_depth"],
        }, step_id=step_id)
        s["phase"] = "complete"
        return {"result_summary": result_summary,
                "branches_created": s["step_number"],
                "assets_harvested": s["sources_analyzed"]}

    @staticmethod
    def _lc(orch, task_id: str, phase: str) -> str:
        return f"task={task_id[:8]} phase={phase}"


async def _phase_plan(orch, task_id, objective, max_depth, budget,
                       previous_context: str = "", step_id: str = "") -> dict:
    prompt_data = get_prompts_dict("research/orchestrator_planner.yaml")
    cached = orch._get_cached_phase(task_id, "planning")
    if cached and cached.get("persona") and cached.get("system_prompt") and cached.get("user_prompt"):
        persona = cached["persona"]
        system_text = cached["system_prompt"]
        user_text = cached["user_prompt"]
    else:
        persona = await orch._build_orchestrator_persona(objective)
        system_text = persona + "\n\n" + prompt_data.get("system", "")
        fmt = {"objective": objective, "max_depth": max_depth, "budget_limit_usd": budget}
        user_template = prompt_data.get("user_with_context", prompt_data.get("user", "")) if previous_context else prompt_data.get("user", "")
        user_text = user_template.format(**fmt)
        if prompt_data.get("anti_mastery"):
            system_text = apply_anti_mastery_filter(system_text)
            user_text = apply_anti_mastery_filter(user_text)
        cache = orch._load_cache(task_id)
        cache["planning"] = {
            "phase": "planning", "persona": persona, "objective": objective,
            "max_depth": max_depth, "budget_limit_usd": budget,
            "system_prompt": system_text, "user_prompt": user_text,
            "temperature": prompt_data.get("temperature", 0.4),
            "max_tokens": prompt_data.get("max_tokens", 1024),
            "cached_at": now_utc_str(),
        }
        orch._save_cache(task_id, cache)

    plan_json = {"goal": objective, "search_queries": [objective], "n_results_per_query": 3, "estimated_depth": 1}
    try:
        llm = getattr(orch._state, "llm_provider", None)
        if llm:
            orch._log_meta(task_id, "orchestrator_plan_prompt", {
                "system_prompt": system_text[:8000], "user_prompt": user_text[:8000],
            }, step_id=step_id or None)
            gen_kwargs: dict = {
                "temperature": prompt_data.get("temperature", 0.4),
                "max_tokens": prompt_data.get("max_tokens", 1024),
            }
            thinking_cfg = prompt_data.get("thinking", {})
            if isinstance(thinking_cfg, dict) and thinking_cfg.get("enabled"):
                gen_kwargs["thinking_override"] = True
                gen_kwargs["reasoning_effort"] = thinking_cfg.get("effort", "high")
            resp = await generate_unified(llm, system_prompt=system_text, user_prompt=user_text,
                expect_json=True, fallback_value=plan_json, **gen_kwargs)
            orch._log_llm_response(task_id, "orchestrator_plan_response", resp, step_id=step_id or None)
            result = resp.get("json_data") or resp.get("content") or {}
            if isinstance(result, str):
                result = json.loads(result)
            if isinstance(result, dict) and result.get("search_queries"):
                plan_json = result
    except Exception as e:
        logger.warning("Plan generation failed, using default: %s", e)

    plan_id = str(uuid.uuid4())
    orch.plan_repo.create({
        "id": plan_id, "task_id": task_id,
        "plan_json": json.dumps(plan_json, ensure_ascii=False),
        "status": "active",
    })
    return {"id": plan_id, **plan_json}
