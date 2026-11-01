"""Research domain storage dataclasses."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ResearchTask:
    """Autonomous deep web research task (Somatic Research Engine)."""

    id: str
    title: str
    objective: str
    trigger_source: str
    status: str = "proposed"
    conversation_id: str | None = None
    priority: int = 2
    max_depth: int = 3
    max_breadth: int = 4
    is_agonistic: bool = False
    budget_limit_usd: float = 0.50
    budget_spent_usd: float = 0.0
    branches_created: int = 0
    assets_harvested: int = 0
    lateral_flights: int = 0
    bifurcation_triggered: bool = False
    result_summary: str | None = None
    proposal_rationale: str | None = None
    proposal_message_id: int | None = None
    approved_by: str | None = None
    proposed_at: datetime | None = None
    approved_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class ResearchBranch:
    """A node in the recursive research tree traversal."""

    id: str
    task_id: str
    conversation_id: str
    query: str
    goal: str
    depth: int
    breadth: int
    status: str = "probing"
    parent_branch_id: str | None = None
    vector_16d: bytes | None = None
    homeostatic_tension: float = 0.0
    created_at: datetime | None = None


@dataclass
class ScrapedAsset:
    """Raw markdown content harvested by sensory affordances."""

    id: str
    branch_id: str
    task_id: str
    url: str
    raw_markdown: str
    memory_node_id: str | None = None
    relevance_score: float = 0.0
    novelty_score: float = 0.0
    diffractive_score: float = 0.0
    created_at: datetime | None = None
