import contextlib
import json
import sqlite3
from datetime import datetime

from .models import (
    BeliefEvent,
    BeliefNode,
    BeliefProposal,
    BeliefStatementVersion,
    CommitmentEvent,
    CommitmentNode,
    Conversation,
    ExpertiseNode,
    Message,
    MessageLink,
    MetricsRecord,
    PerceptionSediment,
    PersonalityState,
    SemanticKnot,
    SkillEvent,
    SkillNode,
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
        structural_signature=row["structural_signature"]
        if ("structural_signature" in row.keys() and row["structural_signature"] is not None)
        else b"",
        structural_justification=row["structural_justification"] if "structural_justification" in row.keys() else None,
        note_count=row["note_count"] if "note_count" in row.keys() else 0,
        metabolized=row["metabolized"] if "metabolized" in row.keys() else 0,
        parent_message_id=row["parent_message_id"] if "parent_message_id" in row.keys() else None,
    )


def _row_to_message_link(row: sqlite3.Row) -> MessageLink:
    created = row["created_at"]
    return MessageLink(
        id=row["id"],
        source_id=row["source_id"],
        target_id=row["target_id"],
        link_type=row["link_type"],
        created_at=datetime.fromisoformat(created) if isinstance(created, str) else created,
        status=row["status"] if "status" in row.keys() else "active",
        justification=row["justification"] if "justification" in row.keys() else "",
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
        last_consolidated_at=datetime.fromisoformat(row["last_consolidated_at"])
        if ("last_consolidated_at" in row.keys() and row["last_consolidated_at"])
        else None,
    )


def _row_to_metrics(row: sqlite3.Row) -> MetricsRecord:
    return MetricsRecord(
        message_id=row["message_id"],
        s_t=row["s_t"],
        rolling_entropy=row["rolling_entropy"] if "rolling_entropy" in row.keys() else None,
        novelty=row["novelty"] if "novelty" in row.keys() else 0.0,
        coupling=row["coupling"] if "coupling" in row.keys() else None,
        agent_divergence=row["agent_divergence"] if "agent_divergence" in row.keys() else None,
        deficit=row["deficit"] if "deficit" in row.keys() else 0.0,
        reverse_perturbation=row["reverse_perturbation"] if "reverse_perturbation" in row.keys() else None,
        surprise_index=row["surprise_index"] if "surprise_index" in row.keys() else None,
        mutual_perturbation=row["mutual_perturbation"] if "mutual_perturbation" in row.keys() else None,
        vitality=row["vitality"] if "vitality" in row.keys() else None,
        phase_shifts=row["phase_shifts"] if "phase_shifts" in row.keys() else None,
        boringness=row["boringness"] if "boringness" in row.keys() else None,
        conceptual_velocity=row["conceptual_velocity"] if "conceptual_velocity" in row.keys() else None,
        divergence_resolution_ratio=row["divergence_resolution_ratio"] if "divergence_resolution_ratio" in row.keys() else None,
        paskian_health=row["paskian_health"] if "paskian_health" in row.keys() else None,
        temperature_rec=row["temperature_rec"] if "temperature_rec" in row.keys() else None,
        presence_penalty_rec=row["presence_penalty_rec"] if "presence_penalty_rec" in row.keys() else None,
        frequency_penalty_rec=row["frequency_penalty_rec"] if "frequency_penalty_rec" in row.keys() else None,
        homeostatic_state=row["homeostatic_state"] if "homeostatic_state" in row.keys() else None,
    )


def _row_to_perception_sediment(row: sqlite3.Row) -> PerceptionSediment:
    opacity = row["opacity"] if "opacity" in row.keys() else 0
    opacity_meta = row["opacity_meta"] if "opacity_meta" in row.keys() else None
    structural_signature = (
        row["structural_signature"]
        if ("structural_signature" in row.keys() and row["structural_signature"] is not None)
        else b""
    )
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
    with contextlib.suppress((json.JSONDecodeError, TypeError)):
        tendril_ids = json.loads(row["tendril_ids"]) if row["tendril_ids"] else []
    source_type = "conversation"
    with contextlib.suppress((IndexError, KeyError)):
        source_type = row["source_type"] or "conversation"

    source_id = ""
    with contextlib.suppress((IndexError, KeyError)):
        source_id = row["source_id"] or ""

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
        "source_type": source_type,
        "source_id": source_id,
    }


def _row_to_belief_node(row: sqlite3.Row) -> BeliefNode:
    created = row["created_at"]
    updated = row["updated_at"]
    last_reinforced = None
    try:
        last_reinforced_raw = row["last_reinforced_at"]
        if last_reinforced_raw:
            last_reinforced = (
                datetime.fromisoformat(last_reinforced_raw)
                if isinstance(last_reinforced_raw, str)
                else last_reinforced_raw
            )
    except (IndexError, KeyError):
        pass

    lifecycle = "crystallized"
    with contextlib.suppress((IndexError, KeyError)):
        lifecycle = row["lifecycle_stage"] or "crystallized"

    last_dreamed = None
    try:
        last_dreamed_raw = row["last_dreamed_at"]
        if last_dreamed_raw:
            last_dreamed = (
                datetime.fromisoformat(last_dreamed_raw) if isinstance(last_dreamed_raw, str) else last_dreamed_raw
            )
    except (IndexError, KeyError):
        pass

    evolved_from = None
    with contextlib.suppress((IndexError, KeyError)):
        evolved_from = row["evolved_from_proposal"]

    genesis_mats = None
    with contextlib.suppress((IndexError, KeyError)):
        genesis_mats = row["genesis_materials"]

    version = 1
    with contextlib.suppress((IndexError, KeyError)):
        version = row["version"] or 1

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
        evolved_from_proposal=evolved_from,
        genesis_materials=genesis_mats,
        version=version,
        last_reinforced_at=last_reinforced,
        last_dreamed_at=last_dreamed,
        created_at=datetime.fromisoformat(created) if isinstance(created, str) else created,
        updated_at=datetime.fromisoformat(updated) if isinstance(updated, str) else updated,
    )


def _row_to_belief_proposal(row: sqlite3.Row) -> BeliefProposal:
    created = row["created_at"]
    updated = row["updated_at"]

    potential_target = None
    with contextlib.suppress((IndexError, KeyError)):
        potential_target = row["potential_merge_target"]

    return BeliefProposal(
        id=row["id"],
        agent_id=row["agent_id"],
        provisional_statement=row["provisional_statement"],
        source_trace=row["source_trace"],
        initial_signature=row["initial_signature"],
        nucleation_mass=row["nucleation_mass"],
        confidence=row["confidence"],
        status=row["status"],
        suggested_label=row["suggested_label"],
        suggested_statement=row["suggested_statement"],
        potential_merge_target=potential_target,
        symbia_reflection=row["symbia_reflection"],
        symbia_friction_rationale=row["symbia_friction_rationale"],
        rejection_rationale=row["rejection_rationale"],
        created_at=datetime.fromisoformat(created) if isinstance(created, str) else created,
        updated_at=datetime.fromisoformat(updated) if isinstance(updated, str) else updated,
    )


def _row_to_belief_statement_version(row: sqlite3.Row) -> BeliefStatementVersion:
    created = row["created_at"]
    return BeliefStatementVersion(
        id=row["id"],
        belief_id=row["belief_id"],
        version=row["version"],
        statement=row["statement"],
        vector_16d=row["vector_16d"],
        change_reason=row["change_reason"],
        created_at=datetime.fromisoformat(created) if isinstance(created, str) else created,
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


def _row_to_skill_node(row: sqlite3.Row) -> SkillNode:
    created = row["created_at"]
    updated = row["updated_at"]
    last_used = None
    try:
        last_used_raw = row["last_used_at"]
        if last_used_raw:
            last_used = datetime.fromisoformat(last_used_raw) if isinstance(last_used_raw, str) else last_used_raw
    except (IndexError, KeyError):
        pass

    return SkillNode(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        content=row["content"],
        short_content=row["short_content"] or "",
        always_active=bool(row["always_active"]),
        trigger_keywords=row["trigger_keywords"] or "[]",
        lifecycle_stage=row["lifecycle_stage"] or "nucleation",
        confidence=row["confidence"] or 0.0,
        ontological_mass=row["ontological_mass"] or 0.05,
        vector_16d=row["vector_16d"] or "[]",
        source=row["source"] or "authored",
        version=row["version"] or 1,
        changelog=row["changelog"] or "",
        attunement_notes=row["attunement_notes"] or "[]",
        last_used_at=last_used,
        created_at=datetime.fromisoformat(created) if isinstance(created, str) else created,
        updated_at=datetime.fromisoformat(updated) if isinstance(updated, str) else updated,
    )


def _row_to_skill_event(row: sqlite3.Row) -> SkillEvent:
    created = row["created_at"]
    return SkillEvent(
        id=row["id"],
        skill_id=row["skill_id"],
        event_type=row["event_type"],
        source_type=row["source_type"] or "",
        rationale=row["rationale"] or "",
        annotation=row["annotation"] or "",
        created_at=datetime.fromisoformat(created) if isinstance(created, str) else created,
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


def _row_to_commitment_node(row: sqlite3.Row) -> CommitmentNode:
    created = row["created_at"]
    updated = row["updated_at"]
    return CommitmentNode(
        id=row["id"],
        agent_id=row["agent_id"] if "agent_id" in row.keys() else "symbia",
        label=row["label"],
        statement=row["statement"],
        lifecycle_stage=row["lifecycle_stage"] or "active",
        confidence=row["confidence"] or 0.0,
        ontological_mass=row["ontological_mass"] or 1.0,
        vector_16d=row["vector_16d"] or "[]",
        nucleation_rationale=row["nucleation_rationale"] if "nucleation_rationale" in row.keys() else None,
        collapse_rationale=row["collapse_rationale"] if "collapse_rationale" in row.keys() else None,
        created_at=datetime.fromisoformat(created) if isinstance(created, str) else created,
        updated_at=datetime.fromisoformat(updated) if isinstance(updated, str) else updated,
    )


def _row_to_commitment_event(row: sqlite3.Row) -> CommitmentEvent:
    created = row["created_at"]
    return CommitmentEvent(
        id=row["id"],
        commitment_id=row["commitment_id"],
        event_type=row["event_type"] or "",
        rationale=row["rationale"] if "rationale" in row.keys() else None,
        mass_before=row["mass_before"] if "mass_before" in row.keys() else None,
        mass_after=row["mass_after"] if "mass_after" in row.keys() else None,
        confidence_before=row["confidence_before"] if "confidence_before" in row.keys() else None,
        confidence_after=row["confidence_after"] if "confidence_after" in row.keys() else None,
        created_at=datetime.fromisoformat(created) if isinstance(created, str) else created,
    )


def _row_to_expertise_node(row: sqlite3.Row) -> ExpertiseNode:
    created = row["created_at"]
    updated = row["updated_at"]
    last_signal = None
    try:
        raw = row["last_signal_at"]
        if raw:
            last_signal = datetime.fromisoformat(raw) if isinstance(raw, str) else raw
    except (IndexError, KeyError):
        pass
    description = ""
    with contextlib.suppress((IndexError, KeyError)):
        description = row["description"] or ""
    return ExpertiseNode(
        id=row["id"],
        agent_id=row["agent_id"] if "agent_id" in row.keys() else "symbia",
        domain=row["domain"],
        description=description,
        lifecycle_stage=row["lifecycle_stage"] or "proto",
        ontological_mass=row["ontological_mass"] or 0.05,
        level_label=row["level_label"] or "nascent",
        vector_16d=row["vector_16d"] or "[]",
        signal_count=row["signal_count"] or 0,
        last_signal_at=last_signal,
        crystallization_rationale=row["crystallization_rationale"] if "crystallization_rationale" in row.keys() else None,
        created_at=datetime.fromisoformat(created) if isinstance(created, str) else created,
        updated_at=datetime.fromisoformat(updated) if isinstance(updated, str) else updated,
    )


def _row_to_personality_state(row: sqlite3.Row) -> PersonalityState:
    updated = row["updated_at"]
    last_rec = None
    try:
        raw = row["last_recomputed_at"]
        if raw:
            last_rec = datetime.fromisoformat(raw) if isinstance(raw, str) else raw
    except (IndexError, KeyError):
        pass
    return PersonalityState(
        id=row["id"],
        agent_id=row["agent_id"] if "agent_id" in row.keys() else "symbia",
        aspirational_traits_json=row["aspirational_traits_json"] or "{}",
        active_commitment_ids_json=row["active_commitment_ids_json"] or "[]",
        trait_computation_version=row["trait_computation_version"] or 1,
        last_recomputed_at=last_rec,
        updated_at=datetime.fromisoformat(updated) if isinstance(updated, str) else updated,
    )
