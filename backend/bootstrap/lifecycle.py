"""Application lifecycle (lifespan) and FastAPI app factory.

Extracted from backend/main.py.
Orchestrates the full startup sequence: config → DB → embedder → LLM →
modules → beliefs → skills → pipeline → background → services.
"""

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.router import router as api_router
from backend.bootstrap.background import (
    _init_background_engine,
    _start_background_services,
)
from backend.bootstrap.embedder import _init_embedder
from backend.bootstrap.modules import (
    _init_belief_engine,
    _init_modules,
    _load_identity,
)
from backend.bootstrap.pipeline import _build_pipeline, _register_skills
from backend.bootstrap.providers import _init_providers
from backend.bootstrap.repositories import _init_repos
from backend.config import load_config
from backend.core.logging_config import setup_logging
from backend.modules.llm_client import LLMClientModule
from backend.personality.assembler import PromptAssemblerModule, _build_system_content
from backend.pipeline.registry import PipelineRegistry
from backend.utils.token_counter import estimate_tokens

logger = logging.getLogger(__name__)

# Ensure logging is initialized with current config if not already setup
with contextlib.suppress(Exception):
    setup_logging(load_config())


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

    # Reset any stale exhaustion timers (fresh process, no actual rate limits in effect)
    if hasattr(llm_provider, "reset_exhaustion"):
        llm_provider.reset_exhaustion()

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

    # 6b. Skill activator & Afferent Sensory Router
    from backend.modules.sensory.afferent_sensory_router import AfferentSensoryRouter
    from backend.modules.skills.skill_activator import SkillActivatorModule

    afferent_router = AfferentSensoryRouter.from_config(config)
    skill_activator = SkillActivatorModule(router=afferent_router)
    skill_activator.set_repos(repos["skill_repo"], repos["belief_repo"])
    modules["skill_activator"] = skill_activator

    # 6c. Skill workshop
    from backend.modules.skills.skill_workshop import SkillWorkshopModule

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
    rt = config.get("research_tasks", {})
    logger.info("BOOTSTRAP CONFIG: research_tasks.manual_mode=%s", rt.get("manual_mode", "MISSING"))
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
    app.state.daily_summary_repo = repos["daily_summary_repo"]
    app.state.research_task_repo = repos["research_task_repo"]

    app.state.research_branch_repo = repos["research_branch_repo"]
    app.state.scraped_asset_repo = repos["scraped_asset_repo"]
    app.state.research_meta_log_repo = repos["research_meta_log_repo"]
    app.state.research_plan_repo = repos["research_plan_repo"]
    app.state.research_step_repo = repos["research_step_repo"]
    app.state.research_step_result_repo = repos["research_step_result_repo"]
    app.state.belief_metabolism = belief_metabolism
    app.state.registry = registry
    app.state.pipeline = pipeline
    app.state.pipeline_order = pipeline_order
    app.state.embedder = embedder
    app.state.llm_provider = llm_provider
    app.state.structural_provider = structural_provider
    app.state.structural_scorer = modules["structural_scorer"]
    app.state.system_prompt_tokens = system_prompt_tokens

    # 10.5. Research Task Manager (autonomous research engine lifecycle)
    from backend.services.research.task_manager import ResearchTaskManager

    app.state.research_task_manager = ResearchTaskManager(app.state)

    # Wire app_state into the rhizome web probe module (created before app_state existed)
    if "rhizome_web_probe" in modules:
        modules["rhizome_web_probe"]._set_app_state(app.state)

    # 11. Background engine
    background_engine, background_provider = _init_background_engine(
        config,
        llm_provider,
        vision_provider,
    )
    app.state.background_engine = background_engine
    app.state.background_provider = background_provider
    app.state.vision_provider = vision_provider

    # 12. Background services (scheduler + daemon)
    _start_background_services(app.state)

    logger.info("All modules initialized. Server ready.")
    try:
        yield
    finally:
        logger.info("Shutting down.")
        if hasattr(app.state, "startup_scheduler"):
            await app.state.startup_scheduler.aclose()
        if hasattr(app.state, "dream_daemon"):
            await app.state.dream_daemon.aclose()
        backup_task = getattr(app.state, "db_backup_task", None)
        if backup_task:
            backup_task.cancel()
            await asyncio.gather(backup_task, return_exceptions=True)


# ── App factory ────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(title="AAA Backend", version="0.1.0", lifespan=lifespan)
    import os

    env_origins = os.environ.get("AAA_CORS_ORIGINS", "").strip()
    cors_origins = (
        [o.strip() for o in env_origins.split(",") if o.strip()]
        if env_origins
        else [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8499",
            "http://127.0.0.1:8499",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register global error handlers
    from backend.api.exceptions import register_error_handlers

    register_error_handlers(app)

    app.include_router(api_router)

    # Public preview endpoint (no auth — mounted separately from the authed /api router)
    from backend.api.routes.preview import router as preview_router

    app.include_router(preview_router)

    # Public artwork endpoint for The Diffractive Grain (/av) — no auth
    from backend.api.routes.av import router as av_router

    app.include_router(av_router)

    return app
