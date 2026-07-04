"""Research Metabolism Engine — post-research belief/skill processing.

Two phases:
  1. In-Node (per significant finding): proto-belief proposals, skill nucleation
  2. Post-Research (on task completion): full belief pass, bifurcation, skill scan,
     commitment recalculation, memory consolidation.

See docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Sections 5.6 and 5.7.
"""

import json
import logging
import sqlite3
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

    async def _rake_sedimentation_queue(self, task_id: str) -> int:
        """Rake pending sedimentation packets through ResearchCrystallization.

        Called asynchronously by the daemon's consolidation cycle. Fetches
        pending packets from the orchestrator state, runs crystallization
        via the background engine, persists nodes, and clears the queue.
        See: docs/decisions/ADR-060-research-memory-integration.md
        """
        try:
            # We need the orchestrator to access the task state queue
            orchestrator = getattr(self._state, "research_orchestrator", None)
            if not orchestrator:
                return 0

            packets = orchestrator._pending_sedimentation_packets(task_id)
            if not packets:
                return 0

            bg_engine = getattr(self._state, "background_engine", None)
            if not bg_engine:
                logger.debug("No background engine — skipping sedimentation rake")
                return 0

            task = self._state.research_task_repo.get(task_id)
            conversation_id = (
                task.get("conversation_id") or f"research_{task_id}"
                if task else f"research_{task_id}"
            )

            memory_node_repo = getattr(self._state, "memory_node_repo", None)
            checkpoint_repo = getattr(self._state, "checkpoint_repo", None)
            checkpoint_id = -1
            if checkpoint_repo:
                try:
                    latest = checkpoint_repo.get_latest(conversation_id)
                    if latest:
                        checkpoint_id = latest["id"]
                    else:
                        checkpoint_id = checkpoint_repo.save(
                            conversation_id=conversation_id,
                            message_count=0,
                            summary=f"Research: {task.get('objective', '')[:200]}" if task else "Research",
                            model="research_crystallize",
                        )
                except Exception:
                    pass

            nodes_created = 0
            for packet in packets:
                try:
                    result = await bg_engine.run("research_crystallize", {
                        "text": packet.get("raw_context", ""),
                        "phase": packet.get("phase", "unknown"),
                        "node_type": packet.get("proposed_node_type", "concept"),
                    })
                    content = result.get("content", "")
                    if not content:
                        continue

                    from backend.metabolisation.sedimentation import parse_sedimentation_yaml
                    nodes, _tier = parse_sedimentation_yaml(content)
                    if not nodes:
                        continue

                    for n in nodes:
                        n["source_type"] = "research"
                        n["source_id"] = task_id

                    memory_node_repo.save_nodes(conversation_id, checkpoint_id, nodes)
                    nodes_created += len(nodes)
                    logger.info(
                        "Sedimentation rake: task=%s phase=%s -> %d nodes",
                        task_id[:8], packet.get("phase"), len(nodes),
                    )
                except Exception as e:
                    logger.warning("Sedimentation rake failed for packet: %s", e)

            if nodes_created > 0:
                orchestrator._clear_sedimentation_queue(task_id)

            return nodes_created
        except Exception as e:
            logger.warning("Sedimentation rake failed for task %s: %s", task_id[:8], e)
            return 0

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

    async def rake_research_sedimentation(self) -> int:
        """Rake pending sedimentation packets from all active/completed research tasks.

        Called during daemon idle cycles. Processes packets through ResearchCrystallization
        and persists resulting memory nodes. Does not depend on the orchestrator
        being alive — reloads state from the task's orchestrator_state JSON.
        See: docs/decisions/ADR-060-research-memory-integration.md
        """
        try:
            task_repo = getattr(self, "research_task_repo", None)
            if not task_repo:
                task_repo = getattr(self.app_state, "research_task_repo", None)
            if not task_repo:
                return 0

            bg_engine = getattr(self, "background_engine", None)
            bg_engine = bg_engine or getattr(self.app_state, "background_engine", None)
            if not bg_engine:
                return 0

            active_tasks = task_repo.list_all(status="active", limit=5)
            pending_tasks = task_repo.list_all(status="completed", limit=5)
            tasks_to_rake = (active_tasks or []) + (pending_tasks or [])

            total_nodes = 0
            for task in tasks_to_rake:
                orch_state_raw = task.get("orchestrator_state")
                if not orch_state_raw:
                    continue
                try:
                    state = (json.loads(orch_state_raw)
                             if isinstance(orch_state_raw, str) else orch_state_raw)
                except Exception:
                    continue

                packets = state.get("sedimentation_queue", [])
                if not packets:
                    continue

                conversation_id = (
                    task.get("conversation_id") or f"research_{task['id']}"
                )
                task_id = task["id"]
                task_nodes = 0

                memory_node_repo = getattr(self.app_state, "memory_node_repo", None)
                checkpoint_repo = getattr(self.app_state, "checkpoint_repo", None)
                if not memory_node_repo:
                    continue

                # Ensure conversation record exists for FK constraint
                if checkpoint_repo:
                    try:
                        db_path = getattr(self.app_state, "config", {}).get("database", {}).get("path", "")
                        if db_path:
                            from backend.storage.database import get_db_path
                            db_conn = sqlite3.connect(str(get_db_path(db_path)))
                            db_conn.execute("PRAGMA foreign_keys=ON")
                            db_conn.execute(
                                "INSERT OR IGNORE INTO conversations (id, title, agent_id) VALUES (?, ?, ?)",
                                (conversation_id, f"Research: {task.get('objective', '')[:100]}", "symbia"),
                            )
                            db_conn.commit()
                            db_conn.close()
                    except Exception:
                        pass

                # Get or create a checkpoint
                checkpoint_id = -1
                if checkpoint_repo:
                    try:
                        latest = checkpoint_repo.get_latest(conversation_id)
                        if latest:
                            checkpoint_id = latest["id"]
                        else:
                            checkpoint_id = checkpoint_repo.save(
                                conversation_id=conversation_id,
                                message_count=0,
                                summary=f"Research: {task.get('objective', '')[:200]}",
                                model="research_crystallize",
                            )
                    except Exception:
                        pass

                for packet in packets:
                    try:
                        result = await bg_engine.run("research_crystallize", {
                            "text": packet.get("raw_context", ""),
                            "phase": packet.get("phase", "unknown"),
                            "node_type": packet.get("proposed_node_type", "concept"),
                        })
                        content = result.get("content", "")
                        if not content:
                            continue

                        from backend.metabolisation.sedimentation import parse_sedimentation_yaml
                        nodes, _tier = parse_sedimentation_yaml(content)
                        if not nodes:
                            continue

                        for n in nodes:
                            n["source_type"] = "research"
                            n["source_id"] = task_id

                        memory_node_repo.save_nodes(conversation_id, checkpoint_id, nodes)
                        task_nodes += len(nodes)
                    except Exception:
                        pass

                if task_nodes > 0:
                    state["sedimentation_queue"] = []
                    task_repo.update(
                        task_id,
                        orchestrator_state=json.dumps(state, default=str, ensure_ascii=False),
                    )
                    total_nodes += task_nodes
                    logger.info(
                        "Sedimentation rake: task=%s %d packets -> %d nodes",
                        task_id[:8], len(packets), task_nodes,
                    )

            return total_nodes
        except Exception as e:
            logger.warning("Research sedimentation rake failed: %s", e)
            return 0
