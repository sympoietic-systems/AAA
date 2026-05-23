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


@dataclass
class ErrorLogEntry:
    id: int | None
    timestamp: datetime
    module: str
    error_type: str
    error_message: str
    traceback: Optional[str]
    context: Optional[str]
