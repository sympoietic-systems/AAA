"""Belief data serialization helpers.

Extracted from services/belief.py to eliminate repeated dict-building patterns.
"""

import json
import logging

logger = logging.getLogger(__name__)


def _iso(val):
    """Safe isoformat conversion — returns None for falsy values."""
    return val.isoformat() if val else None


def _parse_source_trace(raw_trace):
    """Parse a source_trace JSON string into a list, returning [] on failure."""
    if not raw_trace:
        return []
    try:
        return json.loads(raw_trace)
    except Exception:
        return []


def serialize_belief_event(event) -> dict:
    """Serialize a belief event row into an API-safe dict."""
    mass, conf = _parse_event_rationale(event.rationale)
    return {
        "id": event.id,
        "timestamp": event.timestamp.isoformat(),
        "source_id": event.source_id,
        "source_type": event.source_type,
        "event_type": event.event_type,
        "delta_confidence": event.impact_score,
        "description": event.rationale,
        "mass": mass,
        "confidence": conf,
    }


def serialize_proposal(p) -> dict:
    """Serialize a belief proposal row into an API-safe dict.

    Used by get_beliefs, list_proposals, and get_proposal.
    """
    lifecycle_stage = "nucleation" if p.status in ("pending", "refined") else "collapsed"
    return {
        "id": p.id,
        "label": p.suggested_label or "emergent-belief",
        "statement": p.suggested_statement or p.provisional_statement,
        "category": "methodological",
        "confidence": p.confidence,
        "ontological_mass": p.nucleation_mass,
        "version": 1,
        "vector_16d": p.initial_signature,
        "origin": "emergent",
        "lifecycle_stage": lifecycle_stage,
        "last_reinforced_at": _iso(p.created_at),
        "updated_at": _iso(p.updated_at),
        "events": [],
        "is_proposal": True,
        "proposal_status": p.status,
        "symbia_reflection": p.symbia_reflection,
        "symbia_friction_rationale": p.symbia_friction_rationale,
        "rejection_rationale": p.rejection_rationale,
        "potential_merge_target": p.potential_merge_target,
        "source_trace": _parse_source_trace(p.source_trace),
    }


def _parse_event_rationale(rationale: str | None) -> tuple[float | None, float | None]:
    """Extract mass and confidence values from a belief event rationale string."""
    import re
    if not rationale:
        return None, None
    mass_match = re.search(r"mass=([\d.]+)", rationale)
    conf_match = re.search(r"conf=([\d.]+)", rationale)
    mass = float(mass_match.group(1)) if mass_match else None
    conf = float(conf_match.group(1)) if conf_match else None
    return mass, conf
