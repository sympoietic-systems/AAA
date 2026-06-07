import json
import sqlite3
from datetime import datetime

import numpy as np

from .models import (
    BeliefEvent,
    BeliefNode,
    Conversation,
    ErrorLogEntry,
    Message,
    MetricsRecord,
    PerceptionSediment,
    SemanticKnot,
)


def _row_to_message(row: sqlite3.Row) -> Message:
    return Message(
        id=row["id"],
        timestamp=datetime.fromisoformat(row["timestamp"]),
        agent_id=row["agent_id"] if "agent_id" in row.keys() else "",
        conversation_id=row["conversation_id"] if "conversation_id" in row.keys() else "",
        speaker=row["speaker"],
        content=row["content"],
        content_tokens=row["content_tokens"] if "content_tokens" in row.keys() else 0,
        thinking=row["thinking"] if "thinking" in row.keys() else None,
        thinking_tokens=row["thinking_tokens"] if "thinking_tokens" in row.keys() else None,
        context_sent=row["context_sent"] if "context_sent" in row.keys() else None,
        embedding=row["embedding"],
        embedding_model=row["embedding_model"],
        embedding_dim=row["embedding_dim"],
        model_used=row["model_used"] if "model_used" in row.keys() else None,
        provider_used=row["provider_used"] if "provider_used" in row.keys() else None,
        structural_signature=row["structural_signature"] if ("structural_signature" in row.keys() and row["structural_signature"] is not None) else b"",
        structural_justification=row["structural_justification"] if "structural_justification" in row.keys() else None,
        note_count=row["note_count"] if "note_count" in row.keys() else 0,
        metabolized=row["metabolized"] if "metabolized" in row.keys() else 0,
    )


def _row_to_conversation(row: sqlite3.Row) -> Conversation:
    return Conversation(
        id=row["id"],
        title=row["title"],
        agent_id=row["agent_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        message_count=row["message_count"] if "message_count" in row.keys() else 0,
        somatic_reservoir_ad=row["somatic_reservoir_ad"] if "somatic_reservoir_ad" in row.keys() else 0.0,
        matrix_warping=row["matrix_warping"] if "matrix_warping" in row.keys() else 0.0,
        immunological_directive_active=row["immunological_directive_active"] if "immunological_directive_active" in row.keys() else 0,
        requires_consolidation=row["requires_consolidation"] if "requires_consolidation" in row.keys() else 0,
        last_consolidated_at=datetime.fromisoformat(row["last_consolidated_at"]) if ("last_consolidated_at" in row.keys() and row["last_consolidated_at"]) else None,
    )


def _row_to_metrics(row: sqlite3.Row) -> MetricsRecord:
    return MetricsRecord(
        message_id=row["message_id"],
        s_t=row["s_t"],
        novelty=row["novelty"],
        rolling_entropy=row["rolling_entropy"],
        coupling=row["coupling"],
        agent_divergence=row["agent_divergence"],
        deficit=row["deficit"],
        reverse_perturbation=row["reverse_perturbation"] if "reverse_perturbation" in row.keys() else None,
        surprise_index=row["surprise_index"] if "surprise_index" in row.keys() else None,
        mutual_perturbation=row["mutual_perturbation"] if "mutual_perturbation" in row.keys() else None,
        vitality=row["vitality"] if "vitality" in row.keys() else None,
        phase_shifts=row["phase_shifts"] if "phase_shifts" in row.keys() else None,
        boringness=row["boringness"] if "boringness" in row.keys() else None,
        conceptual_velocity=row["conceptual_velocity"] if "conceptual_velocity" in row.keys() else None,
        divergence_resolution_ratio=row["divergence_resolution_ratio"] if "divergence_resolution_ratio" in row.keys() else None,
        paskian_health=row["paskian_health"] if "paskian_health" in row.keys() else None,
        temperature_rec=row["temperature_rec"],
        presence_penalty_rec=row["presence_penalty_rec"],
        frequency_penalty_rec=row["frequency_penalty_rec"],
        homeostatic_state=row["homeostatic_state"],
    )


def _row_to_perception_sediment(row: sqlite3.Row) -> PerceptionSediment:
    opacity = row["opacity"] if "opacity" in row.keys() else 0
    opacity_meta = row["opacity_meta"] if "opacity_meta" in row.keys() else None
    structural_signature = row["structural_signature"] if ("structural_signature" in row.keys() and row["structural_signature"] is not None) else b""
    return PerceptionSediment(
        id=row["id"],
        conversation_id=row["conversation_id"],
        file_name=row["file_name"],
        file_type=row["file_type"],
        chunk_index=row["chunk_index"],
        chunk_text=row["chunk_text"],
        embedding=row["embedding"],
        embedding_model=row["embedding_model"],
        token_count=row["token_count"],
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        opacity=opacity,
        opacity_meta=opacity_meta,
        structural_signature=structural_signature,
    )


def _row_to_memory_node(row: sqlite3.Row) -> dict:
    tendril_ids = []
    try:
        tendril_ids = json.loads(row["tendril_ids"]) if row["tendril_ids"] else []
    except (json.JSONDecodeError, TypeError):
        pass
    return {
        "id": row["id"],
        "conversation_id": row["conversation_id"],
        "checkpoint_id": row["checkpoint_id"],
        "node_type": row["node_type"],
        "intensity": row["intensity"],
        "scar": row["scar"],
        "glitch_potential": row["glitch_potential"],
        "intra_active_text": row["intra_active_text"],
        "surface_fragment": row["surface_fragment"],
        "agential_symmetry": row["agential_symmetry"],
        "diffractive_key": row["diffractive_key"],
        "tendril_ids": tendril_ids,
        "created_at": row["created_at"],
    }


def _row_to_belief_node(row: sqlite3.Row) -> BeliefNode:
    created = row["created_at"]
    updated = row["updated_at"]
    last_reinforced = None
    try:
        last_reinforced_raw = row["last_reinforced_at"]
        if last_reinforced_raw:
            last_reinforced = datetime.fromisoformat(last_reinforced_raw) if isinstance(last_reinforced_raw, str) else last_reinforced_raw
    except (IndexError, KeyError):
        pass

    lifecycle = "crystallized"
    try:
        lifecycle = row["lifecycle_stage"] or "crystallized"
    except (IndexError, KeyError):
        pass

    last_dreamed = None
    try:
        last_dreamed_raw = row["last_dreamed_at"]
        if last_dreamed_raw:
            last_dreamed = datetime.fromisoformat(last_dreamed_raw) if isinstance(last_dreamed_raw, str) else last_dreamed_raw
    except (IndexError, KeyError):
        pass

    return BeliefNode(
        id=row["id"],
        agent_id=row["agent_id"],
        label=row["label"],
        statement=row["statement"],
        origin=row["origin"],
        confidence=row["confidence"],
        ontological_mass=row["ontological_mass"],
        somatic_anchor=row["somatic_anchor"],
        vector_16d=row["vector_16d"],
        lifecycle_stage=lifecycle,
        last_reinforced_at=last_reinforced,
        last_dreamed_at=last_dreamed,
        created_at=datetime.fromisoformat(created) if isinstance(created, str) else created,
        updated_at=datetime.fromisoformat(updated) if isinstance(updated, str) else updated,
    )


def _row_to_belief_event(row: sqlite3.Row) -> BeliefEvent:
    ts = row["timestamp"]
    return BeliefEvent(
        id=row["id"],
        timestamp=datetime.fromisoformat(ts) if isinstance(ts, str) else ts,
        belief_id=row["belief_id"],
        source_type=row["source_type"],
        source_id=row["source_id"],
        alignment_coefficient=row["alignment_coefficient"],
        perturbation_magnitude=row["perturbation_magnitude"],
        event_type=row["event_type"],
        impact_score=row["impact_score"],
        rationale=row["rationale"],
    )


def _row_to_semantic_knot(row: sqlite3.Row) -> SemanticKnot:
    created = row["created_at"]
    return SemanticKnot(
        id=row["id"],
        conversation_id=row["conversation_id"],
        created_at=datetime.fromisoformat(created) if isinstance(created, str) else created,
        weight=row["weight"],
        concept_payload=row["concept_payload"],
        embedding=row["embedding"],
        embedding_model=row["embedding_model"],
        token_count=row["token_count"],
        structural_signature=row["structural_signature"] or b"",
    )
