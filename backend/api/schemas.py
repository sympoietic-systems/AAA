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
    max_tokens: Optional[int] = Field(default=None, description="Override max_tokens for this request")
    parent_message_id: Optional[int] = Field(default=None, description="Parent message ID for conversation branching")


class GenerateRequest(BaseModel):
    conversation_id: str
    user_message_id: int
    max_tokens: Optional[int] = Field(default=None, description="Override max_tokens for this request")
    include_structural_scoring: Optional[bool] = None



class ProposedBranch(BaseModel):
    title: str
    content: str


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
    truncated: Optional[bool] = Field(default=None, description="Whether response was truncated by token limit")
    finish_reason: Optional[str] = Field(default=None, description="LLM finish reason (stop, length, max_tokens)")
    active_skills: list[str] = Field(default_factory=list, description="Skill names active for this response")
    active_beliefs: list[str] = Field(default_factory=list, description="Belief labels in the attractor window for this response")
    parent_message_id: Optional[int] = None
    proposed_branches: Optional[list[ProposedBranch]] = None


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
    parent_message_id: Optional[int] = None


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
    agent_flux: bool = False


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


class DbSkillInfo(BaseModel):
    id: str
    name: str
    description: str
    always_active: bool = False
    trigger_keywords: list[str] = []
    lifecycle_stage: str = "nucleation"
    confidence: float = 0.0
    ontological_mass: float = 0.05
    vector_16d: list[float] = []
    source: str = "authored"
    version: int = 1
    changelog: str = ""
    last_used_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    refusal_reason: Optional[str] = None


class DbSkillsResponse(BaseModel):
    always_active: list[DbSkillInfo]
    on_demand: list[DbSkillInfo]
    collapsed: list[DbSkillInfo] = []
    proposed: list[DbSkillInfo] = []
    all: list[DbSkillInfo]


class SkillUpdateRequest(BaseModel):
    description: Optional[str] = None
    content: Optional[str] = None
    trigger_keywords: Optional[list[str]] = None


class SkillCreateRequest(BaseModel):
    name: str
    description: str
    content: Optional[str] = None
    always_active: bool = False
    trigger_keywords: list[str] = []


class WorkshopActionRequest(BaseModel):
    name: str = ""
    description: str = ""
    content: str = ""
    skill_id: str = ""
    always_active: bool = False
    trigger_keywords: list[str] = []
    changelog: str = ""
    reason: str = ""
    human_approved: bool = False
    stage: str = ""


class WorkshopResponse(BaseModel):
    status: str
    message: str = ""
    skill_id: str = ""
    name: str = ""
    content: str = ""
    description: str = ""
    confidence: float = 0.0
    approval_tier: str = ""
    lifecycle_stage: str = ""
    version: int = 0
    anti_mastery_assessment: dict = {}
    skills: list[dict] = []
    count: int = 0
    skill: Optional[dict] = None
    events: list[dict] = []


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



class ConversationTagInfo(BaseModel):
    tag: str
    tag_type: str


class MemoryNodeInfo(BaseModel):
    id: str
    node_type: str
    intensity: float
    scar: str = ""
    glitch_potential: float = 0.0
    intra_active_text: str
    surface_fragment: str = ""
    agential_symmetry: str = "negotiated"
    diffractive_key: str = ""
    tendril_ids: list[str] = []
    created_at: Optional[datetime] = None


class MemoryNodeListResponse(BaseModel):
    nodes: list[MemoryNodeInfo]


class ConversationInfo(BaseModel):
    id: str
    title: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    message_count: int = 0
    tags: list[ConversationTagInfo] = []
    summary: Optional[str] = None
    human_summary: Optional[str] = None


class ConversationListResponse(BaseModel):
    conversations: list[ConversationInfo]
    total_count: int = 0
    has_more: bool = False


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
    display_name: Optional[str] = None


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
    status: str = "ready"


class SedimentInjectionsResponse(BaseModel):
    injections: list[SedimentInjectionInfo]


class TagCreateRequest(BaseModel):
    tag: str


class CommitBranchRequest(BaseModel):
    parent_message_id: int
    content: str
    speaker: str = "apparatus"


class TreeNode(BaseModel):
    id: int
    speaker: str
    content: str
    parent_message_id: Optional[int] = None
    timestamp: datetime


class TreeLink(BaseModel):
    id: str
    source_id: int
    target_id: int
    link_type: str
    status: str = "active"
    justification: Optional[str] = ""


class ConversationTreeResponse(BaseModel):
    nodes: list[TreeNode]
    links: list[TreeLink]


class SpectralSuggestion(BaseModel):
    message_id: int
    speaker: str
    content: str
    similarity: float
    timestamp: datetime


class CommitLinkRequest(BaseModel):
    source_id: int
    target_id: int
    link_type: str = "resonance"
    status: str = "active"
    justification: Optional[str] = ""
