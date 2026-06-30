"""Research Metabolism Engine — post-research belief/skill processing.

Two phases:
  1. In-Node (per significant finding): proto-belief proposals, skill nucleation
  2. Post-Research (on task completion): full belief pass, bifurcation, skill scan,
     commitment recalculation, memory consolidation.

See docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Sections 5.6 and 5.7.
"""

import json
import logging
from typing import Any

logger = logging.getLogger("aaa.research_metabolism")


class ResearchMetabolismEngine:
    """Processes completed research findings through belief and skill systems."""

    def __init__(self, app_state: Any):
        self._state = app_state

    @property
    def config(self) -> dict:
        return self._state.config.get("research_consolidation", {})

    # ── Main Entry Point ─────────────────────────────────────────────

    async def metabolize_research_results(self, task: dict) -> dict:
        """Process a completed research task through belief/skill metabolism.

        Runs all post-research metabolic passes and returns a summary dict.
        """
        results = {
            "beliefs_updated": 0,
            "skills_proposed": 0,
            "bifurcations": 0,
            "memory_nodes_created": 0,
            "semantic_knots": 0,
        }

        task_id = task["id"]
        conversation_id = task.get("conversation_id") or f"research_{task_id}"

        # Collect all harvested content
        assets = self._state.scraped_asset_repo.get_by_task(task_id)
        if not assets:
            logger.info("Research task %s: no assets to metabolize", task_id)
            return results

        all_content = "\n\n".join(a.get("raw_markdown", "") for a in assets)

        # ── Step 1: Generate synthesis summary ──
        try:
            summary = await self._synthesize_findings(task, all_content)
            self._state.research_task_repo.update(task_id, result_summary=summary)
        except Exception as e:
            logger.warning("Synthesis failed for task %s: %s", task_id, e)
            summary = ""

        # ── Step 2: Memory consolidation (branch-scoped batch) ──
        try:
            node_count = await self._consolidate_to_memory(task, all_content)
            results["memory_nodes_created"] = node_count
        except Exception as e:
            logger.warning("Memory consolidation failed: %s", e)

        # ── Step 3: Bifurcation evaluation ──
        try:
            from backend.metabolisation.bifurcation import evaluate_evidence_perturbation
            for asset in assets:
                diff_score = asset.get("diffractive_score", 0.0)
                if diff_score > 0.78:
                    event_id = await evaluate_evidence_perturbation(
                        app_state=self._state,
                        state_impact_vector=None,  # Would use embedder
                        source_description=f"Research task: {task.get('title', task_id)}",
                    )
                    if event_id:
                        results["bifurcations"] += 1
        except ImportError:
            logger.debug("Bifurcation module not available — skipping")

        # ── Step 4: Update task counters ──
        self._state.research_task_repo.update(
            task_id,
            bifurcation_triggered=1 if results["bifurcations"] > 0 else 0,
        )

        logger.info(
            "Research metabolism complete for %s: %d beliefs, %d nodes, %d bifurcations",
            task_id, results["beliefs_updated"], results["memory_nodes_created"], results["bifurcations"],
        )
        return results

    # ── Synthesis ────────────────────────────────────────────────────

    async def _synthesize_findings(self, task: dict, all_content: str) -> str:
        """Generate a cross-branch executive summary of research findings."""
        try:
            from backend.utils.prompt_loader import get_prompts_dict
            prompt_data = get_prompts_dict("research/synthesizer.yaml")

            llm_provider = getattr(self._state, "llm_provider", None)
            if not llm_provider:
                return "LLM provider not available for synthesis."

            branches = self._state.research_branch_repo.get_by_task(task["id"])
            branch_summaries = "\n\n".join(
                f"Branch {b.get('id','?')[:8]}: {b.get('query','')[:200]} (depth={b.get('depth',0)}, status={b.get('status','?')})"
                for b in branches[:10]
            )

            system_text = prompt_data.get("system", "")
            # Build persona context via ResearchContextBuilder
            try:
                from backend.services.research.context_builder import ResearchContextBuilder
                builder = ResearchContextBuilder(self._state)
                persona = await builder.build_orchestration_context(task.get("objective", ""), "research_synthesis")
                if persona:
                    system_text = persona + "\n\n" + system_text
            except Exception as e:
                logger.warning("Failed to build synthesis persona: %s", e)

            user_text = (prompt_data.get("user", "")).format(
                task_title=task.get("title", ""),
                objective=task.get("objective", ""),
                branch_count=len(branches),
                asset_count=len(self._state.scraped_asset_repo.get_by_task(task["id"])),
                lateral_flights=task.get("lateral_flights", 0),
                branch_summaries=branch_summaries,
            )

            from backend.utils.anti_mastery import apply_anti_mastery_filter
            system_text = apply_anti_mastery_filter(system_text)
            user_text = apply_anti_mastery_filter(user_text)

            from backend.modules.llm_client import generate_unified
            response = await generate_unified(
                provider=llm_provider,
                system_prompt=system_text,
                user_prompt=user_text,
                expect_json=True,
                fallback_value={"summary": "Synthesis LLM call failed — see server logs."},
                temperature=prompt_data.get("temperature", 0.4),
                max_tokens=prompt_data.get("max_tokens", 3072),
            )
            # Log if fallback was used
            if response.get("error"):
                logger.warning("Synthesis LLM call fell back: %s", response["error"])
            result = response.get("json_data") or response.get("content") or {}
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    result = {"summary": str(result)[:2000]}
            return result.get("summary", "") if isinstance(result, dict) else str(result)[:2000]
        except Exception as e:
            logger.error("Synthesis failed: %s", e)
            return f"Research complete. {len(self._state.scraped_asset_repo.get_by_task(task['id']))} assets harvested."

    # ── Memory Consolidation ─────────────────────────────────────────

    async def _consolidate_to_memory(self, task: dict, all_content: str) -> int:
        """Consolidate research findings into memory_nodes.

        Uses the existing consolidation engine (consolidate.yaml) with
        research source tagging. Does NOT use branch-scoped batching in
        this initial implementation — consolidates the full synthesis.
        """
        try:
            bg_engine = getattr(self._state, "background_engine", None)
            if not bg_engine:
                logger.debug("No background engine — skipping memory consolidation")
                return 0

            result = await bg_engine.run("consolidate", {
                "text": all_content[:8000],
                "source_type": "research",
                "source_id": task["id"],
                "conversation_id": task.get("conversation_id") or f"research_{task['id']}",
            })

            if result and result.get("status") == "ok":
                return result.get("nodes_created", 0)
            return 0
        except Exception as e:
            logger.warning("Memory consolidation failed: %s", e)
            return 0


class ResearchMetabolismMixin:
    """Mixin for daemon classes that need to call post-research metabolism."""

    async def metabolize_completed_research(self) -> None:
        """Check for completed research tasks and run metabolism on them."""
        try:
            task_repo = getattr(self, "research_task_repo", None)
            if not task_repo:
                task_repo = getattr(self.app_state, "research_task_repo", None)
            if not task_repo:
                return

            completed = task_repo.list_all(status="completed", limit=5)
            if not completed:
                return

            engine = ResearchMetabolismEngine(self.app_state)
            for task in completed:
                # Check if already metabolized (has result_summary set)
                if task.get("result_summary"):
                    continue
                try:
                    await engine.metabolize_research_results(task)
                except Exception as e:
                    logger.error("Metabolism failed for task %s: %s", task["id"], e)
        except Exception as e:
            logger.warning("Research metabolism scan failed: %s", e)
