from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Message:
    id: int | None
    timestamp: datetime
    agent_id: str
    speaker: str
    content: str
    thinking: Optional[str]
    embedding: bytes
    embedding_model: str
    embedding_dim: int


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
    temperature_rec: float | None
    presence_penalty_rec: float | None
    frequency_penalty_rec: float | None
    homeostatic_state: str | None


@dataclass
class ErrorLogEntry:
    id: int | None
    timestamp: datetime
    module: str
    error_type: str
    error_message: str
    traceback: Optional[str]
    context: Optional[str]
