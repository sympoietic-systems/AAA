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
class MemoryNode:
    id: str
    conversation_id: str
    checkpoint_id: int
    node_type: str = "concept"
    intensity: float = 0.5
    scar: str = ""
    glitch_potential: float = 0.0
    intra_active_text: str = ""
    surface_fragment: str = ""
    agential_symmetry: str = "negotiated"
    diffractive_key: str = ""
    tendril_ids: list[str] | None = None
    created_at: Optional[datetime] = None
    # R4: Merge observability — track when and how many times a node has been revised
    revision_count: int = 0
    last_merged_at: Optional[datetime] = None

    def __post_init__(self):
        if self.tendril_ids is None:
            self.tendril_ids = []


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
    metabolized: int = 0
    parent_message_id: Optional[int] = None


@dataclass
class MessageLink:
    id: str
    source_id: int
    target_id: int
    link_type: str = "resonance"
    created_at: Optional[datetime] = None
    status: str = "active"
    justification: str = ""


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
    evolved_from_proposal: Optional[str] = None
    genesis_materials: Optional[str] = None  # JSON list
    version: int = 1
    last_reinforced_at: Optional[datetime] = None
    last_dreamed_at: Optional[datetime] = None
    created_at: datetime = datetime.min
    updated_at: datetime = datetime.min
    # 13C: Ghost merging persistence — track which belief absorbed this one
    merged_from: Optional[str] = None  # JSON list of absorbed ghost IDs
    merged_into: Optional[str] = None  # ID of the keeper belief that absorbed this ghost


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
    suggested_label: Optional[str] = None
    suggested_statement: Optional[str] = None
    potential_merge_target: Optional[str] = None
    symbia_reflection: Optional[str] = None
    symbia_friction_rationale: Optional[str] = None
    rejection_rationale: Optional[str] = None
    created_at: datetime = datetime.min
    updated_at: datetime = datetime.min


@dataclass
class BeliefStatementVersion:
    id: str
    belief_id: str
    version: int
    statement: str
    vector_16d: str  # JSON string representation of 16D vector
    change_reason: Optional[str] = None
    created_at: datetime = datetime.min


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
    last_used_at: Optional[datetime] = None
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
    lifecycle_stage: str = "active"   # proto | active | spectral
    confidence: float = 0.0
    ontological_mass: float = 1.0
    vector_16d: str = "[]"
    nucleation_rationale: Optional[str] = None
    collapse_rationale: Optional[str] = None
    created_at: datetime = datetime.min
    updated_at: datetime = datetime.min


@dataclass
class CommitmentEvent:
    """Audit trail for commitment lifecycle transitions."""
    id: str
    commitment_id: str
    event_type: str = ""  # nucleation | crystallization | mass_update | statement_refinement | collapse
    rationale: Optional[str] = None
    mass_before: Optional[float] = None
    mass_after: Optional[float] = None
    confidence_before: Optional[float] = None
    confidence_after: Optional[float] = None
    created_at: datetime = datetime.min


@dataclass
class ExpertiseNode:
    """Domain expertise accretion state from structural coupling signals."""
    id: str
    agent_id: str = "symbia"
    domain: str = ""
    description: str = ""
    lifecycle_stage: str = "proto"     # proto | active | dormant
    ontological_mass: float = 0.05
    level_label: str = "nascent"       # nascent | developing | advanced | dormant
    vector_16d: str = "[]"
    signal_count: int = 0
    last_signal_at: Optional[datetime] = None
    crystallization_rationale: Optional[str] = None
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
    last_recomputed_at: Optional[datetime] = None
    updated_at: datetime = datetime.min


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


@dataclass
class CompressedMessageBlock:
    """R5: LLM-compressed batch of messages that exited the floating window."""
    id: int | None = None
    conversation_id: str = ""
    first_message_id: int = 0
    last_message_id: int = 0
    compressed_block: str = ""
    created_at: datetime | None = None


@dataclass
class ResearchTask:
    """Autonomous deep web research task (Somatic Research Engine)."""
    id: str
    title: str
    objective: str
    trigger_source: str
    status: str = "proposed"
    conversation_id: Optional[str] = None
    priority: int = 2
    max_depth: int = 3
    max_breadth: int = 4
    is_agonistic: bool = False
    budget_limit_usd: float = 0.50
    budget_spent_usd: float = 0.0
    branches_created: int = 0
    assets_harvested: int = 0
    lateral_flights: int = 0
    bifurcation_triggered: bool = False
    result_summary: Optional[str] = None
    proposal_rationale: Optional[str] = None
    proposal_message_id: Optional[int] = None
    approved_by: Optional[str] = None
    proposed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class ResearchBranch:
    """A node in the recursive research tree traversal."""
    id: str
    task_id: str
    conversation_id: str
    query: str
    goal: str
    depth: int
    breadth: int
    status: str = "probing"
    parent_branch_id: Optional[str] = None
    vector_16d: Optional[bytes] = None
    homeostatic_tension: float = 0.0
    created_at: Optional[datetime] = None


@dataclass
class ScrapedAsset:
    """Raw markdown content harvested by sensory affordances."""
    id: str
    branch_id: str
    task_id: str
    url: str
    raw_markdown: str
    memory_node_id: Optional[str] = None
    relevance_score: float = 0.0
    novelty_score: float = 0.0
    diffractive_score: float = 0.0
    created_at: Optional[datetime] = None
