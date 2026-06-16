"""Application lifecycle (lifespan) and FastAPI app factory.

Extracted from backend/main.py.
Orchestrates the full startup sequence: config → DB → embedder → LLM →
modules → beliefs → skills → pipeline → background → services.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.router import router as api_router
from backend.bootstrap.providers import _init_providers
from backend.bootstrap.repositories import _init_repos
from backend.bootstrap.embedder import _init_embedder
from backend.bootstrap.modules import (
    _init_belief_engine,
    _init_modules,
    _load_identity,
)
from backend.bootstrap.pipeline import _build_pipeline, _register_skills
from backend.bootstrap.background import (
    _init_background_engine,
    _start_background_services,
)
from backend.config import load_config
from backend.modules.llm_client import LLMClientModule
from backend.pipeline.registry import PipelineRegistry
from backend.personality.assembler import PromptAssemblerModule, _build_system_content
from backend.utils.token_counter import estimate_tokens

logger = logging.getLogger(__name__)


class _ColorFormatter(logging.Formatter):
    """ANSI color-coded log formatter: red for ERROR, yellow for WARNING, reset for others."""
    _COLORS = {
        "ERROR":    "\033[31;1m",   # bold red
        "WARNING":  "\033[33;1m",   # bold yellow
        "CRITICAL": "\033[41;97m",  # white on red background
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self._COLORS.get(record.levelname, "")
        if color:
            record.levelname = f"{color}{record.levelname}{self._RESET}"
            record.msg = f"{color}{record.msg}{self._RESET}"
        return super().format(record)


_handler = logging.StreamHandler()
_handler.setFormatter(_ColorFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[_handler])


# ── App lifecycle ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: wire all modules, services, and background tasks."""
    config = load_config()

    # 1. Database + repos
    repos = _init_repos(config)

    # 1b. Load identity (for agent name + assembler)
    identity_data, agent_name, identity_path = _load_identity(config)

    # 2. Embedder
    embedder = _init_embedder(config)

    # 3. LLM providers
    llm_provider, structural_provider, vision_provider = _init_providers(config)
    llm_module = LLMClientModule(llm_provider)

    # 4. Processing modules
    modules = _init_modules(config, repos, embedder, structural_provider, vision_provider)

    # 5. Beliefs
    belief_metabolism = _init_belief_engine(repos, identity_path, structural_provider)

    # 6. Prompt assembler
    ctx_cfg = config.get("context", {})
    registry = PipelineRegistry()
    prompt_assembler = PromptAssemblerModule(
        identity_path=identity_path,
        skill_registry=registry,
        max_context_tokens=ctx_cfg.get("max_tokens", 16384),
        commitment_repo=repos["commitment_repo"],
        expertise_repo=repos["expertise_repo"],
        personality_state_repo=repos["personality_state_repo"],
    )
    modules["prompt_assembler"] = prompt_assembler

    # 6b. Skill activator
    from backend.modules.skill_activator import SkillActivatorModule
    skill_activator = SkillActivatorModule()
    skill_activator.set_repos(repos["skill_repo"], repos["belief_repo"])
    modules["skill_activator"] = skill_activator

    # 6c. Skill workshop
    from backend.modules.skill_workshop import SkillWorkshopModule
    skill_workshop = SkillWorkshopModule()
    skill_workshop.set_repos(repos["skill_repo"], repos["belief_repo"])
    modules["skill_workshop"] = skill_workshop

    # 7. Register skills
    _register_skills(registry, embedder, modules, belief_metabolism, llm_module)

    # 8. System prompt
    system_prompt_text = _build_system_content(identity_data, registry)
    system_prompt_tokens = estimate_tokens(system_prompt_text)
    logger.info("System prompt tokens: %s", system_prompt_tokens)

    # 9. Pipeline
    pipeline, pipeline_order = _build_pipeline(config, registry, repos, modules)

    # 10. Wire app state
    app.state.config = config
    app.state.agent_name = agent_name
    app.state.message_repo = repos["message_repo"]
    app.state.error_repo = repos["error_repo"]
    app.state.metrics_repo = repos["metrics_repo"]
    app.state.metrics_module = modules["conversation_metrics"]
    app.state.conversation_repo = repos["conversation_repo"]
    app.state.perception_repo = repos["perception_repo"]
    app.state.perception_module = modules["perception_module"]
    app.state.checkpoint_repo = repos["checkpoint_repo"]
    app.state.memory_node_repo = repos["memory_node_repo"]
    app.state.belief_repo = repos["belief_repo"]
    app.state.semantic_knot_repo = repos["semantic_knot_repo"]
    app.state.note_repo = repos["note_repo"]
    app.state.skill_repo = repos["skill_repo"]
    app.state.notification_repo = repos["notification_repo"]
    app.state.commitment_repo = repos["commitment_repo"]
    app.state.expertise_repo = repos["expertise_repo"]
    app.state.personality_state_repo = repos["personality_state_repo"]
    app.state.dream_log_repo = repos["dream_log_repo"]
    app.state.belief_metabolism = belief_metabolism
    app.state.registry = registry
    app.state.pipeline = pipeline
    app.state.pipeline_order = pipeline_order
    app.state.embedder = embedder
    app.state.llm_provider = llm_provider
    app.state.structural_provider = structural_provider
    app.state.structural_scorer = modules["structural_scorer"]
    app.state.system_prompt_tokens = system_prompt_tokens

    # 11. Background engine
    background_engine, background_provider = _init_background_engine(
        config, llm_provider, vision_provider,
    )
    app.state.background_engine = background_engine
    app.state.background_provider = background_provider
    app.state.vision_provider = vision_provider

    # 12. Background services (scheduler + daemon)
    _start_background_services(app.state)

    logger.info("All modules initialized. Server ready.")
    yield
    logger.info("Shutting down.")
    if hasattr(app.state, "dream_daemon"):
        app.state.dream_daemon.stop()


# ── App factory ────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(title="AAA Backend", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register global error handlers
    from backend.api.exceptions import register_error_handlers
    register_error_handlers(app)

    app.include_router(api_router)
    return app
