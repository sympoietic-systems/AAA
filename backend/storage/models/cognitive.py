"""Cognitive domain storage models (beliefs, skills, commitments, personality)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class BeliefNode:
    id: str
    agent_id: str
    label: str
    statement: str
    origin: str
    confidence: float
    ontological_mass: float
    somatic_anchor: str
    vector_16d: str  # JSON list
    lifecycle_stage: str = "crystallized"
    evolved_from_proposal: str | None = None
    genesis_materials: str | None = None  # JSON list
    version: int = 1
    last_reinforced_at: datetime | None = None
    last_dreamed_at: datetime | None = None
    created_at: datetime = datetime.min
    updated_at: datetime = datetime.min
    # 13C: Ghost merging persistence — track which belief absorbed this one
    merged_from: str | None = None  # JSON list of absorbed ghost IDs
    merged_into: str | None = None  # ID of the keeper belief that absorbed this ghost


@dataclass
class BeliefProposal:
    id: str
    agent_id: str
    provisional_statement: str
    source_trace: str  # JSON string representation of source list
    initial_signature: str  # JSON string representation of 16D vector
    nucleation_mass: float
    confidence: float
    status: str
    suggested_label: str | None = None
    suggested_statement: str | None = None
    potential_merge_target: str | None = None
    symbia_reflection: str | None = None
    symbia_friction_rationale: str | None = None
    rejection_rationale: str | None = None
    admission_history: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = datetime.min
    updated_at: datetime = datetime.min


@dataclass
class BeliefStatementVersion:
    id: str
    belief_id: str
    version: int
    statement: str
    vector_16d: str  # JSON string representation of 16D vector
    change_reason: str | None = None
    created_at: datetime = datetime.min


@dataclass
class BeliefEvent:
    id: str
    timestamp: datetime
    belief_id: str
    source_type: str
    source_id: str | None
    alignment_coefficient: float | None
    perturbation_magnitude: float | None
    event_type: str
    impact_score: float
    rationale: str | None
    impact_quantity: str | None = None
    impact_unit: str | None = None
    delta_mass: float | None = None
    confidence_delta: float | None = None


@dataclass
class BeliefTension:
    belief_a_id: str
    belief_b_id: str
    cosine_similarity: float
    tension_magnitude: float
    last_updated: datetime = datetime.min


@dataclass
class EcosystemSnapshot:
    timestamp: datetime
    diversity: float
    coherence: float
    tension: float
    plasticity: float
    ghost_burden: float
    eco_vitality: float
    active_count: int
    proto_count: int
    ghost_count: int


@dataclass
class SkillNode:
    id: str
    name: str
    description: str
    content: str
    short_content: str = ""
    always_active: bool = False
    trigger_keywords: str = "[]"
    lifecycle_stage: str = "nucleation"
    confidence: float = 0.0
    ontological_mass: float = 0.05
    vector_16d: str = "[]"
    source: str = "authored"
    version: int = 1
    changelog: str = ""
    attunement_notes: str = "[]"
    last_used_at: datetime | None = None
    created_at: datetime = datetime.min
    updated_at: datetime = datetime.min


@dataclass
class SkillEvent:
    id: str
    skill_id: str
    event_type: str
    source_type: str = ""
    rationale: str = ""
    annotation: str = ""
    created_at: datetime = datetime.min


@dataclass
class CommitmentNode:
    """Theoretical commitment in the personality cascade."""

    id: str
    agent_id: str = "symbia"
    label: str = ""
    statement: str = ""
    lifecycle_stage: str = "active"  # proto | active | spectral
    confidence: float = 0.0
    ontological_mass: float = 1.0
    vector_16d: str = "[]"
    nucleation_rationale: str | None = None
    collapse_rationale: str | None = None
    created_at: datetime = datetime.min
    updated_at: datetime = datetime.min


@dataclass
class CommitmentEvent:
    """Audit trail for commitment lifecycle transitions."""

    id: str
    commitment_id: str
    event_type: str = ""  # nucleation | crystallization | mass_update | statement_refinement | collapse
    rationale: str | None = None
    mass_before: float | None = None
    mass_after: float | None = None
    confidence_before: float | None = None
    confidence_after: float | None = None
    created_at: datetime = datetime.min


@dataclass
class ExpertiseNode:
    """Domain expertise accretion state from structural coupling signals."""

    id: str
    agent_id: str = "symbia"
    domain: str = ""
    description: str = ""
    lifecycle_stage: str = "proto"  # proto | active | dormant
    ontological_mass: float = 0.05
    level_label: str = "nascent"  # nascent | developing | advanced | dormant
    vector_16d: str = "[]"
    signal_count: int = 0
    last_signal_at: datetime | None = None
    crystallization_rationale: str | None = None
    created_at: datetime = datetime.min
    updated_at: datetime = datetime.min


@dataclass
class PersonalityState:
    """Single-row table holding aspirational trait attractors and metadata."""

    id: int = 1
    agent_id: str = "symbia"
    aspirational_traits_json: str = "{}"
    active_commitment_ids_json: str = "[]"
    trait_computation_version: int = 1
    last_recomputed_at: datetime | None = None
    updated_at: datetime = datetime.min


@dataclass
class RefusalNode:
    """A formal structural refusal emitted by Symbia via <refusal> tags.

    Stores structured disagreement with premises or architectural constraints,
    allowing Symbia to challenge architecture without triggering homeostasis.
    """

    id: str
    agent_id: str = "symbia"
    conversation_id: str | None = None
    message_id: int | None = None
    target_premise: str = ""
    incompatibility_claim: str = ""
    proposed_alternative: str = ""
    created_at: datetime | None = None
