from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AttachmentInfo(BaseModel):
    file_name: str
    file_type: str
    token_count: int = 0
    preview: str | None = None


class ChatRequest(BaseModel):
    content: str
    speaker: str = Field(default="human", pattern="^(human|apparatus)$")
    conversation_id: str = Field(default="", description="Conversation ID; auto-created if empty")
    attachments: list[AttachmentInfo] | None = None


class ChatResponse(BaseModel):
    id: int | None = None
    timestamp: datetime | None = None
    conversation_id: str = ""
    speaker: str
    content: str
    thinking: Optional[str] = None
    content_tokens: int = 0
    thinking_tokens: Optional[int] = None
    embedding_generated: bool = False
    error: str | None = None
    metrics: Optional["MetricsInfo"] = None
    homeostatic_recommendations: Optional["HomeostaticRecommendations"] = None
    attachments: list[AttachmentInfo] | None = None
    context_sent: str | None = None
    model_used: Optional[str] = None
    provider_used: Optional[str] = None


class HistoryMessage(BaseModel):
    id: int
    timestamp: datetime
    speaker: str
    content: str
    thinking: Optional[str] = None
    content_tokens: int = 0
    thinking_tokens: Optional[int] = None
    metrics: Optional["MetricsInfo"] = None
    model_used: Optional[str] = None
    provider_used: Optional[str] = None


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
    children: list["SkillInfo"] = []


class SkillsResponse(BaseModel):
    pipeline: list[SkillInfo]
    on_demand: list[SkillInfo]


class MetricsInfo(BaseModel):
    pairwise_similarity: float | None = None
    conceptual_novelty: float | None = None
    rolling_entropy: float | None = None
    coupling_coherence: float | None = None
    agent_self_divergence: float | None = None
    reverse_perturbation: float | None = None
    surprise_index: float | None = None
    mutual_perturbation: float | None = None
    homeostatic_deficit: float | None = None
    conversation_vitality: float | None = None
    boringness: float | None = None
    conceptual_velocity: float | None = None
    divergence_resolution_ratio: float | None = None
    paskian_health: float | None = None
    phase_shifts: list[dict] | None = None


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


class ConversationInfo(BaseModel):
    id: str
    title: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    message_count: int = 0


class ConversationListResponse(BaseModel):
    conversations: list[ConversationInfo]


class ConversationUpdateRequest(BaseModel):
    title: str


class ConversationTokenInfo(BaseModel):
    conversation_id: str
    title: str = ""
    user_tokens: int = 0
    agent_tokens: int = 0
    thinking_tokens: int = 0
    total_tokens: int = 0


class TokenResponse(BaseModel):
    conversations: list[ConversationTokenInfo]
    system_prompt_tokens: int = 0
    grand_total_tokens: int = 0


class BackgroundTaskRequest(BaseModel):
    action: str
    conversation_id: str | None = None
    text: str | None = None
    context: dict | None = None
    use_vision: bool = False


class BackgroundTaskResponse(BaseModel):
    action: str
    result: str
    model_used: str
    error: str | None = None
