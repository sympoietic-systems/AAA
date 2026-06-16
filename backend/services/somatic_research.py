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

        # Initialize: generate root-level sub-queries
        sub_queries = await self._generate_sub_queries(
            objective, is_agonistic, 0, max_depth, max_breadth
        )

        # Recursive exploration
        all_assets = []
        lateral_flights = 0
        branches_created = 0

        for query_dict in sub_queries:
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

        return {
            "task_id": task_id,
            "branches_created": branches_created,
            "assets_harvested": len(all_assets),
            "lateral_flights": lateral_flights,
            "all_assets": all_assets,
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
        if depth >= max_depth:
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
            try:
                from backend.services.sensory_affordances import select_and_fetch
                scraped_text = await select_and_fetch(
                    url_or_query=query,
                    task_type="single_url",
                    config=self._state.config,
                )
            except Exception as e:
                logger.warning("Sensory fetch failed for '%s': %s", query[:60], e)
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
            )

            # 4. Store asset
            asset_id = str(uuid.uuid4())
            self.asset_repo.create({
                "id": asset_id,
                "branch_id": branch_id,
                "task_id": task_id,
                "url": query,  # In practice, this would be the actual URL
                "raw_markdown": scraped_text[:10000],
                "relevance_score": 0.7,  # Placeholder — compute with embedder
                "novelty_score": 0.5,
                "diffractive_score": analysis.get("diffractive_score", 0.0),
            })

            assets = [{"id": asset_id, "branch_id": branch_id}]

            return {
                "assets": assets,
                "learnings": analysis.get("learnings", []),
                "followups": analysis.get("followups", []),
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

        try:
            llm_provider = getattr(self._state, "llm_provider", None)
            if llm_provider is None:
                logger.error("No LLM provider available for research analysis")
                return {"learnings": [], "gaps": [], "followups": [], "diffractive_notes": []}

            from backend.modules.llm_client import generate_unified
            response = await generate_unified(
                provider=llm_provider,
                system_prompt=system_text,
                user_prompt=user_text,
                expect_json=True,
                temperature=prompt_data.get("temperature", 0.3),
                max_tokens=prompt_data.get("max_tokens", 2048),
            )
            result = response.get("json_data") or {}
            if isinstance(result, str):
                result = json.loads(result)
            return result if isinstance(result, dict) else {}
        except Exception as e:
            logger.error("LLM analysis failed for node: %s", e)
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
