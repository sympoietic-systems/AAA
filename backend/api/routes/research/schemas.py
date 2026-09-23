"""Pydantic schemas and payload membranes for the Autonomous Research Engine."""

from pydantic import BaseModel, Field


class InjectedDocSpec(BaseModel):
    file_id: str = Field(..., max_length=150)
    conversation_id: str | None = Field(default=None, max_length=100)
    document_mode: str = Field(default="chunks", max_length=50)
    document_chunk_limit: int = Field(default=5, ge=1, le=50)


class DispatchPayload(BaseModel):
    objective: str = Field(..., min_length=1, max_length=5000)
    title: str | None = Field(default=None, max_length=300)
    conversation_id: str | None = Field(default=None, max_length=100)
    max_depth: int = Field(default=3, ge=1, le=10)
    max_breadth: int = Field(default=4, ge=1, le=10)
    is_agonistic: bool = False
    budget_limit_usd: float = Field(default=0.50, ge=0.0, le=50.0)
    previous_context: str | None = Field(default=None, max_length=50_000)
    continue_from_task_id: str | None = Field(default=None, max_length=100)
    additional_cycles: int | None = Field(default=None, ge=1, le=10)
    inject_file_id: str | None = Field(default=None, max_length=150)
    inject_conversation_id: str | None = Field(default=None, max_length=100)
    document_mode: str | None = Field(default=None, max_length=50)
    document_chunk_limit: int | None = Field(default=None, ge=1, le=50)
    injected_documents: list[InjectedDocSpec] | None = None


class ContinuePayload(BaseModel):
    source_task_id: str = Field(..., max_length=100)
    adjusted_objective: str | None = Field(default=None, max_length=5000)
    title: str | None = Field(default=None, max_length=300)
    conversation_id: str | None = Field(default=None, max_length=100)
    additional_cycles: int = Field(default=1, ge=1, le=10)
    inject_file_id: str | None = Field(default=None, max_length=150)
    inject_conversation_id: str | None = Field(default=None, max_length=100)
    document_mode: str | None = Field(default=None, max_length=50)
    document_chunk_limit: int | None = Field(default=None, ge=1, le=50)
    injected_documents: list[InjectedDocSpec] | None = None
    budget_limit_usd: float | None = Field(default=None, ge=0.0, le=50.0)
    max_breadth: int | None = Field(default=None, ge=1, le=10)
    is_agonistic: bool | None = None


class ContinueTaskPayload(BaseModel):
    adjusted_objective: str | None = Field(default=None, max_length=5000)
    additional_cycles: int = Field(default=1, ge=1, le=10)
    inject_file_id: str | None = Field(default=None, max_length=150)
    inject_conversation_id: str | None = Field(default=None, max_length=100)
    document_mode: str | None = Field(default=None, max_length=50)
    document_chunk_limit: int | None = Field(default=None, ge=1, le=50)
    budget_limit_usd: float | None = Field(default=None, ge=0.0, le=50.0)


class ApproveProposalPayload(BaseModel):
    objective: str | None = Field(default=None, max_length=5000)
    title: str | None = Field(default=None, max_length=300)
    conversation_id: str | None = Field(default=None, max_length=100)
    max_depth: int = Field(default=2, ge=1, le=10)
    max_breadth: int = Field(default=3, ge=1, le=10)
    is_agonistic: bool = False
    rationale: str | None = Field(default=None, max_length=2000)


class MemoryNodeResponse(BaseModel):
    id: str
    node_type: str
    intensity: float
    scar: str
    intra_active_text: str
    surface_fragment: str = ""
    diffractive_key: str = ""
    agential_symmetry: str = ""
    source_type: str = "conversation"
    source_id: str = ""
    created_at: str | None = None


class MemoryNodesResponse(BaseModel):
    task_id: str
    nodes: list[MemoryNodeResponse]
    count: int


class KnotResponse(BaseModel):
    id: str
    weight: float
    concept_payload: str
    token_count: int
    created_at: str | None = None


class KnotsResponse(BaseModel):
    task_id: str
    knots: list[KnotResponse]
    count: int
