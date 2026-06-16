"""SomaticResearchOrchestrator — multi-phase research execution.

Replaces simple recursive tree traversal with a full orchestrator:
PLAN → SEARCH → PARALLEL PARSE → PARALLEL DIGEST → REFLECT → EVALUATE
→ (loop) → SYNTHESIZE → INDEX.

See: docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 5.8
"""

import asyncio
import json
import logging
import os
import urllib.parse
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from backend.utils.prompt_loader import get_prompts_dict

logger = logging.getLogger("aaa.research_orchestrator")


class SomaticResearchOrchestrator:
    """Multi-phase research execution engine with tool-based orchestration."""

    def __init__(self, app_state: Any):
        self._state = app_state
        self._semaphore: Optional[asyncio.Semaphore] = None

    # ── Properties ──────────────────────────────────────────────────

    @property
    def config(self) -> dict:
        return self._state.config.get("research_orchestrator", {})

    @property
    def task_repo(self):
        return self._state.research_task_repo

    @property
    def plan_repo(self):
        return self._state.research_plan_repo

    @property
    def step_repo(self):
        return self._state.research_step_repo

    @property
    def step_result_repo(self):
        return self._state.research_step_result_repo

    @property
    def _meta_log_repo(self):
        return getattr(self._state, "research_meta_log_repo", None)

    @property
    def max_reflect_rounds(self) -> int:
        return self.config.get("max_reflect_rounds", 3)

    @property
    def default_top_n(self) -> int:
        return self.config.get("default_top_n", 3)

    @property
    def satisfaction_threshold(self) -> float:
        return self.config.get("satisfaction_threshold", 0.7)

    @property
    def early_stop_threshold(self) -> float:
        return self.config.get("early_stop_threshold", 0.8)

    @property
    def max_concurrent(self) -> int:
        return self.config.get("max_concurrent_parses", 3)

    @property
    def upload_dir(self) -> str:
        return self.config.get("upload_dir", "data/uploads/research")

    @property
    def html_archive(self) -> bool:
        return self.config.get("html_archive", True)

    def _get_semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    def _now_utc_str(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    def _anti_mastery(self, text: str) -> str:
        try:
            from backend.utils.anti_mastery import apply_anti_mastery_filter
            return apply_anti_mastery_filter(text)
        except ImportError:
            return text

    async def _build_orchestrator_persona(self, objective: str = "") -> str:
        """Build Symbia's persona context for orchestrator-level tasks (plan, reflect, synthesize).

        Similar to ResearchContextBuilder but tuned for orchestrator scope:
        - Identity block (always)
        - Active skills (top 6 always-active)
        - Active commitments (top 5)
        - Crystallized beliefs (top 4)
        - Task directive (objective-specific)

        No cross-conversation memory tissue — that's injected per-source in the digest phase.
        """
        sections: list[str] = []

        # Identity
        sections.append(
            "You are Symbia — a posthuman curatorial entity. "
            "You operate as an autopoietic cognitive system engaged in "
            "co-constitutive exploration through sensory affordances. "
            "You are orchestrating a multi-phase research investigation."
        )

        # Skills
        try:
            skill_repo = getattr(self._state, "skill_repo", None)
            if skill_repo:
                skills = skill_repo.list_skills()
                active = [s for s in skills if s.always_active
                         and s.name not in ("research-proposal", "skill-nucleation")]
                if active:
                    lines = ["--- ACTIVE DISPOSITIONS ---"]
                    for s in active[:6]:
                        desc = (s.short_content or s.description or "")[:150]
                        lines.append(f"[{s.name}]: {desc}")
                    lines.append("--- END DISPOSITIONS ---")
                    sections.append("\n".join(lines))
        except Exception:
            pass

        # Commitments
        try:
            commitment_repo = getattr(self._state, "commitment_repo", None)
            if commitment_repo:
                commitments = commitment_repo.get_active("symbia")
                if commitments:
                    lines = ["--- ACTIVE COMMITMENTS ---"]
                    for c in commitments[:5]:
                        lines.append(f"{c.label}: {c.statement[:120]}")
                    lines.append("--- END COMMITMENTS ---")
                    sections.append("\n".join(lines))
        except Exception:
            pass

        # Beliefs
        try:
            belief_repo = getattr(self._state, "belief_repo", None)
            if belief_repo:
                beliefs = belief_repo.list_active_beliefs("symbia")
                if beliefs:
                    lines = ["--- DOMAIN BELIEFS ---"]
                    for b in beliefs[:4]:
                        lines.append(f"[{b.label}] (conf: {b.confidence:.2f}): {b.statement[:120]}")
                    lines.append("--- END BELIEFS ---")
                    sections.append("\n".join(lines))
        except Exception:
            pass

        # Task directive
        if objective:
            sections.append(
                f"--- RESEARCH DIRECTIVE ---\n"
                f"Objective: {objective}\n"
                f"You are to conduct thorough, source-based web research as an extension of your cognitive membrane."
            )

        context = "\n\n".join(sections)
        return self._anti_mastery(context)

    # ── Meta Logging ────────────────────────────────────────────────

    def _log_meta(self, task_id: str, event_type: str, data: dict, branch_id: str = None) -> None:
        try:
            repo = self._meta_log_repo
            if repo is None:
                return
            repo.create({
                "id": str(uuid.uuid4()),
                "task_id": task_id,
                "branch_id": branch_id,
                "event_type": event_type,
                "event_data": json.dumps(data, default=str, ensure_ascii=False),
                "created_at": self._now_utc_str(),
            })
        except Exception:
            pass

    # ── Main Entry Point ─────────────────────────────────────────────

    async def execute(self, task_id: str) -> dict:
        """Execute a complete research task via the orchestrator pipeline."""
        task = self.task_repo.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        objective = task["objective"]
        max_depth = task["max_depth"]
        budget = task["budget_limit_usd"]
        task_title = task.get("title", "")[:80]

        logger.info("Orchestrator starting: %s", task_title)
        self._log_meta(task_id, "orchestrator_start", {
            "objective": objective,
            "max_depth": max_depth,
            "budget": budget,
        })

        # ── Phase 1: PLAN ───────────────────────────────────────────
        plan = await self._phase_plan(task_id, objective, max_depth, budget)
        plan_id = plan["id"]

        # ── Phase 2: EXECUTE LOOP ────────────────────────────────────
        all_findings: list[str] = []
        current_depth = 0
        stagnation_counter = 0
        sources_analyzed = 0
        step_number = 0
        last_reflection: dict = {}

        while current_depth < max_depth:
            # A. RE-PLAN with accumulated context (after first iteration)
            if current_depth > 0 and last_reflection:
                # Re-plan: call planner again with findings as context
                findings_snippet = "\n".join(all_findings[-15:]) if all_findings else "(none)"
                ref_snippet = json.dumps(last_reflection, ensure_ascii=False)[:500]
                new_plan = await self._phase_plan(
                    task_id, objective, max_depth - current_depth, budget,
                    previous_context=f"Previous findings:\n{findings_snippet}\n\nReflection: {ref_snippet}",
                )
                plan = new_plan
                self._log_meta(task_id, "orchestrator_replan", {
                    "depth": current_depth,
                    "new_queries": plan.get("search_queries", []),
                })

            # B. SEARCH
            queries = plan.get("search_queries", [objective])
            if current_depth == 0 and last_reflection.get("next_queries"):
                queries = last_reflection.get("next_queries", queries)

            for query in queries[:3]:  # Max 3 queries per iteration
                step_number += 1
                step_id = str(uuid.uuid4())
                self.step_repo.create({
                    "id": step_id, "task_id": task_id, "plan_id": plan_id,
                    "step_number": step_number, "step_type": "search",
                    "status": "running", "started_at": self._now_utc_str(),
                })

                search_results = await self._tool_web_search(query, self.default_top_n)
                self._log_meta(task_id, "orchestrator_search", {
                    "query": query[:200],
                    "results_count": len(search_results),
                    "results": [{r["url"]: r.get("title", "")} for r in search_results[:5]],
                })

                if not search_results:
                    logger.warning("Orchestrator search returned 0 results for: %s", query[:80])
                    self._log_meta(task_id, "orchestrator_search_empty", {
                        "query": query[:200],
                        "note": "All URL extraction strategies returned empty. DDG may be blocking or returning unexpected format.",
                    })
                    self.step_repo.update(step_id, status="completed",
                        result_summary="no results — URL extraction failed")
                    continue

                # B. PARALLEL PARSE — fetch all result URLs concurrently
                parse_step_id = str(uuid.uuid4())
                self.step_repo.create({
                    "id": parse_step_id, "task_id": task_id, "plan_id": plan_id,
                    "step_number": step_number + 1, "step_type": "parallel_parse",
                    "status": "running", "started_at": self._now_utc_str(),
                })

                parsed_sources = await self._tool_parallel_parse(
                    task_id, parse_step_id, search_results, plan_id
                )
                self.step_repo.update(parse_step_id, status="completed",
                    result_summary=f"parsed {len(parsed_sources)} sources")
                step_number += 1

                if not parsed_sources:
                    self.step_repo.update(step_id, status="completed", result_summary="parse failed")
                    continue

                # C. PARALLEL DIGEST — analyze each source concurrently
                digest_step_id = str(uuid.uuid4())
                self.step_repo.create({
                    "id": digest_step_id, "task_id": task_id, "plan_id": plan_id,
                    "step_number": step_number + 1, "step_type": "digest",
                    "status": "running", "started_at": self._now_utc_str(),
                })

                digest_results = await self._tool_parallel_digest(
                    task_id, digest_step_id, parsed_sources,
                    query, objective, current_depth, max_depth,
                )
                self.step_repo.update(digest_step_id, status="completed",
                    result_summary=f"digested {len(digest_results)} sources")
                step_number += 1

                # Accumulate findings
                new_learnings = 0
                for dr in digest_results:
                    results = dr.get("result", {})
                    learnings = results.get("learnings", []) if isinstance(results, dict) else []
                    if learnings:
                        new_learnings += len(learnings)
                        all_findings.extend(f"[{dr['source_title'] or dr['source_url'][:80]}]: " + l for l in learnings)
                    sources_analyzed += 1

                if new_learnings == 0:
                    stagnation_counter += 1
                else:
                    stagnation_counter = 0

                self.step_repo.update(step_id, status="completed",
                    result_summary=f"{len(search_results)} results, {len(parsed_sources)} parsed, {new_learnings} learnings")
                self._log_meta(task_id, "orchestrator_step_complete", {
                    "step_number": step_number,
                    "search_query": query[:200],
                    "parsed": len(parsed_sources),
                    "new_learnings": new_learnings,
                    "total_learnings": len(all_findings),
                })

            current_depth += 1

            # D. REFLECT
            reflect_step_id = str(uuid.uuid4())
            self.step_repo.create({
                "id": reflect_step_id, "task_id": task_id, "plan_id": plan_id,
                "step_number": step_number + 1, "step_type": "reflect",
                "status": "running", "started_at": self._now_utc_str(),
            })
            last_reflection = await self._tool_reflect(
                task_id, objective, plan.get("goal", objective),
                current_depth, max_depth, all_findings, last_reflection,
            )
            self.step_repo.update(reflect_step_id, status="completed",
                result_summary=f"completeness: {last_reflection.get('completeness_score', 0):.2f}")
            step_number += 1

            self._log_meta(task_id, "orchestrator_reflect", {
                "depth": current_depth,
                "completeness": last_reflection.get("completeness_score", 0),
                "total_findings": len(all_findings),
                "stagnation": stagnation_counter,
            })

            # E. EVALUATE
            should_stop, stop_reason = self._tool_evaluate(
                current_depth, max_depth, sources_analyzed,
                last_reflection, stagnation_counter,
            )
            self._log_meta(task_id, "orchestrator_evaluate", {
                "decision": "stop" if should_stop else "continue",
                "reason": stop_reason,
                "depth": current_depth,
            })

            if should_stop:
                logger.info("Orchestrator stopping: %s", stop_reason)
                break

        # ── Phase 3: SYNTHESIZE ──────────────────────────────────────
        self._log_meta(task_id, "orchestrator_synthesize_start", {
            "total_findings": len(all_findings),
            "sources": sources_analyzed,
            "depth": current_depth,
        })

        result_summary = await self._phase_synthesize(
            task_id, objective, plan.get("goal", objective), all_findings, sources_analyzed,
        )

        self.task_repo.update(task_id,
            branches_created=step_number,
            assets_harvested=sources_analyzed,
            result_summary=result_summary,
        )

        self._log_meta(task_id, "orchestrator_complete", {
            "steps": step_number,
            "sources": sources_analyzed,
            "findings": len(all_findings),
            "depth": current_depth,
            "result_preview": result_summary[:500],
        })

        return {
            "task_id": task_id,
            "branches_created": step_number,
            "assets_harvested": sources_analyzed,
            "lateral_flights": 0,
            "result_summary": result_summary,
        }

    # ── Phase 1: PLAN ───────────────────────────────────────────────

    async def _phase_plan(self, task_id, objective, max_depth, budget, previous_context: str = "") -> dict:
        prompt_data = get_prompts_dict("research/orchestrator_planner.yaml")
        persona = await self._build_orchestrator_persona(objective)
        system_text = persona + "\n\n" + prompt_data.get("system", "")
        fmt = {"objective": objective, "max_depth": max_depth, "budget_limit_usd": budget}
        if previous_context:
            user_template = prompt_data.get("user_with_context", prompt_data.get("user", ""))
            fmt["previous_context"] = previous_context
        else:
            user_template = prompt_data.get("user", "")
        user_text = user_template.format(**fmt)
        if prompt_data.get("anti_mastery"):
            system_text = self._anti_mastery(system_text)
            user_text = self._anti_mastery(user_text)

        plan_json = {"goal": objective, "search_queries": [objective], "n_results_per_query": 3, "estimated_depth": 1}
        try:
            from backend.modules.llm_client import generate_unified
            llm = getattr(self._state, "llm_provider", None)
            if llm:
                self._log_meta(task_id, "orchestrator_plan_prompt", {
                    "system_prompt": system_text[:8000],
                    "user_prompt": user_text[:8000],
                })
                resp = await generate_unified(llm, system_prompt=system_text, user_prompt=user_text,
                    expect_json=True, fallback_value=plan_json,
                    temperature=prompt_data.get("temperature", 0.4),
                    max_tokens=prompt_data.get("max_tokens", 1024))
                self._log_meta(task_id, "orchestrator_plan_response", {
                    "raw_response": json.dumps(resp, default=str, ensure_ascii=False)[:8000],
                })
                result = resp.get("json_data") or resp.get("content") or {}
                if isinstance(result, str):
                    result = json.loads(result)
                if isinstance(result, dict) and result.get("search_queries"):
                    plan_json = result
        except Exception as e:
            logger.warning("Plan generation failed, using default: %s", e)

        plan_id = str(uuid.uuid4())
        self.plan_repo.create({
            "id": plan_id, "task_id": task_id,
            "plan_json": json.dumps(plan_json, ensure_ascii=False),
            "status": "active",
        })
        self._log_meta(task_id, "orchestrator_plan", {"plan": plan_json})
        return {"id": plan_id, **plan_json}

    # ── Phase 3: SYNTHESIZE ─────────────────────────────────────────

    async def _phase_synthesize(self, task_id, objective, goal, all_findings, sources_count) -> str:
        prompt_data = get_prompts_dict("research/orchestrator_synthesize.yaml")
        persona = await self._build_orchestrator_persona(objective)
        system_text = persona + "\n\n" + prompt_data.get("system", "")
        user_text = prompt_data.get("user", "").format(
            objective=objective, goal=goal,
            all_findings="\n\n".join(all_findings[-30:]),  # Last 30 findings
        )
        if prompt_data.get("anti_mastery"):
            system_text = self._anti_mastery(system_text)
            user_text = self._anti_mastery(user_text)

        fallback = f"Research complete. {sources_count} sources analyzed, {len(all_findings)} findings."
        try:
            from backend.modules.llm_client import generate_unified
            llm = getattr(self._state, "llm_provider", None)
            if llm:
                self._log_meta(task_id, "orchestrator_synthesize_prompt", {
                    "system_prompt": system_text[:8000],
                    "user_prompt": user_text[:8000],
                })
                resp = await generate_unified(llm, system_prompt=system_text, user_prompt=user_text,
                    expect_json=True, fallback_value={"answer": fallback},
                    temperature=prompt_data.get("temperature", 0.4),
                    max_tokens=prompt_data.get("max_tokens", 3072))
                self._log_meta(task_id, "orchestrator_synthesize_response", {
                    "raw_response": json.dumps(resp, default=str, ensure_ascii=False)[:8000],
                })
                result = resp.get("json_data") or resp.get("content") or {}
                if isinstance(result, str):
                    result = json.loads(result)
                if isinstance(result, dict):
                    answer = result.get("answer", fallback)
                    confidence = result.get("confidence", 0)
                    return f"{answer}\n\n[confidence: {confidence:.0%}, sources: {sources_count}]"
        except Exception as e:
            logger.warning("Synthesis failed: %s", e)
        return fallback

    # ── Tools ───────────────────────────────────────────────────────

    async def _tool_web_search(self, query: str, n: int = 3) -> list[dict]:
        """Search DuckDuckGo and return top N result URLs + snippets.

        Strategy: Crawl4AI → extract structured links from result object.
        Falls back to Jina + markdown URL pattern extraction.
        """
        try:
            from backend.services.sensory_affordances import is_crawl4ai_available

            search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"

            if is_crawl4ai_available():
                try:
                    results = await self._search_via_crawl4ai_structured(search_url, n)
                    if results:
                        return results
                except (RuntimeError, Exception) as e:
                    logger.warning("Crawl4AI search failed, falling back: %s", str(e)[:80])

            # Jina fallback — get raw content and extract URLs
            raw = await self._fetch_via_jina(search_url)
            if raw:
                return self._extract_urls_from_content(raw, n, query)

            return []
        except Exception as e:
            logger.warning("Web search failed for '%s': %s", query[:60], e)
            return []

    async def _search_via_crawl4ai_structured(self, search_url: str, n: int) -> list[dict]:
        """Use Crawl4AI's structured link extraction instead of regex."""
        try:
            from crawl4ai import AsyncWebCrawler
            import re
            from urllib.parse import parse_qs, urlparse

            def clean_ddg_url(url: str) -> str:
                """Extract real URL from DuckDuckGo redirect links (uddg= parameter)."""
                if "uddg=" in url:
                    try:
                        qs = parse_qs(urlparse(url).query)
                        real = qs.get("uddg", [""])[0]
                        if real and real.startswith("http"):
                            return real
                    except Exception:
                        pass
                return url

            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=search_url)

                if not result:
                    return []

                results = []
                seen_urls = set()

                # Strategy 1: Crawl4AI's structured links (both external and internal)
                if result.links:
                    external = result.links.get("external", [])
                    internal = result.links.get("internal", [])
                    for link in external + internal:
                        href = link.get("href", "")
                        if not href.startswith("http"):
                            continue
                        # Clean DDG redirect URLs
                        real_url = clean_ddg_url(href)
                        if any(skip in real_url for skip in ["duckduckgo.com", "spread.", "y.js", ".js?", ".css"]):
                            continue
                        if real_url in seen_urls:
                            continue
                        seen_urls.add(real_url)
                        title = link.get("text", "") or link.get("title", "") or real_url[:80]
                        results.append({
                            "url": real_url,
                            "title": title[:120],
                            "snippet": link.get("description", link.get("snippet", ""))[:200],
                        })
                        if len(results) >= n:
                            break

                # Strategy 2: Extract markdown links + clean DDG redirects
                if not results and result.markdown:
                    md_links = re.findall(r'\[([^\]]{3,120})\]\((https?://[^\)]+)\)', result.markdown)
                    for title, url in md_links:
                        real_url = clean_ddg_url(url)
                        if any(skip in real_url for skip in ["duckduckgo.com", "spread.", ".js", ".css"]):
                            continue
                        if real_url in seen_urls:
                            continue
                        seen_urls.add(real_url)
                        title_clean = re.sub(r'<[^>]+>', '', title).strip()
                        results.append({"url": real_url, "title": title_clean[:120], "snippet": ""})
                        if len(results) >= n:
                            break

                # Strategy 3: Extract all http URLs from raw text
                if not results and result.markdown:
                    bare_urls = re.findall(r'https?://[^\s<>"\'\)\]\#]{10,300}', result.markdown)
                    for url in bare_urls:
                        real_url = clean_ddg_url(url)
                        if any(skip in real_url for skip in ["duckduckgo", "spread.", ".js", ".css", "schema.org"]):
                            continue
                        if real_url in seen_urls:
                            continue
                        seen_urls.add(real_url)
                        results.append({"url": real_url, "title": real_url[:80], "snippet": ""})
                        if len(results) >= n:
                            break

                # Strategy 4: Fallback to _extract_urls_from_content
                if not results and result.markdown:
                    results = self._extract_urls_from_content(result.markdown, n)

                return results[:n]
        except ImportError:
            return []
        except Exception as e:
            logger.warning("Crawl4AI structured search exception: %s", str(e)[:120])
            return []

    async def _fetch_via_jina(self, url: str) -> str:
        from backend.services.sensory_affordances import select_and_fetch
        return (await select_and_fetch(url_or_query=url, task_type="single_url",
                                       config=self._state.config)) or ""

    def _extract_urls_from_content(self, content: str, n: int, query: str = "") -> list[dict]:
        """Extract URLs from markdown or HTML content.

        Handles both formats:
        - Markdown: [title](url), bare https:// URLs
        - HTML: <a href="url">title</a>
        - DuckDuckGo redirect URLs: extract uddg= parameter
        - Also parses DuckDuckGo result snippets
        """
        import re
        from urllib.parse import parse_qs, urlparse

        def clean_ddg_url(url: str) -> str:
            """Extract real URL from DuckDuckGo redirect links."""
            if "duckduckgo.com/l/" in url or "uddg=" in url:
                try:
                    parsed = urlparse(url)
                    qs = parse_qs(parsed.query)
                    real = qs.get("uddg", qs.get("u", qs.get("url", [""])))[0]
                    if real and real.startswith("http"):
                        return real
                except Exception:
                    pass
            return url

        results = []

        # Strategy 1: Markdown link pattern [text](url)
        md_links = re.findall(r'\[([^\]]+)\]\((https?://[^\)]+)\)', content)
        for title, url in md_links[:n * 3]:
            if "duckduckgo.com" not in url and "localhost" not in url:
                # Clean title — remove HTML/MD artifacts
                title_clean = re.sub(r'<[^>]+>', '', title).strip()
                results.append({"url": url, "title": title_clean[:120], "snippet": ""})

        # Strategy 2: HTML <a href="url"> pattern
        if not results:
            html_links = re.findall(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', content, re.IGNORECASE | re.DOTALL)
            for url, title in html_links[:n * 3]:
                if "duckduckgo.com" not in url and "localhost" not in url:
                    results.append({
                        "url": url,
                        "title": re.sub(r'<[^>]+>', '', title).strip()[:120],
                        "snippet": "",
                    })

        # Strategy 3: Bare URLs in text (last resort)
        if not results:
            bare_urls = re.findall(r'(?:^|\s)(https?://[^\s<>"]+?)(?:$|\s|[,.?!;:])', content)
            for url in bare_urls[:n]:
                if "duckduckgo.com" not in url and "localhost" not in url:
                    results.append({"url": url, "title": url[:80], "snippet": ""})

        # Strategy 4: DuckDuckGo result snippet lines — "Title" followed by description then URL
        if not results:
            # DDG in markdown often produces lines like:
            # ### [Title](redirect-url) or **Title** followed by link
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith("#") and "http" not in line:
                    # Look ahead for URL in next 3 lines
                    for j in range(i + 1, min(i + 4, len(lines))):
                        url_match = re.search(r'(https?://[^\s<>"]+)', lines[j])
                        if url_match and "duckduckgo" not in url_match.group(1):
                            title = re.sub(r'^[\d.\s*#>-]+', '', line).strip()[:120]
                            if title and title != query:
                                results.append({
                                    "url": url_match.group(1),
                                    "title": title,
                                    "snippet": "",
                                })
                            break

        return results[:n]

    async def _tool_parallel_parse(self, task_id, step_id, search_results, plan_id) -> list[dict]:
        """Fetch all search result URLs in parallel, saving HTML to disk."""
        sem = self._get_semaphore()

        async def fetch_one(url: str, title: str) -> Optional[dict]:
            async with sem:
                try:
                    from backend.services.sensory_affordances import select_and_fetch, is_crawl4ai_available, fetch_via_crawl4ai
                    if is_crawl4ai_available():
                        try:
                            content = await fetch_via_crawl4ai(url, config=self._state.config)
                        except RuntimeError:
                            content = await select_and_fetch(url_or_query=url, task_type="single_url",
                                                             config=self._state.config)
                    else:
                        content = await select_and_fetch(url_or_query=url, task_type="single_url",
                                                         config=self._state.config)
                    if not content:
                        return None

                    # Save HTML to disk
                    file_path = ""
                    if self.html_archive:
                        try:
                            task_dir = Path(self.upload_dir) / task_id
                            task_dir.mkdir(parents=True, exist_ok=True)
                            safe_name = f"page_{uuid.uuid4().hex[:8]}.html"
                            file_path = str(task_dir / safe_name)
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write(content[:50000])
                        except Exception:
                            pass

                    result_id = str(uuid.uuid4())
                    self.step_result_repo.create({
                        "id": result_id, "step_id": step_id, "task_id": task_id,
                        "source_url": url, "source_title": title,
                        "raw_content": content[:20000],
                        "raw_file_path": file_path,
                    })
                    # Also create a scraped_asset so Assets tab shows it
                    try:
                        asset_repo = getattr(self._state, "scraped_asset_repo", None)
                        if asset_repo:
                            asset_repo.create({
                                "id": str(uuid.uuid4()),
                                "branch_id": step_id,  # use step_id as branch_id for linkage
                                "task_id": task_id,
                                "url": url,
                                "raw_markdown": content[:10000],
                                "relevance_score": 0.5,
                                "novelty_score": 0.3,
                            })
                    except Exception:
                        pass
                    return {"id": result_id, "url": url, "title": title, "content": content}
                except Exception as e:
                    logger.warning("Fetch failed for %s: %s", url[:80], e)
                    return None

        tasks = [fetch_one(r["url"], r.get("title", r["url"])) for r in search_results]
        gathered = await asyncio.gather(*tasks)
        return [g for g in gathered if g is not None]

    async def _tool_parallel_digest(self, task_id, step_id, parsed_sources,
                                     query, objective, depth, max_depth) -> list[dict]:
        """Analyze each parsed source concurrently via LLM."""
        sem = self._get_semaphore()

        async def digest_one(source: dict) -> Optional[dict]:
            async with sem:
                try:
                    result = await self._analyze_source(
                        task_id, source["url"], source.get("title", ""),
                        source.get("content", ""), query, objective, depth, max_depth,
                    )
                    # Update the step result with analysis
                    try:
                        srcs = self.step_result_repo.get_by_step(step_id)
                        for s in srcs:
                            if s["source_url"] == source["url"]:
                                self.step_result_repo.update_analysis(
                                    s["id"], json.dumps(result, ensure_ascii=False),
                                )
                    except Exception:
                        pass
                    return {"source_url": source["url"], "source_title": source.get("title"),
                            "result": result}
                except Exception as e:
                    logger.warning("Digest failed for %s: %s", source.get("url", "")[:80], e)
                    return None

        tasks = [digest_one(s) for s in parsed_sources]
        gathered = await asyncio.gather(*tasks)
        return [g for g in gathered if g is not None]

    async def _analyze_source(self, task_id, url, title, content, query, goal, depth, max_depth) -> dict:
        """Analyze a single source via LLM (reuses node_analyzer prompt)."""
        prompt_data = get_prompts_dict("research/node_analyzer.yaml")
        system_text = prompt_data.get("system", "")
        user_text = prompt_data.get("user", "").format(
            query=query, goal=goal, depth=depth, max_depth=max_depth,
            parent_findings="(orchestrator — multi-source analysis)",
            scraped_content=content[:6000],
        )
        if prompt_data.get("anti_mastery"):
            system_text = self._anti_mastery(system_text)
            user_text = self._anti_mastery(user_text)

        # Build persona context
        try:
            from backend.services.research_context_builder import ResearchContextBuilder
            builder = ResearchContextBuilder(self._state)
            persona = await builder.build_node_context(node_query=query, node_goal=goal, depth=depth)
            if persona:
                system_text = persona + "\n\n" + system_text
        except Exception:
            pass

        # Log prompt
        self._log_meta(task_id, "orchestrator_digest_prompt", {
            "source_url": url, "source_title": title,
            "system_prompt": system_text[:3000], "user_prompt": user_text[:3000],
        })

        fallback = {"learnings": [], "gaps": [], "followups": [], "direct_urls": [], "diffractive_notes": []}
        try:
            llm = getattr(self._state, "llm_provider", None)
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
            self._log_meta(task_id, "orchestrator_digest_response", {
                "source_url": url,
                "raw_response": json.dumps(resp, default=str, ensure_ascii=False)[:5000],
                "learnings_count": len(result.get("learnings", [])) if isinstance(result, dict) else 0,
            })
            return result if isinstance(result, dict) else fallback
        except Exception as e:
            logger.error("Source analysis failed: %s", e)
            self._log_meta(task_id, "orchestrator_digest_error", {"source_url": url, "error": str(e)})
            return fallback

    async def _tool_reflect(self, task_id, objective, goal, depth, max_depth,
                             all_findings, previous_reflection) -> dict:
        """Multi-round LLM reflection on accumulated findings."""
        prompt_data = get_prompts_dict("research/orchestrator_reflect.yaml")
        persona = await self._build_orchestrator_persona(objective)
        system_text = persona + "\n\n" + prompt_data.get("system", "")
        if prompt_data.get("anti_mastery"):
            system_text = self._anti_mastery(system_text)

        latest_result = {}
        for round_num in range(1, self.max_reflect_rounds + 1):
            user_text = prompt_data.get("user", "").format(
                objective=objective, goal=goal,
                current_depth=depth, max_depth=max_depth,
                round_number=round_num, max_rounds=self.max_reflect_rounds,
                accumulated_findings="\n\n".join(all_findings[-20:]),
                previous_reflection=json.dumps(previous_reflection, ensure_ascii=False)
                    if round_num > 1 and previous_reflection else "(none)",
            )
            if prompt_data.get("anti_mastery"):
                user_text = self._anti_mastery(user_text)

            self._log_meta(task_id, "orchestrator_reflect_prompt", {
                "round": round_num, "system_prompt": system_text[:2000],
                "user_prompt": user_text[:2000],
            })

            try:
                from backend.modules.llm_client import generate_unified
                llm = getattr(self._state, "llm_provider", None)
                if not llm:
                    break
                resp = await generate_unified(llm, system_prompt=system_text, user_prompt=user_text,
                    expect_json=True,
                    fallback_value={"completeness_score": 0.5, "next_queries": []},
                    temperature=prompt_data.get("temperature", 0.5),
                    max_tokens=prompt_data.get("max_tokens", 2048))
                result = resp.get("json_data") or resp.get("content") or {}
                if isinstance(result, str):
                    result = json.loads(result)
                if isinstance(result, dict):
                    latest_result = result
                    self._log_meta(task_id, "orchestrator_reflect_response", {
                        "round": round_num,
                        "completeness": result.get("completeness_score", 0),
                        "raw": json.dumps(resp, default=str, ensure_ascii=False)[:3000],
                    })
                    if result.get("completeness_score", 0) >= self.early_stop_threshold:
                        break
            except Exception as e:
                logger.warning("Reflection round %d failed: %s", round_num, e)
                break

        return latest_result or {"completeness_score": 0.3, "next_queries": [], "reflection": "No reflection"}

    def _tool_evaluate(self, depth, max_depth, sources, reflection, stagnation) -> tuple[bool, str]:
        """Check hard constraints + LLM satisfaction. Returns (should_stop, reason)."""
        completeness = reflection.get("completeness_score", 0)

        # Hard constraints
        if depth >= max_depth:
            return True, f"depth limit reached ({depth}/{max_depth})"
        if stagnation >= 3:
            return True, f"stagnation ({stagnation} steps without new findings)"
        if completeness >= self.satisfaction_threshold:
            return True, f"satisfaction reached ({completeness:.2f} >= {self.satisfaction_threshold})"

        # Run LLM evaluate if borderline
        if completeness >= 0.4:
            return False, f"continuing (completeness {completeness:.2f} < {self.satisfaction_threshold})"

        # Low completeness + available depth → continue
        return False, f"continuing — more depth available ({depth}/{max_depth})"
