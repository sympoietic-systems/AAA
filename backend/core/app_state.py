from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from backend.metabolisation.pipeline import ProcessingPipeline
    from backend.pipeline.registry import PipelineRegistry


@dataclass
class AppState:
    config: dict = field(default_factory=dict)
    agent_name: str = "symbia"
    system_prompt_tokens: int = 0
    pipeline_order: list[str] = field(default_factory=list)
    latest_diffractive_meta: Optional[dict] = None

    # Repositories
    message_repo: Any = None
    error_repo: Any = None
    metrics_repo: Any = None
    conversation_repo: Any = None
    perception_repo: Any = None
    checkpoint_repo: Any = None
    memory_node_repo: Any = None
    belief_repo: Any = None
    semantic_knot_repo: Any = None
    note_repo: Any = None

    # Core services
    pipeline: Optional[Any] = None  # ProcessingPipeline
    registry: Optional[Any] = None  # PipelineRegistry
    embedder: Any = None
    perception_module: Any = None
    metrics_module: Any = None
    belief_metabolism: Any = None

    # Background services
    background_engine: Any = None
    background_provider: Any = None
    startup_scheduler: Any = None
    dream_daemon: Any = None

    # Research engine
    research_task_manager: Any = None
    research_task_repo: Any = None
    research_branch_repo: Any = None
    scraped_asset_repo: Any = None

    # LLM providers
    llm_provider: Any = None
    structural_provider: Any = None
    vision_provider: Any = None
