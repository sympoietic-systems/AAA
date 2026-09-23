"""Sedimentation Packet Queue — Persistent staging queue for research memory nodes."""

import logging
from collections.abc import Callable
from typing import Any

from backend.utils.research_logger import now_utc_str

logger = logging.getLogger("aaa.research_orchestrator.sedimentation")


class SedimentationPacketQueue:
    """Manages unraked sedimentation packets staged in orchestrator state.

    Packets are stored in orchestrator_state and raked asynchronously
    by the daemon's consolidation cycle.
    See: docs/decisions/ADR-060-research-memory-integration.md
    """

    @staticmethod
    def push(
        state_mgr: Any,
        persist_fn: Callable[[str], None],
        task_id: str,
        phase: str,
        trigger_thresholds: dict,
        raw_context: str,
        proposed_node_type: str,
        confidence: float = 0.0,
    ) -> None:
        """Push a sedimentation packet to the task's persistent queue."""
        s = state_mgr.ensure_state(task_id)
        packet = {
            "phase": phase,
            "trigger_thresholds": trigger_thresholds,
            "raw_context": raw_context[:8000],
            "proposed_node_type": proposed_node_type,
            "confidence": confidence,
            "pushed_at": now_utc_str(),
        }
        s.setdefault("sedimentation_queue", []).append(packet)
        persist_fn(task_id)
        logger.info(
            "Sedimentation packet pushed: task=%s phase=%s type=%s",
            task_id[:8],
            phase,
            proposed_node_type,
        )

    @staticmethod
    def pending(state_mgr: Any, task_id: str) -> list[dict]:
        """Return all unraked sedimentation packets for a task (non-destructive)."""
        s = state_mgr.get_state(task_id)
        return list(s.get("sedimentation_queue", []))

    @staticmethod
    def clear(state_mgr: Any, persist_fn: Callable[[str], None], task_id: str) -> int:
        """Clear all packets from the queue after successful rake. Returns count cleared."""
        s = state_mgr.get_state(task_id)
        count = len(s.get("sedimentation_queue", []))
        s["sedimentation_queue"] = []
        persist_fn(task_id)
        return count
