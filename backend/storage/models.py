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
class ErrorLogEntry:
    id: int | None
    timestamp: datetime
    module: str
    error_type: str
    error_message: str
    traceback: Optional[str]
    context: Optional[str]
