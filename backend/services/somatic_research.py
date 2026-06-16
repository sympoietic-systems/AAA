"""SomaticResearchEngine — asynchronous recursive tree traversal.

The core execution engine for autonomous web research. Manages the
recursive exploration of sub-queries, utility scoring, lateral line-of-flight
detection, and branch pruning.

See docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 5.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

from backend.utils.prompt_loader import get_prompts_dict
from backend.utils.somatic_math import (
    calculate_diffractive_similarity,
    calculate_rhizomatic_utility,
    compute_novelty,
    compute_relevance,
    normalize_cost,
    should_trigger_lateral_flight,
    compute_detour_query_embedding,
)

logger = logging.getLogger("aaa.somatic_research")


class SomaticResearchEngine:
    """Executes recursive tree traversal for autonomous web research.

    Coordinates the interplay between sensory affordances, persona context
    building, utility scoring, and branch management.
    """

    def __init__(self, app_state: Any):
        self._state = app_state
        self._semaphore: Optional[asyncio.Semaphore] = None

    @property
    def config(self) -> dict:
        return self._state.config.get("rhizome_research", {})

    @property
    def task_repo(self):
        return self._state.research_task_repo

    @property
    def branch_repo(self):
        return self._state.research_branch_repo

    @property
    def asset_repo(self):
        return self._state.scraped_asset_repo

    @property
    def task_manager(self):
        return self._state.research_task_manager

    @property
    def max_concurrent_probes(self) -> int:
        return self.config.get("max_concurrent_probes", 3)

    @property
    def lateral_threshold(self) -> float:
        return self.config.get("lateral_flight_threshold", 0.72)

    @property
    def detour_alpha(self) -> float:
        return self.config.get("detour_interpolation_alpha", 0.5)

    def _get_semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent_probes)
        return self._semaphore

    @property
    def _meta_log_repo(self):
        return getattr(self._state, "research_meta_log_repo", None)

    def _log_meta(self, task_id: str, event_type: str, data: dict, branch_id: str = None) -> None:
        """Log a research event to the meta-log for debugging/traceability."""
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
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            })
        except Exception:
            pass  # Never let meta-logging break research execution

    def _anti_mastery(self, text: str) -> str:
        try:
            from backend.utils.anti_mastery import apply_anti_mastery_filter
            return apply_anti_mastery_filter(text)
        except ImportError:
            return text

    # ── Main Entry Point ─────────────────────────────────────────────

    async def execute(self, task_id: str) -> dict:
        """Execute a complete research task.

        Called by ResearchTaskManager._execute_task() when a task
        transitions to ACTIVE state.

        Returns:
            Results dict with summary, branch/asset counts, lateral_flights
        """
        task = self.task_repo.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        logger.info("Starting research task %s: %s", task_id, task.get("title", "")[:80])

        objective = task["objective"]
        max_depth = task["max_depth"]
        max_breadth = task["max_breadth"]
        is_agonistic = bool(task["is_agonistic"])
        conversation_id = task.get("conversation_id") or f"research_{task_id}"

        self._log_meta(task_id, "task_started", {
            "title": task.get("title", ""),
            "objective": objective,
            "max_depth": max_depth,
            "max_breadth": max_breadth,
            "is_agonistic": is_agonistic,
            "budget_limit": task["budget_limit_usd"],
        })

        # Auto-create conversation if it doesn't exist (console-initiated research)
        if not task.get("conversation_id"):
            try:
                conv_repo = getattr(self._state, "conversation_repo", None)
                if conv_repo and not conv_repo.get(conversation_id):
                    conv_repo.create(
                        conversation_id=conversation_id,
                        title=task.get("title", "Research Task"),
                        agent_id="symbia",
                    )
                    logger.info("Created research conversation: %s", conversation_id)
            except Exception as e:
                logger.warning("Could not create research conversation: %s", e)

        # Initialize: generate root-level sub-queries
        sub_queries = await self._generate_sub_queries(
            objective, is_agonistic, 0, max_depth, max_breadth
        )
        self._log_meta(task_id, "query_generation", {
            "objective": objective,
            "sub_queries": sub_queries,
            "is_agonistic": is_agonistic,
        })

        # Recursive exploration with total node cap
        MAX_TOTAL_NODES = 50
        self._node_count = 0
        all_assets = []
        lateral_flights = 0
        branches_created = 0

        for query_dict in sub_queries:
            if self._node_count >= MAX_TOTAL_NODES:
                self._log_meta(task_id, "node_limit_reached", {"limit": MAX_TOTAL_NODES})
                logger.warning("Research task %s: reached node limit %d, stopping", task_id, MAX_TOTAL_NODES)
                break
            branch_assets, branch_laterals = await self._traverse_rhizome(
                task_id=task_id,
                conversation_id=conversation_id,
                query=query_dict.get("query", query_dict if isinstance(query_dict, str) else ""),
                goal=query_dict.get("goal", "") if isinstance(query_dict, dict) else "",
                depth=0,
                max_depth=max_depth,
                breadth=max_breadth,
                parent_branch_id=None,
            )
            all_assets.extend(branch_assets)
            lateral_flights += branch_laterals
            branches_created += 1

        # Update task
        self.task_repo.update(task_id,
            branches_created=branches_created,
            assets_harvested=len(all_assets),
            lateral_flights=lateral_flights,
        )

        logger.info(
            "Research task %s complete: %d branches, %d assets, %d lateral flights",
            task_id, branches_created, len(all_assets), lateral_flights,
        )

        # Generate synthesis summary via LLM
        result_summary = (
            f"Research complete. {branches_created} branches, "
            f"{len(all_assets)} assets, {lateral_flights} lateral flights."
        )
        if all_assets:
            try:
                self._log_meta(task_id, "synthesis_start", {"assets_count": len(all_assets)})
                from backend.metabolisation.research_metabolism import ResearchMetabolismEngine
                metabolism = ResearchMetabolismEngine(self._state)
                await metabolism.metabolize_research_results(task)
                # Re-read task to get the LLM-generated summary
                updated = self.task_repo.get(task_id)
                if updated and updated.get("result_summary"):
                    result_summary = updated["result_summary"]
                self._log_meta(task_id, "synthesis_complete", {"summary": result_summary[:500]})
            except Exception as e:
                logger.warning("Synthesis/metabolism skipped: %s", e)
                self._log_meta(task_id, "synthesis_error", {"error": str(e)})

        self._log_meta(task_id, "task_complete", {
            "branches_created": branches_created,
            "assets_harvested": len(all_assets),
            "lateral_flights": lateral_flights,
            "result_summary": result_summary[:500],
        })

        return {
            "task_id": task_id,
            "branches_created": branches_created,
            "assets_harvested": len(all_assets),
            "lateral_flights": lateral_flights,
            "result_summary": result_summary,
        }

    # ── Recursive Tree Traversal ─────────────────────────────────────

    async def _traverse_rhizome(
        self,
        task_id: str,
        conversation_id: str,
        query: str,
        goal: str,
        depth: int,
        max_depth: int,
        breadth: int,
        parent_branch_id: Optional[str],
    ) -> tuple[list[dict], int]:
        """Recursive tree traversal — probe, score, branch.

        Returns (assets_list, lateral_flights_count).
        """
        self._node_count += 1
        MAX_TOTAL_NODES = 50

        if depth >= max_depth or self._node_count > MAX_TOTAL_NODES:
            if self._node_count > MAX_TOTAL_NODES:
                self._log_meta(task_id, "node_limit_reached_branch", {"limit": MAX_TOTAL_NODES, "at_depth": depth})
            return [], 0

        # Create branch record
        branch_id = str(uuid.uuid4())
        self.branch_repo.create({
            "id": branch_id,
            "task_id": task_id,
            "conversation_id": conversation_id,
            "parent_branch_id": parent_branch_id,
            "query": query,
            "goal": goal,
            "depth": depth,
            "breadth": breadth,
            "status": "probing",
        })
        self._log_meta(task_id, "branch_create", {
            "branch_id": branch_id,
            "parent_branch_id": parent_branch_id,
            "query": query,
            "goal": goal,
            "depth": depth,
            "breadth": breadth,
        }, branch_id=branch_id)

        # Probe the node
        result = await self._probe_node(branch_id, task_id, query, goal, depth, max_depth)
        assets = result.get("assets", [])
        lateral_flights = 0

        # Check for lateral detour
        diffractive_score = result.get("diffractive_score", 0.0)
        if should_trigger_lateral_flight(diffractive_score, self.lateral_threshold) and depth + 1 < max_depth:
            lateral_flights += 1
            logger.info("Lateral flight triggered at depth %d: S_diff=%.3f", depth, diffractive_score)
            # Spawn detour branch (simplified — would need detour query generation)
            self.branch_repo.update(branch_id, status="detoured")

            # Generate child sub-queries for exploration
            if result.get("followups"):
                for followup in result["followups"][:breadth]:
                    child_assets, child_flights = await self._traverse_rhizome(
                        task_id=task_id,
                        conversation_id=conversation_id,
                        query=followup if isinstance(followup, str) else followup.get("query", ""),
                        goal="" if isinstance(followup, str) else followup.get("goal", ""),
                        depth=depth + 1,
                        max_depth=max_depth,
                        breadth=max(1, breadth // 2),
                        parent_branch_id=branch_id,
                    )
                    assets.extend(child_assets)
                    lateral_flights += child_flights
        else:
            self.branch_repo.update(branch_id, status="crystallized")

            # Standard recursion — generate sub-queries from findings
            if result.get("followups") and depth + 1 < max_depth:
                for followup in result["followups"][:breadth]:
                    child_assets, child_flights = await self._traverse_rhizome(
                        task_id=task_id,
                        conversation_id=conversation_id,
                        query=followup if isinstance(followup, str) else followup.get("query", ""),
                        goal="" if isinstance(followup, str) else followup.get("goal", ""),
                        depth=depth + 1,
                        max_depth=max_depth,
                        breadth=max(1, breadth // 2),
                        parent_branch_id=branch_id,
                    )
                    assets.extend(child_assets)
                    lateral_flights += child_flights

        return assets, lateral_flights

    # ── Node Probe ───────────────────────────────────────────────────

    async def _probe_node(
        self,
        branch_id: str,
        task_id: str,
        query: str,
        goal: str,
        depth: int,
        max_depth: int,
    ) -> dict:
        """Probe a single research node: fetch -> analyze -> score.

        Returns dict with keys: assets, learnings, followups, diffractive_score
        """
        sem = self._get_semaphore()
        async with sem:
            # 1. Fetch web content via sensory affordances
            scraped_text = ""
            fetched_url = query  # Track what was actually fetched
            fetch_method = "none"
            try:
                from backend.services.sensory_affordances import select_and_fetch, is_crawl4ai_available, fetch_via_crawl4ai
                # Convert search phrases to URLs if needed
                if query.startswith("http://") or query.startswith("https://"):
                    fetched_url = query
                    fetch_method = "jina_direct"
                    scraped_text = await select_and_fetch(
                        url_or_query=query, task_type="single_url", config=self._state.config,
                    )
                elif is_crawl4ai_available():
                    # Use Crawl4AI browser to scrape search results
                    import urllib.parse
                    search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
                    fetched_url = search_url
                    fetch_method = "crawl4ai"
                    try:
                        scraped_text = await fetch_via_crawl4ai(search_url, config=self._state.config)
                        if not scraped_text:
                            # Fallback to Jina
                            fetch_method = "jina_fallback"
                            scraped_text = await select_and_fetch(
                                url_or_query=search_url, task_type="single_url", config=self._state.config,
                            )
                    except RuntimeError as cre:
                        # Crawl4AI antibot/connection errors — clean fallback
                        fetch_method = "jina_fallback_after_crawl4ai_error"
                        self._log_meta(task_id, "fetch_note", {
                            "query": query[:200],
                            "method": "crawl4ai",
                            "note": "Crawl4AI blocked/connection closed, falling back to Jina",
                            "error_snippet": str(cre)[:120],
                        }, branch_id=branch_id)
                        scraped_text = await select_and_fetch(
                            url_or_query=search_url, task_type="single_url", config=self._state.config,
                        )
                    except Exception:
                        fetch_method = "jina_fallback_after_error"
                        scraped_text = await select_and_fetch(
                            url_or_query=search_url, task_type="single_url", config=self._state.config,
                        )
                else:
                    import urllib.parse
                    search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
                    fetched_url = search_url
                    fetch_method = "jina_search"
                    scraped_text = await select_and_fetch(
                        url_or_query=search_url, task_type="single_url", config=self._state.config,
                    )

                self._log_meta(task_id, "fetch_complete", {
                    "query": query[:200],
                    "fetched_url": fetched_url,
                    "method": fetch_method,
                    "content_length": len(scraped_text) if scraped_text else 0,
                    "content_preview": (scraped_text or "")[:500],
                }, branch_id=branch_id)

            except Exception as e:
                logger.warning("Sensory fetch failed for '%s': %s", query[:60], e)
                self._log_meta(task_id, "fetch_error", {
                    "query": query[:200],
                    "fetched_url": fetched_url,
                    "method": fetch_method,
                    "error": str(e),
                }, branch_id=branch_id)
                self.branch_repo.update(branch_id, status="collapsed")
                return {"assets": [], "learnings": [], "followups": [], "diffractive_score": 0.0}

            if not scraped_text:
                self.branch_repo.update(branch_id, status="collapsed")
                return {"assets": [], "learnings": [], "followups": [], "diffractive_score": 0.0}

            # 2. Build persona context and analyze
            context = ""
            try:
                from backend.services.research_context_builder import ResearchContextBuilder
                builder = ResearchContextBuilder(self._state)
                context = await builder.build_node_context(
                    node_query=query, node_goal=goal, depth=depth,
                )
            except Exception as e:
                logger.warning("Context build failed: %s", e)

            # 3. Analyze via LLM
            analysis = await self._analyze_scraped_content(
                query=query, goal=goal, depth=depth, max_depth=max_depth,
                scraped_content=scraped_text[:8000], persona_context=context,
                task_id=task_id, branch_id=branch_id,
            )

            # 4. Store asset
            asset_id = str(uuid.uuid4())
            self.asset_repo.create({
                "id": asset_id,
                "branch_id": branch_id,
                "task_id": task_id,
                "url": fetched_url,
                "raw_markdown": scraped_text[:10000],
                "relevance_score": 0.7,  # Placeholder — compute with embedder
                "novelty_score": 0.5,
                "diffractive_score": analysis.get("diffractive_score", 0.0),
            })

            assets = [{"id": asset_id, "branch_id": branch_id}]

            # Combine followup search queries with direct URL fetches
            followups = list(analysis.get("followups", []))
            direct_urls = [u for u in analysis.get("direct_urls", []) if isinstance(u, str) and u.startswith("http")]
            if direct_urls:
                self._log_meta(task_id, "direct_urls_found", {
                    "urls": direct_urls,
                    "count": len(direct_urls),
                }, branch_id=branch_id)
                # Prepend URL-fetch followups so they're processed first
                followups = direct_urls + followups

            return {
                "assets": assets,
                "learnings": analysis.get("learnings", []),
                "followups": followups,
                "diffractive_score": analysis.get("diffractive_score", 0.0),
            }

    async def _analyze_scraped_content(
        self,
        query: str,
        goal: str,
        depth: int,
        max_depth: int,
        scraped_content: str,
        persona_context: str,
        task_id: str = "",
        branch_id: str = "",
    ) -> dict:
        """Analyze scraped web content through Symbia's lens via LLM."""
        prompt_data = get_prompts_dict("research/node_analyzer.yaml")

        system_text = prompt_data.get("system", "")
        if prompt_data.get("anti_mastery"):
            system_text = self._anti_mastery(system_text)

        # Prepend persona context to system prompt
        if persona_context:
            system_text = persona_context + "\n\n" + system_text

        user_text = (prompt_data.get("user", "")).format(
            query=query,
            goal=goal,
            depth=depth,
            max_depth=max_depth,
            parent_findings="(none — root node)",
            scraped_content=scraped_content[:6000],
        )

        if prompt_data.get("anti_mastery"):
            user_text = self._anti_mastery(user_text)

        # Log the LLM prompt
        self._log_meta(task_id, "llm_prompt", {
            "query": query[:200],
            "goal": goal[:200],
            "depth": depth,
            "system_prompt": system_text,
            "user_prompt": user_text,
            "temperature": prompt_data.get("temperature", 0.3),
            "max_tokens": prompt_data.get("max_tokens", 2048),
        }, branch_id=branch_id)

        try:
            llm_provider = getattr(self._state, "llm_provider", None)
            if llm_provider is None:
                logger.error("No LLM provider available for research analysis")
                self._log_meta(task_id, "llm_error", {"error": "No LLM provider available"}, branch_id=branch_id)
                return {"learnings": [], "gaps": [], "followups": [], "diffractive_notes": []}

            from backend.modules.llm_client import generate_unified
            response = await generate_unified(
                provider=llm_provider,
                system_prompt=system_text,
                user_prompt=user_text,
                expect_json=True,
                fallback_value={"learnings": [], "gaps": [], "followups": [], "diffractive_notes": []},
                temperature=prompt_data.get("temperature", 0.3),
                max_tokens=prompt_data.get("max_tokens", 2048),
            )
            result = response.get("json_data") or response.get("content") or {}
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    result = {}

            # Log the LLM response
            self._log_meta(task_id, "llm_response", {
                "query": query[:200],
                "raw_response": json.dumps(response, default=str, ensure_ascii=False)[:8000],
                "learnings_count": len(result.get("learnings", [])) if isinstance(result, dict) else 0,
                "followups_count": len(result.get("followups", [])) if isinstance(result, dict) else 0,
                "diffractive_score": result.get("diffractive_score", 0) if isinstance(result, dict) else 0,
                "learnings": (result.get("learnings", []) if isinstance(result, dict) else [])[:5],
            }, branch_id=branch_id)

            return result if isinstance(result, dict) else {}
        except Exception as e:
            logger.error("LLM analysis failed for node: %s", e)
            self._log_meta(task_id, "llm_error", {
                "query": query[:200],
                "error": str(e),
            }, branch_id=branch_id)
            return {}

    # ── Query Generation ─────────────────────────────────────────────

    async def _generate_sub_queries(
        self,
        objective: str,
        is_agonistic: bool,
        depth: int,
        max_depth: int,
        max_breadth: int,
    ) -> list[dict]:
        """Generate initial sub-queries from a research objective."""
        try:
            from backend.services.agonistic_planner import AgonisticPlanner
            planner = AgonisticPlanner(
                llm_provider=getattr(self._state, "llm_provider", None),
                app_state=self._state,
            )
            stagnation = 0.8 if is_agonistic else 0.3
            return await planner.generate_queries(
                objective=objective,
                stagnation_index=stagnation,
                depth=depth,
                max_depth=max_depth,
                breadth=max_breadth,
            )
        except Exception as e:
            logger.error("Sub-query generation failed: %s", e)
            return [{"query": objective, "goal": "Investigate the core objective"}]
