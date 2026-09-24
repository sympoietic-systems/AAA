"""Framework-neutral data contracts shared by API and service layers."""

from datetime import datetime

from pydantic import BaseModel, Field


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
    phase_shifts: list[dict[str, object]] | None = None


class HomeostaticRecommendations(BaseModel):
    temperature: dict[str, object] | None = None
    presence_penalty: dict[str, object] | None = None
    frequency_penalty: dict[str, object] | None = None
    state: str = "healthy"
    triggered_flags: list[str] = Field(default_factory=list)


class AttachmentInfo(BaseModel):
    file_name: str
    file_type: str
    token_count: int = 0
    preview: str | None = None


class ProposedBranch(BaseModel):
    title: str
    content: str


class ChatResponse(BaseModel):
    id: int | None = None
    timestamp: datetime | None = None
    conversation_id: str = ""
    speaker: str
    content: str
    thinking: str | None = None
    content_tokens: int = 0
    thinking_tokens: int | None = None
    embedding_generated: bool = False
    error: str | None = None
    metrics: MetricsInfo | None = None
    homeostatic_recommendations: HomeostaticRecommendations | None = None
    attachments: list[AttachmentInfo] | None = None
    context_sent: str | None = None
    model_used: str | None = None
    provider_used: str | None = None
    structural_justification: str | None = None
    user_message_id: int | None = None
    user_structural_signature: list[float] | None = None
    user_structural_justification: str | None = None
    truncated: bool | None = Field(default=None, description="Whether response was truncated by token limit")
    finish_reason: str | None = Field(default=None, description="LLM finish reason (stop, length, max_tokens)")
    active_skills: list[str] = Field(default_factory=list, description="Skill names active for this response")
    active_beliefs: list[str] = Field(
        default_factory=list, description="Belief labels in the attractor window for this response"
    )
    parent_message_id: int | None = None
    proposed_branches: list[ProposedBranch] | None = None
