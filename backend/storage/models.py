from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Conversation:
    id: str
    title: str
    agent_id: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    somatic_reservoir_ad: float = 0.0
    matrix_warping: float = 0.0
    immunological_directive_active: int = 0
    requires_consolidation: int = 0
    last_consolidated_at: Optional[datetime] = None


@dataclass
class Message:
    id: int | None
    timestamp: datetime
    agent_id: str
    conversation_id: str
    speaker: str
    content: str
    content_tokens: int = 0
    thinking: Optional[str] = None
    thinking_tokens: Optional[int] = None
    context_sent: Optional[str] = None
    embedding: bytes = b""
    embedding_model: str = ""
    embedding_dim: int = 0
    model_used: Optional[str] = None
    provider_used: Optional[str] = None
    structural_signature: bytes = b""
    structural_justification: Optional[str] = None
    note_count: int = 0


@dataclass
class MetricsRecord:
    message_id: int
    s_t: float
    novelty: float
    rolling_entropy: float | None
    coupling: float | None
    agent_divergence: float | None
    deficit: float
    reverse_perturbation: float | None
    surprise_index: float | None
    mutual_perturbation: float | None
    vitality: float | None
    phase_shifts: str | None
    boringness: float | None
    conceptual_velocity: float | None
    divergence_resolution_ratio: float | None
    paskian_health: float | None
    temperature_rec: float | None
    presence_penalty_rec: float | None
    frequency_penalty_rec: float | None
    homeostatic_state: str | None


@dataclass
class PerceptionSediment:
    id: int | None
    conversation_id: str
    file_name: str
    file_type: str
    chunk_index: int
    chunk_text: str
    embedding: bytes
    embedding_model: str
    token_count: int
    created_at: datetime | None = None
    opacity: int = 0
    opacity_meta: Optional[str] = None
    structural_signature: bytes = b""


@dataclass
class ErrorLogEntry:
    id: int | None
    timestamp: datetime
    module: str
    error_type: str
    error_message: str
    traceback: Optional[str]
    context: Optional[str]


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
    last_reinforced_at: Optional[datetime] = None
    created_at: datetime = datetime.min
    updated_at: datetime = datetime.min


@dataclass
class BeliefEvent:
    id: str
    timestamp: datetime
    belief_id: str
    source_type: str
    source_id: Optional[str]
    alignment_coefficient: Optional[float]
    perturbation_magnitude: Optional[float]
    event_type: str
    impact_score: float
    rationale: Optional[str]


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
class SemanticKnot:
    id: str
    conversation_id: str
    created_at: datetime
    weight: float
    concept_payload: str
    embedding: bytes
    embedding_model: str
    token_count: int
    structural_signature: bytes = b""
