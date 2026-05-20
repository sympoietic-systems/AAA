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
