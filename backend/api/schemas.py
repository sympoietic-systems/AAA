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
    include_structural_scoring: Optional[bool] = None


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
    structural_justification: Optional[str] = None
    user_message_id: Optional[int] = None
    user_structural_signature: Optional[list[float]] = None
    user_structural_justification: Optional[str] = None


class HistoryMessage(BaseModel):
    id: int
    timestamp: datetime
    speaker: str
    content: str
    thinking: Optional[str] = None
    context_sent: Optional[str] = None
    has_context: Optional[bool] = None
    content_tokens: int = 0
    thinking_tokens: Optional[int] = None
    metrics: Optional["MetricsInfo"] = None
    model_used: Optional[str] = None
    provider_used: Optional[str] = None
    structural_signature: Optional[list[float]] = None
    structural_justification: Optional[str] = None


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
    diffractive: Optional["DiffractiveInfo"] = None


class DiffractiveSourceInfo(BaseModel):
    type: str
    source_title: str
    similarity: float


class DiffractiveInfo(BaseModel):
    state: str = "FLOWING"
    previous_state: str = "FLOWING"
    p_diffract: float = 0.0
    stagnation_index: float = 0.0
    r_context: float = 0.0
    dynamic_max: int = 0
    cohesion_timer: int = 0
    similarity_range_memory: list[float] = []
    similarity_range_files: list[float] = []
    candidates_searched: int = 0
    items_injected: int = 0
    tokens_used: int = 0
    token_budget: int = 0
    duration_ms: float = 0.0
    sources: list[DiffractiveSourceInfo] = []



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


class ConversationFile(BaseModel):
    file_name: str
    file_type: str
    status: str
    summary: Optional[str] = None
    summary_model: Optional[str] = None
    token_count: int = 0
    chunk_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConversationFilesResponse(BaseModel):
    conversation_id: str
    files: list[ConversationFile]


class NoteCreateRequest(BaseModel):
    message_id: int
    selected_text: str
    comment: str = ""
    visibility: str = "personal"
    start_offset: Optional[int] = None


class NoteResponse(BaseModel):
    id: str
    conversation_id: str
    message_id: int
    selected_text: str
    comment: str
    visibility: str
    created_at: str
    updated_at: str


class NoteUpdateRequest(BaseModel):
    comment: Optional[str] = None
    visibility: Optional[str] = None


class SedimentFileInfo(BaseModel):
    conversation_id: str
    conversation_title: str = ""
    file_name: str
    file_type: str
    summary: Optional[str] = None
    token_count: int = 0
    chunk_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SedimentFilesResponse(BaseModel):
    files: list[SedimentFileInfo]


class SedimentInjectRequest(BaseModel):
    files: list[dict]  # Each: { "source_conversation_id": str, "source_file_name": str }


class SedimentInjectionInfo(BaseModel):
    id: str
    source_conversation_id: str
    source_file_name: str
    source_conversation_title: str = ""
    file_type: str = ""
    token_count: int = 0
    chunk_count: int = 0
    summary: Optional[str] = None
    injected_at: Optional[str] = None


class SedimentInjectionsResponse(BaseModel):
    injections: list[SedimentInjectionInfo]
