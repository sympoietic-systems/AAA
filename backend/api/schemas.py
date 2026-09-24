from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from backend import contracts as _contracts

AttachmentInfo = _contracts.AttachmentInfo
ChatResponse = _contracts.ChatResponse
HomeostaticRecommendations = _contracts.HomeostaticRecommendations
HistoryMessage = _contracts.HistoryMessage
HistoryResponse = _contracts.HistoryResponse
MetricsInfo = _contracts.MetricsInfo
ProposedBranch = _contracts.ProposedBranch


class ChatRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=50_000)
    speaker: str = Field(default="human", max_length=100, pattern=r"^(human|apparatus|[\w-]+)$")
    conversation_id: str = Field(
        default="", max_length=100, pattern=r"^$|^[\w-]+$", description="Conversation ID; auto-created if empty"
    )
    attachments: list[AttachmentInfo] | None = Field(default=None, max_length=100)
    include_structural_scoring: bool | None = None
    max_tokens: int | None = Field(default=None, ge=1, le=131_072, description="Override max_tokens for this request")
    parent_message_id: int | None = Field(
        default=None, ge=1, description="Parent message ID for conversation branching"
    )
    agent_id: str | None = Field(
        default=None, max_length=100, pattern=r"^[\w-]+$", description="Optional calling agent name"
    )


class GenerateRequest(BaseModel):
    conversation_id: str = Field(..., min_length=1, max_length=100, pattern=r"^[\w-]+$")
    user_message_id: int = Field(..., ge=1)
    max_tokens: int | None = Field(default=None, ge=1, le=131_072, description="Override max_tokens for this request")
    include_structural_scoring: bool | None = None


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
    triggers: list[str] = Field(default_factory=list)
    cost: str = "free"
    status: bool = True
    children: list["SkillInfo"] = Field(default_factory=list)


class SkillsResponse(BaseModel):
    pipeline: list[SkillInfo]
    on_demand: list[SkillInfo]


class DbSkillInfo(BaseModel):
    id: str
    name: str
    description: str
    content: str = ""
    always_active: bool = False
    trigger_keywords: list[str] = Field(default_factory=list)
    lifecycle_stage: str = "nucleation"
    confidence: float = 0.0
    ontological_mass: float = 0.05
    vector_16d: list[float] = Field(default_factory=list)
    source: str = "authored"
    version: int = 1
    changelog: str = ""
    last_used_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    refusal_reason: str | None = None


class DbSkillsResponse(BaseModel):
    always_active: list[DbSkillInfo]
    on_demand: list[DbSkillInfo]
    collapsed: list[DbSkillInfo] = Field(default_factory=list)
    proposed: list[DbSkillInfo] = Field(default_factory=list)
    all: list[DbSkillInfo]


class SkillUpdateRequest(BaseModel):
    description: str | None = None
    content: str | None = None
    trigger_keywords: list[str] | None = None


class SkillCreateRequest(BaseModel):
    name: str
    description: str
    content: str | None = None
    always_active: bool = False
    trigger_keywords: list[str] = Field(default_factory=list)


class WorkshopActionRequest(BaseModel):
    name: str = ""
    description: str = ""
    content: str = ""
    skill_id: str = ""
    always_active: bool = False
    trigger_keywords: list[str] = Field(default_factory=list)
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
    anti_mastery_assessment: dict = Field(default_factory=dict)
    skills: list[dict] = Field(default_factory=list)
    count: int = 0
    skill: dict | None = None
    events: list[dict] = Field(default_factory=list)


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
    similarity_range_memory: list[float] = Field(default_factory=list)
    similarity_range_files: list[float] = Field(default_factory=list)
    candidates_searched: int = 0
    items_injected: int = 0
    tokens_used: int = 0
    token_budget: int = 0
    duration_ms: float = 0.0
    sources: list[DiffractiveSourceInfo] = Field(default_factory=list)


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
    tendril_ids: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class MemoryNodeListResponse(BaseModel):
    nodes: list[MemoryNodeInfo]


class ConversationInfo(BaseModel):
    id: str
    title: str
    agent_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    message_count: int = 0
    tags: list[ConversationTagInfo] = Field(default_factory=list)
    summary: str | None = None
    human_summary: str | None = None


class ConversationListResponse(BaseModel):
    conversations: list[ConversationInfo]
    total_count: int = 0
    has_more: bool = False


class ConversationUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


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
    action: str = Field(..., min_length=1, max_length=100)
    conversation_id: str | None = Field(default=None, max_length=100, pattern=r"^[\w-]+$")
    text: str | None = Field(default=None, max_length=50_000)
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
    summary: str | None = None
    summary_model: str | None = None
    token_count: int = 0
    chunk_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConversationFilesResponse(BaseModel):
    conversation_id: str
    files: list[ConversationFile]


class NoteCreateRequest(BaseModel):
    asset_type: str = Field(default="conversation_message", max_length=100)
    asset_id: str = Field(default="", max_length=100)
    conversation_id: str | None = Field(default=None, max_length=100)
    selected_text: str = Field(..., min_length=1, max_length=50_000)
    comment: str = Field(default="", max_length=50_000)
    visibility: Literal["personal", "shared", "agent"] = "personal"
    start_offset: int | None = None
    message_id: int | None = None


class NoteResponse(BaseModel):
    id: str
    asset_type: str
    asset_id: str
    conversation_id: str | None = None
    selected_text: str
    comment: str
    visibility: str
    created_at: str
    updated_at: str


class NoteUpdateRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=50_000)
    visibility: Literal["personal", "shared", "agent"] | None = None


class UnifiedNoteResponse(NoteResponse):
    step_number: int | None = None
    step_type: str | None = None


class SedimentFileInfo(BaseModel):
    conversation_id: str
    conversation_title: str = ""
    file_name: str
    file_type: str
    summary: str | None = None
    token_count: int = 0
    chunk_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None
    display_name: str | None = None


class SedimentFilesResponse(BaseModel):
    files: list[SedimentFileInfo]


class SedimentInjectRequest(BaseModel):
    files: list[dict] = Field(..., max_length=100)  # Each: { "source_conversation_id": str, "source_file_name": str }


class SedimentInjectionInfo(BaseModel):
    id: str
    source_conversation_id: str
    source_file_name: str
    source_conversation_title: str = ""
    file_type: str = ""
    token_count: int = 0
    chunk_count: int = 0
    summary: str | None = None
    injected_at: str | None = None
    status: str = "ready"
    display_name: str | None = None


class SedimentInjectionsResponse(BaseModel):
    injections: list[SedimentInjectionInfo]
    conversation_id: str | None = None


class TagCreateRequest(BaseModel):
    tag: str = Field(..., min_length=1, max_length=100)


class CommitBranchRequest(BaseModel):
    parent_message_id: int = Field(..., ge=1)
    content: str = Field(..., min_length=1, max_length=50_000)
    speaker: str = Field(default="apparatus", max_length=100)


class TreeNode(BaseModel):
    id: int
    speaker: str
    content: str
    parent_message_id: int | None = None
    timestamp: datetime


class TreeLink(BaseModel):
    id: str
    source_id: int
    target_id: int
    link_type: str
    status: str = "active"
    justification: str | None = ""


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
    justification: str | None = ""
