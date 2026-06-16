"""Rhizome Web Probe — pipeline module for autonomous deep web research.

Triggers when stagnation or belief tension is detected during pipeline
execution. Creates research tasks via ResearchTaskManager — does NOT
execute synchronously. Research runs asynchronously in the background.

Positioned between perception (Module 3) and conversation_metrics (Module 5)
in the processing pipeline.

See docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 8.
"""

import logging
from typing import Optional

from backend.modules.base import ProcessingModule, ModuleResult
from backend.pipeline.metadata import ModuleMeta

logger = logging.getLogger("aaa.rhizome_web_probe")


class RhizomeWebProbeModule(ProcessingModule):
    """Pipeline module that initiates deep web research.

    Evaluates trigger conditions (stagnation, belief tension, curiosity)
    and delegates task creation to ResearchTaskManager. The actual
    research executes asynchronously — this module returns immediately.
    """

    def __init__(self, config: dict):
        self._config = config
        self._app_state = None  # Set by _set_app_state after bootstrap

    def _set_app_state(self, app_state) -> None:
        """Called after AppState is assembled during bootstrap."""
        self._app_state = app_state

    @property
    def _rhizome_config(self) -> dict:
        if self._app_state:
            return self._app_state.config.get("rhizome_research", {})
        return self._config.get("rhizome_research", {})

    @property
    def name(self) -> str:
        return "rhizome_web_probe"

    @property
    def module_meta(self) -> ModuleMeta:
        return ModuleMeta(
            name="rhizome_web_probe",
            description=(
                "Detects conversational stagnation and belief tension, "
                "triggering autonomous deep web research. Research tasks "
                "execute asynchronously via ResearchTaskManager."
            ),
            category="ingestion",
            always_run=True,
            triggers=["research", "web", "probe", "stagnation", "tension"],
        )

    def validate(self) -> bool:
        config = self._rhizome_config
        if not config.get("enabled", False):
            logger.debug("Rhizome research disabled in config")
            return True  # Not an error, just skip
        return True

    async def process(self, payload: dict) -> dict:
        config = self._rhizome_config
        if not config.get("enabled", False):
            return payload

        conversation_id = payload.get("conversation_id", "")
        if not conversation_id:
            return payload

        # ── Guard: Don't trigger if already researching this conversation ──
        task_manager = getattr(self._app_state, "research_task_manager", None) if self._app_state else None
        if task_manager and task_manager.has_active_for_conversation(conversation_id):
            return payload

        # ── Trigger Condition 1: Stagnation ──
        metrics = payload.get("metrics", {})
        stagnation_index = metrics.get("stagnation_index", metrics.get("boringness", 0.0))
        is_stagnant = stagnation_index >= config.get("agonistic_stagnation_threshold", 0.7)

        # ── Trigger Condition 2: Tension hotspots ──
        tension_hotspots = payload.get("proto_belief_proposals", []) or []
        has_tension = len(tension_hotspots) > 0

        # ── Trigger Condition 3: Minimum curiosity ──
        homeostatic = payload.get("homeostatic_regulator", {}) or {}
        curiosity = homeostatic.get("curiosity", 0.5)
        is_curious = curiosity >= config.get("min_curiosity_to_probe", 0.3)

        if not is_curious or (not is_stagnant and not has_tension):
            return payload

        # ── Formulate probe query ──
        target_query = payload.get("content", "")[:200]
        if has_tension:
            target_query = f"Disrupt assumptions: {tension_hotspots[0].get('statement', tension_hotspots[0])}"

        if not target_query or len(target_query) < 10:
            return payload

        # ── Create NOTIFICATION — don't auto-execute ──
        # In Phase 1, all Symbia-initiated research is PROPOSED (requires user approval).
        # The pipeline module only creates the notification/proposal.
        # Execution happens via the Research Console AFTER user approval.

        if task_manager:
            try:
                rationale = (
                    "Stagnation detected" if is_stagnant else "Belief tension detected"
                )
                task_id = task_manager.create_task(
                    objective=target_query,
                    trigger_source="symbia_stagnation" if is_stagnant else "symbia_conflict",
                    title=target_query[:80],
                    conversation_id=conversation_id,
                    status="proposed",
                    priority=3,
                    max_depth=config.get("daemon_max_depth", config.get("max_depth", 2)),
                    max_breadth=config.get("daemon_max_breadth", config.get("max_breadth", 2)),
                    is_agonistic=is_stagnant,
                    budget_limit_usd=0.25,
                    proposal_rationale=rationale,
                )

                payload["research_proposal_id"] = task_id
                logger.info(
                    "Rhizome web probe created proposal %s for conv %s (stagnation=%.2f)",
                    task_id[:8], conversation_id, stagnation_index,
                )
            except Exception as e:
                logger.warning("Failed to create research proposal: %s", e)

        return payload
