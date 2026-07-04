"""Dream Daemon Research Integration — background autonomous research proposals.

Adds _scan_and_propose_research() to the AutopoieticDreamDaemon.
During idle periods, scans for Tension Hotspots in active beliefs
and creates PROPOSED research tasks for user review.

See docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 13.
"""

import asyncio
import logging

logger = logging.getLogger("aaa.dream_research")


class DreamResearchMixin:
    """Mixin for AutopoieticDreamDaemon — background research proposal generation."""

    async def _scan_and_propose_research(self) -> None:
        """Scan for tension hotspots and create research proposals.

        Called during the daemon's idle loop. Does NOT execute research
        directly — creates PROPOSED tasks awaiting user approval.
        Respects config limits on max concurrent proposals.
        """
        task_config = self.app_state.config.get("research_tasks", {})
        if not task_config.get("enabled", False):
            return

        task_repo = getattr(self.app_state, "research_task_repo", None)
        if not task_repo:
            return

        belief_repo = getattr(self.app_state, "belief_repo", None)
        if not belief_repo:
            return

        manager = getattr(self.app_state, "research_task_manager", None)
        if not manager:
            return

        # ── Guard: Don't exceed max pending proposals ──
        pending_count = task_repo.count_by_status("proposed")
        max_startup = task_config.get("max_startup_proposals", 3)
        if pending_count >= max_startup:
            return

        # ── Find Tension Hotspots ──
        try:
            beliefs = belief_repo.get_active()
        except Exception:
            try:
                beliefs = belief_repo.list_active()
            except Exception:
                return

        if not beliefs:
            return

        # Find beliefs with lowest confidence (proxy for tension)
        stressed = sorted(
            [b for b in beliefs if b.get("lifecycle_stage") == "crystallized"],
            key=lambda b: b.get("confidence", 0.5),
        )
        if not stressed:
            return

        for belief in stressed[:2]:  # Check top 2 most stressed beliefs
            confidence = float(belief.get("confidence", 0.5))
            stress_score = 1.0 - confidence

            if stress_score < 0.65:
                continue

            # ── Guard: Don't duplicate proposals for same belief ──
            already_proposed = task_repo.list_all(status="proposed", limit=50)
            duplicate = any(
                belief.get("label", "") in p.get("objective", "")
                for p in already_proposed
            )
            if duplicate:
                continue

            # ── Create proposal ──
            belief_label = belief.get("label", "unknown")
            belief_statement = belief.get("statement", "")
            objective = (
                f"Critical analysis regarding: {belief_label} — {belief_statement[:100]}"
            )
            rationale = (
                f"Tension hotspot detected during idle monitoring. "
                f"Belief '{belief_label}' has confidence {confidence:.2f} "
                f"(stress: {stress_score:.2f}). External evidence "
                f"could help resolve this cognitive tension."
            )

            try:
                task_id = manager.create_task(
                    objective=objective,
                    trigger_source="symbia_dream",
                    title=f"Dream Proposal: {belief_label}",
                    status="proposed",
                    priority=4,
                    max_depth=task_config.get("daemon_max_depth", 2),
                    max_breadth=task_config.get("daemon_max_breadth", 2),
                    is_agonistic=True,
                    budget_limit_usd=task_config.get(
                        "dream_research_usd",
                        self.app_state.config.get("metabolic_budgets", {}).get("dream_research_usd", 0.50),
                    ),
                    proposal_rationale=rationale,
                )

                # Dispatch notification
                try:
                    notif_repo = getattr(self.app_state, "notification_repo", None)
                    if notif_repo:
                        notif_repo.create(
                            type="trace",
                            snippet=f"Dream proposal: {belief_label} (stress: {stress_score:.2f})",
                            source="dream_daemon:proposal",
                            source_type="research",
                            source_id=task_id,
                        )
                except Exception:
                    pass

                logger.info(
                    "Dream Daemon proposed research: '%s' (stress=%.2f) -> %s",
                    belief_label, stress_score, task_id[:8],
                )
            except Exception as e:
                logger.warning("Dream daemon failed to create proposal: %s", e)

    async def metabolize_research_on_idle(self) -> None:
        """Run post-research metabolism for completed tasks during idle."""
        try:
            from backend.metabolisation.research_metabolism import ResearchMetabolismMixin
            mixin = ResearchMetabolismMixin()
            mixin.app_state = self.app_state
            await mixin.metabolize_completed_research()
        except Exception as e:
            logger.warning("Research metabolism during idle failed: %s", e)

    async def _drain_research_queue(self) -> None:
        """Periodic safety net: drain queued research tasks that weren't auto-activated.

        The primary dispatch path is fire-and-forget via asyncio.create_task()
        in ResearchTaskManager.queue(). This method catches tasks that slipped
        through (e.g., event loop under load dropped the task, or rapid queuing
        exceeded concurrent slots temporarily).
        """
        try:
            manager = getattr(self.app_state, "research_task_manager", None)
            if not manager:
                return

            # Respect manual_mode — user wants explicit control
            if manager.config.get("manual_mode", False):
                return

            # Only drain if slots are available
            semaphore = getattr(manager, "_active_semaphore", None)
            if semaphore and semaphore.locked():
                return

            task = manager.task_repo.get_next_queued()
            if not task:
                return

            task_id = task["id"]
            logger.info("Daemon safety net: activating stuck research task %s", task_id[:8])
            manager.transition(task_id, "active")
            coro = manager._execute_task(task_id)
            asyncio_task = asyncio.create_task(coro)
            manager._active_tasks[task_id] = asyncio_task
        except Exception as e:
            logger.debug("Research queue drain: %s", e)
