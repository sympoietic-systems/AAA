"""Research tool methods -- parse, digest, reflect, evaluate.

Extracted from SomaticResearchOrchestrator. Each function takes the
orchestrator instance as its first parameter ("orch").
"""

import asyncio
import json
import logging
import re
import uuid
from pathlib import Path
from typing import Optional

from backend.modules.llm_client import generate_unified
from backend.services.research.sensory_affordances import select_and_fetch, is_crawl4ai_available, fetch_via_crawl4ai
from backend.services.research.context_builder import ResearchContextBuilder
from backend.utils.prompt_loader import get_prompts_dict
from backend.utils.anti_mastery import apply_anti_mastery_filter
from backend.utils.research_logger import now_utc_str

logger = logging.getLogger("aaa.research_tools")


async def _tool_parallel_parse_grouped(orch, task_id, group_steps, search_results, plan_id) -> list[dict]:
        """Fetch all search result URLs in parallel, saving HTML to disk. Skips already-fetched URLs.
        Uses local DB cache lookup to avoid redundant network requests.
        """
        sem = orch._get_semaphore()

        # Dedup: for each URL, check if we already have its content in the DB
        # (either from a scraped_asset record or a step_result).
        # If we do, reuse it so we avoid a redundant network fetch but still
        # pass the content into this cycle's digest step.
        new_urls = []
        reused = []
        for r in search_results:
            url = r.get("url", "")
            q_group = r.get("query_group", 1)
            step_id = group_steps.get(q_group) or (list(group_steps.values())[0] if group_steps else None)
            cached_content = None

            # Check the step_result table for existing raw_content for this URL in this task
            if orch.step_result_repo:
                try:
                    task_results = orch.step_result_repo.get_by_task(task_id)
                    for er in task_results:
                        if er.get("source_url") == url and er.get("raw_content") and not er["raw_content"].startswith("Error:"):
                            cached_content = er["raw_content"]
                            break
                except Exception:
                    pass

            if cached_content:
                # Content already in DB — create a new step_result row linked to THIS cycle's step_id
                logger.info("DB cache hit, reusing content for URL: %s", url[:80])
                if orch.step_result_repo and step_id:
                    try:
                        result_id = str(uuid.uuid4())
                        orch.step_result_repo.create({
                            "id": result_id, "step_id": step_id, "task_id": task_id,
                            "source_url": url, "source_title": r.get("title", url),
                            "raw_content": cached_content,
                            "raw_file_path": "",
                        })
                        reused.append({
                            "id": result_id, "url": url, "title": r.get("title", url),
                            "content": cached_content, "query_group": q_group,
                        })
                    except Exception as e:
                        logger.warning("Failed to create reused step_result for %s: %s", url[:80], e)
            else:
                new_urls.append(r)

        if reused:
            logger.info("Reused %d cached pages, fetching %d new URLs — %s",
                        len(reused), len(new_urls), orch._log_context(task_id, "parsing"))

        # Fetch truly-new URLs in parallel
        async def fetch_one(url: str, title: str, q_group: int) -> Optional[dict]:
            step_id = group_steps.get(q_group)
            if not step_id:
                step_id = list(group_steps.values())[0]

            async with sem:
                try:
                    from backend.services.research.sensory_affordances import select_and_fetch, is_crawl4ai_available, fetch_via_crawl4ai
                    # Try Jina Reader first (cloud service, handles anti-bot better),
                    # then Crawl4AI as local fallback
                    content = await select_and_fetch(url_or_query=url, task_type="single_url",
                                                     config=orch._state.config)
                    # If tiered gave empty content but Crawl4AI is available, try it directly
                    if not content and is_crawl4ai_available():
                        try:
                            content = await fetch_via_crawl4ai(url, config=orch._state.config)
                        except RuntimeError:
                            pass
                    if not content:
                        logger.warning("All backends returned empty content for %s", url[:80])
                        if orch.step_result_repo:
                            try:
                                orch.step_result_repo.create({
                                    "id": str(uuid.uuid4()), "step_id": step_id, "task_id": task_id,
                                    "source_url": url, "source_title": title,
                                    "raw_content": "Error: Empty content returned from all backends",
                                    "raw_file_path": None,
                                })
                            except Exception as db_err:
                                logger.warning("Failed to save parse empty result to DB: %s", db_err)
                        return None

                    # Save HTML to disk (relative to backend/ directory)
                    file_path = ""
                    if orch.html_archive:
                        try:
                            base = Path(__file__).resolve().parent.parent  # backend/
                            task_dir = base / "data" / "uploads" / "research" / task_id
                            task_dir.mkdir(parents=True, exist_ok=True)
                            safe_name = f"page_{uuid.uuid4().hex[:8]}.html"
                            file_path = str(task_dir / safe_name)
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write(content[:orch._TRUNC_HTML_ARCHIVE])
                        except Exception:
                            logger.warning("Failed to archive HTML for %s", url[:80])

                    result_id = str(uuid.uuid4())
                    orch.step_result_repo.create({
                        "id": result_id, "step_id": step_id, "task_id": task_id,
                        "source_url": url, "source_title": title,
                        "raw_content": content[:orch._TRUNC_STEP_RESULT],
                        "raw_file_path": file_path,
                    })
                    return {"id": result_id, "url": url, "title": title, "content": content, "query_group": q_group}
                except Exception as e:
                    logger.warning("Fetch failed for %s: %s", url[:80], e)
                    if orch.step_result_repo:
                        try:
                            orch.step_result_repo.create({
                                "id": str(uuid.uuid4()), "step_id": step_id, "task_id": task_id,
                                "source_url": url, "source_title": title,
                                "raw_content": f"Error: Fetch failed: {str(e)[:300]}",
                                "raw_file_path": None,
                            })
                        except Exception as db_err:
                            logger.warning("Failed to save parse error result to DB: %s", db_err)
                    return None

        tasks = []
        seen_urls_in_batch = set()
        for r in new_urls:
            url = r["url"]
            if url not in seen_urls_in_batch:
                seen_urls_in_batch.add(url)
                tasks.append(fetch_one(url, r.get("title", url), r.get("query_group", 1)))

        gathered = await asyncio.gather(*tasks)
        fetched = [g for g in gathered if g is not None]
        return reused + fetched

async def _tool_parallel_digest_grouped(orch, task_id, group_steps, parsed_sources,
                                            queries, objective, depth, max_depth) -> list[dict]:
        """Analyze each parsed source concurrently via LLM, saving results under the correct step_id."""
        sem = orch._get_semaphore()

        async def digest_one(source: dict) -> Optional[dict]:
            async with sem:
                try:
                    q_group = source.get("query_group", 1)
                    step_id = group_steps.get(q_group)
                    if not step_id:
                        step_id = list(group_steps.values())[0]

                    query_text = queries[q_group - 1] if (q_group - 1) < len(queries) else objective
                    
                    result = await _analyze_source(orch,
                        task_id, source["url"], source.get("title", ""),
                        source.get("content", ""), query_text, objective, depth, max_depth,
                        step_id=step_id,
                    )
                    # Update the step result with analysis — scope to the CURRENT step_id
                    # to avoid overwriting results from the same URL in previous cycles.
                    try:
                        parse_step_id = None
                        if orch.step_repo:
                            steps = orch.step_repo.get_by_task(task_id)
                            parse_step = next((s for s in steps if s.get("step_type") == "parallel_parse" and s.get("query_group") == q_group and orch._get_step_depth(s) == depth), None)
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
                                break  # stop at first match within this step
                    except Exception as db_err:
                        logger.warning("Failed to update step result analysis for %s: %s", source["url"][:40], db_err)
                    return {"source_url": source["url"], "source_title": source.get("title"),
                            "result": result, "query_group": q_group}
                except Exception as e:
                    logger.warning("Digest failed for %s: %s", source.get("url", "")[:80], e)
                    return None

        tasks = [digest_one(s) for s in parsed_sources]
        gathered = await asyncio.gather(*tasks)
        return [g for g in gathered if g is not None]

# Anti-bot / paywall / garbage patterns -- skip these without LLM call
_CONTENT_JUNK_PATTERNS: list[str] = [
    "Security check required",
    "Cloudflare",
    "Please complete the security check",
    "Enable JavaScript and cookies to continue",
]

async def _analyze_source(orch, task_id, url, title, content, query, goal, depth, max_depth, step_id: str = "") -> dict:
        """Analyze a single source via LLM (reuses node_analyzer prompt)."""
        # Skip obviously garbage content (anti-bot, paywalls, empty nav wrappers)
        content_stripped = (content or "").strip()
        if len(content_stripped) < 200:
            logger.info("Skipping short content (%d chars) for %s", len(content_stripped), url[:80])
            return {"learnings": [], "gaps": [f"Content too short ({len(content_stripped)} chars) — likely paywall or block"], "followups": [], "direct_urls": [], "diffractive_notes": []}
        for junk in _CONTENT_JUNK_PATTERNS:
            if junk.lower() in content_stripped[:1000].lower():
                logger.info("Skipping junk content ('%s') for %s", junk, url[:80])
                return {"learnings": [], "gaps": [f"Blocked by anti-bot protection ('{junk}')"], "followups": [], "direct_urls": [url], "diffractive_notes": []}

        prompt_data = get_prompts_dict("research/node_analyzer.yaml")
        system_text = prompt_data.get("system", "")
        user_text = prompt_data.get("user", "").format(
            query=query, goal=goal, depth=depth, max_depth=max_depth,
            parent_findings="(orchestrator — multi-source analysis)",
            scraped_content=content[:orch._TRUNC_LLM_CONTENT],
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
        orch._log_meta(task_id, "orchestrator_digest_prompt", {
            "source_url": url, "source_title": title,
            "system_prompt": system_text[:orch._TRUNC_META_LOG],
            "user_prompt": user_text[:orch._TRUNC_META_LOG],
        }, step_id=step_id or None)

        fallback = {"learnings": [], "gaps": [], "followups": [], "direct_urls": [], "diffractive_notes": []}
        try:
            llm = getattr(orch._state, "llm_provider", None)
            if not llm:
                return fallback
            from backend.modules.llm_client import generate_unified
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

async def _tool_reflect(orch, task_id, objective, goal, depth, max_depth,
                             all_findings, previous_reflection,
                             digest_signals: dict = None,
                             step_id: str = "") -> dict:
        """Multi-round LLM reflection on accumulated findings.
        
        digest_signals: dict with keys followups, direct_urls, gaps — collected
        from all digest results in this cycle. Injected into prompt so the LLM
        can use concrete pointers when generating next_queries.
        """
        prompt_data = get_prompts_dict("research/orchestrator_reflect.yaml")

        # Try cache first for persona, system prompt, and user prompt (matching depth)
        cached = orch._get_cached_phase(task_id, "reflecting")
        if (
            cached
            and cached.get("current_depth") == depth
            and cached.get("system_prompt")
            and cached.get("user_prompt")
        ):
            logger.info("Using cached preview prompts for reflecting phase (depth %d)", depth)
            system_text = cached["system_prompt"]
            user_text = cached["user_prompt"]
            
            orch._log_meta(task_id, "orchestrator_reflect_prompt", {
                "system_prompt": system_text[:2000],
                "user_prompt": user_text[:2000],
            }, step_id=step_id or None)

            latest_result = {}
            try:
                from backend.modules.llm_client import generate_unified
                llm = getattr(orch._state, "llm_provider", None)
                if llm:
                    resp = await generate_unified(llm, system_prompt=system_text, user_prompt=user_text,
                        expect_json=True,
                        fallback_value={"completeness_score": 0.5, "next_queries": [], "next_direct_urls": []},
                        temperature=prompt_data.get("temperature", 0.5),
                        max_tokens=prompt_data.get("max_tokens", 2048))
                    result = resp.get("json_data") or resp.get("content") or {}
                    if isinstance(result, str):
                        result = json.loads(result)
                    if isinstance(result, dict):
                        latest_result = result
                        orch._log_llm_response(task_id, "orchestrator_reflect_response", resp, extra={
                            "completeness": result.get("completeness_score", 0),
                        }, step_id=step_id or None)
                        if step_id:
                            orch._save_llm_response_to_step_data(step_id, resp)
            except Exception as e:
                logger.warning("Reflection failed with cached preview: %s", e)

            return latest_result or {"completeness_score": 0.3, "next_queries": [], "next_direct_urls": [], "reflection": "No reflection"}

        if cached and cached.get("persona") and cached.get("system_prompt"):
            persona = cached["persona"]
            system_text = cached["system_prompt"]
        else:
            persona = await orch._build_orchestrator_persona(objective)
            system_text = persona + "\n\n" + prompt_data.get("system", "")
            if prompt_data.get("anti_mastery"):
                system_text = apply_anti_mastery_filter(system_text)
            # Cache for next use
            cache = orch._load_cache(task_id)
            cache["reflecting"] = {
                "phase": "reflecting",
                "persona": persona,
                "objective": objective,
                "goal": goal,
                "system_prompt": system_text,
                "cached_at": now_utc_str(),
            }
            orch._save_cache(task_id, cache)

        # Build digest signals block for prompt injection
        signals = digest_signals or {}

        parsed_urls_list = orch._get_parsed_urls(task_id)

        # Extract findings of the current cycle from the DB
        current_cycle_findings = []
        if orch.step_repo and orch.step_result_repo:
            try:
                steps = orch.step_repo.get_by_task(task_id)
                current_parse_steps = [
                    st for st in steps
                    if st.get("step_type") == "parallel_parse" and orch._get_step_depth(st) == depth
                ]
                for ps in current_parse_steps:
                    db_results = orch.step_result_repo.get_by_step(ps["id"])
                    for r in db_results:
                        if r.get("analyzed_json"):
                            try:
                                analysis = json.loads(r["analyzed_json"])
                                learnings = analysis.get("learnings", [])
                                title = r.get("source_title") or r.get("source_url", "")[:80]
                                for l in learnings:
                                    current_cycle_findings.append(f"[{title}]: {l}")
                            except Exception:
                                pass
            except Exception as e:
                logger.warning("Failed to retrieve current cycle findings: %s", e)

        # Fallback if DB fetch returned nothing
        if not current_cycle_findings:
            current_cycle_findings = all_findings

        # Compute historical findings
        historical_set = set(all_findings) - set(current_cycle_findings)
        historical_findings = [f for f in all_findings if f in historical_set]

        # Compress findings and extract sources map globally
        all_to_compress = current_cycle_findings + historical_findings
        formatted_urls, compressed_all, compressed_followups, compressed_gaps = _apply_unified_references(orch,
            parsed_urls_list,
            all_to_compress,
            signals.get("followups", []),
            signals.get("gaps", []),
        )
        
        parsed_urls_text = "\n".join(formatted_urls) or "(none)"
        compressed_current = compressed_all[:len(current_cycle_findings)]
        compressed_historical = compressed_all[len(current_cycle_findings):]

        if depth > 0:
            accumulated_findings_text = (
                f"### New Findings (Cycle {depth + 1}):\n" +
                ("\n".join(compressed_current) if compressed_current else "(none)")
            )
            if historical_findings:
                accumulated_findings_text += (
                    f"\n\n### Historical Findings (Cycle 1 to {depth}):\n" +
                    "\n".join(compressed_historical)
                )
        else:
            accumulated_findings_text = "\n".join(compressed_current)

        followups_text = "\n".join(f"- {f}" for f in compressed_followups) or "(none)"
        gaps_text = "\n".join(f"- {g}" for g in compressed_gaps) or "(none)"
        direct_urls_text = "\n".join(f"- {u}" for u in signals.get("direct_urls", [])) or "(none)"

        # Format previous_reflection as structured markdown
        prev_refl_formatted = orch._format_reflection_markdown(previous_reflection, depth, include_cycle=True)

        user_text = prompt_data.get("user", "").format(
            objective=objective, goal=goal,
            current_depth=depth, max_depth=max_depth,
            parsed_urls=parsed_urls_text,
            accumulated_findings=accumulated_findings_text,
            previous_reflection=prev_refl_formatted,
            digest_followups=followups_text,
            digest_direct_urls=direct_urls_text,
            digest_gaps=gaps_text,
        )
        if prompt_data.get("anti_mastery"):
            user_text = apply_anti_mastery_filter(user_text)

        orch._log_meta(task_id, "orchestrator_reflect_prompt", {
            "system_prompt": system_text[:2000],
            "user_prompt": user_text[:2000],
        }, step_id=step_id or None)

        latest_result = {}
        try:
            from backend.modules.llm_client import generate_unified
            llm = getattr(orch._state, "llm_provider", None)
            if llm:
                resp = await generate_unified(llm, system_prompt=system_text, user_prompt=user_text,
                    expect_json=True,
                    fallback_value={"completeness_score": 0.5, "next_queries": [], "next_direct_urls": []},
                    temperature=prompt_data.get("temperature", 0.5),
                    max_tokens=prompt_data.get("max_tokens", 2048))
                result = resp.get("json_data") or resp.get("content") or {}
                if isinstance(result, str):
                    result = json.loads(result)
                if isinstance(result, dict):
                    latest_result = result
                    orch._log_llm_response(task_id, "orchestrator_reflect_response", resp, extra={
                        "completeness": result.get("completeness_score", 0),
                    }, step_id=step_id or None)
                    if step_id:
                        orch._save_llm_response_to_step_data(step_id, resp)
        except Exception as e:
            logger.warning("Reflection failed: %s", e)

        return latest_result or {"completeness_score": 0.3, "next_queries": [], "next_direct_urls": [], "reflection": "No reflection"}

async def _tool_evaluate(
        orch, task_id: str, step_id: str, objective: str,
        depth: int, max_depth: int, sources: int,
        reflection: dict, stagnation: int,
    ) -> tuple[bool, str]:
        """Check hard constraints first (no LLM); call LLM only in the borderline zone."""
        completeness = reflection.get("completeness_score", 0)

        # ── Hard constraints — fast, no LLM ──────────────────────────
        if depth >= max_depth:
            return True, f"depth limit reached ({depth}/{max_depth})"
        if stagnation >= 3:
            return True, f"stagnation ({stagnation} consecutive steps without new findings)"
        if completeness >= orch.satisfaction_threshold:
            return True, f"satisfaction reached ({completeness:.2f} >= {orch.satisfaction_threshold})"

        # ── Below borderline — continue without LLM call ──────────────
        if completeness < 0.4:
            return False, f"continuing — completeness too low ({completeness:.2f}), more depth needed"

        # ── Borderline zone (0.4 <= completeness < threshold) — LLM decides ──
        logger.info("Evaluate: borderline completeness %.2f — calling LLM evaluator", completeness)
        try:
            prompt_data = get_prompts_dict("research/orchestrator_evaluate.yaml")

            key_insights   = reflection.get("key_insights", [])
            remaining_gaps = reflection.get("remaining_gaps", [])
            next_queries   = reflection.get("next_queries", [])
            next_direct    = reflection.get("next_direct_urls", [])

            system_text = prompt_data.get("system", "")
            user_text = prompt_data.get("user", "").format(
                objective=objective,
                current_depth=depth,
                max_depth=max_depth,
                sources_analyzed=sources,
                completeness_score=f"{completeness:.2f}",
                key_insights   =  "\n".join(f"- {i}" for i in key_insights)    or "(none)",
                remaining_gaps =  "\n".join(f"- {g}" for g in remaining_gaps)  or "(none)",
                next_queries   =  "\n".join(f"- {q}" for q in next_queries)    or "(none)",
                next_direct_urls= "\n".join(f"- {u}" for u in next_direct)     or "(none)",
                depth_reached  = str(depth >= max_depth),
                stagnation_steps= stagnation,
                stagnated      = str(stagnation >= 3),
            )
            if prompt_data.get("anti_mastery"):
                system_text = apply_anti_mastery_filter(system_text)
                user_text   = apply_anti_mastery_filter(user_text)

            orch._log_meta(task_id, "orchestrator_evaluate_prompt", {
                "system_prompt": system_text[:orch._TRUNC_META_LOG],
                "user_prompt":   user_text[:orch._TRUNC_META_LOG],
            }, step_id=step_id or None)

            from backend.modules.llm_client import generate_unified
            llm = getattr(orch._state, "llm_provider", None)
            if not llm:
                raise RuntimeError("No LLM provider")

            resp = await generate_unified(
                llm,
                system_prompt=system_text,
                user_prompt=user_text,
                expect_json=True,
                fallback_value={"decision": "continue", "reason": "evaluation unavailable",
                                "completeness_assessment": completeness},
                temperature=prompt_data.get("temperature", 0.2),
                max_tokens=prompt_data.get("max_tokens", 1024),
            )
            orch._log_llm_response(task_id, "orchestrator_evaluate_response", resp,
                                   step_id=step_id or None)
            if step_id:
                orch._save_llm_response_to_step_data(step_id, resp)

            result = resp.get("json_data") or resp.get("content") or {}
            if isinstance(result, str):
                result = json.loads(result)
            if isinstance(result, dict):
                decision = result.get("decision", "continue").lower()
                reason   = result.get("reason", f"LLM completeness at {completeness:.2f}")
                return decision == "stop", reason

        except Exception as exc:
            logger.warning("LLM evaluate failed, defaulting to continue: %s", exc)

        return False, f"continuing (completeness {completeness:.2f} < {orch.satisfaction_threshold}, LLM fallback)"

def _classify_source_status(orch, raw_content: str | None) -> str:
        if not raw_content or not raw_content.strip():
            return "empty"
        c = raw_content.strip()
        if c.startswith("Error:"):
            err = c[6:].strip().lower()
            if "timeout" in err:
                return "failed (timeout)"
            if "dns" in err or "resolve" in err:
                return "failed (dns error)"
            return f"failed ({err[:40]})"
        if len(c) < 200:
            return "too short"
        junk_patterns = ["security check required", "cloudflare", "enable javascript", "please complete the security check"]
        c_lower = c[:1000].lower()
        if any(p in c_lower for p in junk_patterns):
            return "blocked (anti-bot)"
        import re
        if re.match(r'^(skip|close|open navigation|sign in|sign up)', c[:100].strip(), re.IGNORECASE):
            return "paywall"
        return "ok"

def _apply_unified_references(
        self, parsed_urls_list: list[dict], findings: list[str], followups: list[str] = None, gaps: list[str] = None
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        """
        Builds a unified source ID map (S1, S2, ...) from parsed_urls_list,
        then replaces the source titles in findings, followups, and gaps with [S1], [S2] etc.
        Returns:
            parsed_urls_formatted: list of formatted string lines with [S##] prefix.
            compressed_findings: list of findings with source titles replaced by [S##].
            compressed_followups: list of followups with source titles replaced by [S##].
            compressed_gaps: list of gaps with source titles replaced by [S##].
        """
        import re
        
        # If parsed_urls_list is empty (e.g. in final synthesize phase),
        # dynamically extract all source keys from the findings to build a basic list.
        if not parsed_urls_list:
            seen_srcs = []
            for f in findings:
                match = re.match(r"^\[(.*?)\]:\s*(.*)$", f)
                if match:
                    src_key = match.group(1)
                    if src_key not in seen_srcs:
                        seen_srcs.append(src_key)
            parsed_urls_list = [{"url": s, "title": s, "status": ""} for s in seen_srcs]

        # Build source mapping: title -> S##, url -> S##
        source_map = {}
        parsed_urls_formatted = []
        
        for idx, u in enumerate(parsed_urls_list, 1):
            sid = f"S{idx}"
            title = u.get("title") or u["url"]
            url = u["url"]
            status = u.get("status", "")
            
            # Map both title and url to sid for robust matching
            source_map[title] = sid
            source_map[url] = sid
            if len(title) > 80:
                source_map[title[:80]] = sid
            
            # Format: - [S1] [Title](URL) — Status
            status_suffix = f" — {status}" if status else ""
            if title and title != url:
                parsed_urls_formatted.append(f"- [{sid}] [{title}]({url}){status_suffix}")
            else:
                parsed_urls_formatted.append(f"- [{sid}] {url}{status_suffix}")

        def compress_item(item_str: str) -> str:
            # Matches pattern: ^\[(.*?)\]:\s*(.*)$
            match = re.match(r"^\[(.*?)\]:\s*(.*)$", item_str)
            if match:
                src_key = match.group(1)
                content = match.group(2)
                
                # Check for direct key match
                if src_key in source_map:
                    return f"[{source_map[src_key]}]: {content}"
                
                # Try prefix/substring match in case of minor mismatches/truncations
                for key, sid in source_map.items():
                    if src_key.startswith(key) or key.startswith(src_key):
                        return f"[{sid}]: {content}"
                        
            return item_str

        compressed_findings = [compress_item(f) for f in findings]
        compressed_followups = [compress_item(f) for f in (followups or [])]
        compressed_gaps = [compress_item(g) for g in (gaps or [])]
        
        return parsed_urls_formatted, compressed_findings, compressed_followups, compressed_gaps

