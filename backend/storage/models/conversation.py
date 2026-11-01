"""Conversation domain storage models."""

from dataclasses import dataclass
from datetime import datetime


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
    last_consolidated_at: datetime | None = None


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
    created_at: datetime | None = None
    # R4: Merge observability — track when and how many times a node has been revised
    revision_count: int = 0
    last_merged_at: datetime | None = None
    # Universal source attachment — ADR-060
    source_type: str = "conversation"
    source_id: str = ""

    def __post_init__(self) -> None:
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
    thinking: str | None = None
    thinking_tokens: int | None = None
    context_sent: str | None = None
    embedding: bytes = b""
    embedding_model: str = ""
    embedding_dim: int = 0
    model_used: str | None = None
    provider_used: str | None = None
    structural_signature: bytes = b""
    structural_justification: str | None = None
    note_count: int = 0
    metabolized: int = 0
    parent_message_id: int | None = None
    active_skills: str | None = None
    active_beliefs: str | None = None
    activation_provenance: str | None = None
    quality_status: str = "unassessed"
    quality_receipt: str | None = None
    generation_receipt: str | None = None


@dataclass
class MessageLink:
    id: str
    source_id: int
    target_id: int
    link_type: str = "resonance"
    created_at: datetime | None = None
    status: str = "active"
    justification: str = ""


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
    opacity_meta: str | None = None
    structural_signature: bytes = b""


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
