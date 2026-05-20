from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    content: str
    speaker: str = Field(default="human", pattern="^(human|apparatus)$")


class ChatResponse(BaseModel):
    id: int | None = None
    timestamp: datetime | None = None
    speaker: str
    content: str
    thinking: Optional[str] = None
    embedding_generated: bool = False
    error: str | None = None
    metrics: Optional["MetricsInfo"] = None
    homeostatic_recommendations: Optional["HomeostaticRecommendations"] = None


class HistoryMessage(BaseModel):
    id: int
    timestamp: datetime
    speaker: str
    content: str
    thinking: Optional[str] = None


class HistoryResponse(BaseModel):
    messages: list[HistoryMessage]
    count: int


class HealthResponse(BaseModel):
    status: str
    modules: dict[str, bool]


class ErrorResponse(BaseModel):
    status: str = "error"
    message: str


class AgentInfo(BaseModel):
    name: str
    version: str = ""


class SkillInfo(BaseModel):
    name: str
    description: str
    category: str
    always_run: bool
    triggers: list[str] = []
    cost: str = "free"
    status: bool = True


class SkillsResponse(BaseModel):
    pipeline: list[SkillInfo]
    on_demand: list[SkillInfo]


class MetricsInfo(BaseModel):
    pairwise_similarity: float | None = None
    conceptual_novelty: float | None = None
    rolling_entropy: float | None = None
    coupling_coherence: float | None = None
    agent_self_divergence: float | None = None
    homeostatic_deficit: float | None = None


class HomeostaticRecommendations(BaseModel):
    temperature: dict | None = None
    presence_penalty: dict | None = None
    frequency_penalty: dict | None = None
    state: str = "healthy"
    triggered_flags: list[str] = []


class MetricsResponse(BaseModel):
    window_size: int
    aggregates: dict
    latest: MetricsInfo | None = None
    recommendations: HomeostaticRecommendations | None = None
