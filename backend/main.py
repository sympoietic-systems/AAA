import logging
import os

# Bypass system registry proxy settings
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"
for k in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]:
    if k in os.environ:
        del os.environ[k]

from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.router import router
from backend.config import load_config
from backend.metabolisation.pipeline import ProcessingPipeline
from backend.modules.background_tasks.actions.consolidate import ConsolidateAction
from backend.modules.background_tasks.actions.conversation_summary import ConversationSummaryAction
from backend.modules.background_tasks.actions.document_collision import DocumentCollisionAction
from backend.modules.background_tasks.actions.semantic_knot import SemanticKnotAction
from backend.modules.background_tasks.actions.summarize import SummarizeAction
from backend.modules.background_tasks.actions.title import GenerateTitleAction
from backend.modules.background_tasks.actions.dream_topic_decision import DreamTopicDecisionAction
from backend.modules.background_tasks.actions.resonance_finder import ResonanceFinderAction
from backend.modules.background_tasks.actions.refine_skill import RefineSkillAction
from backend.modules.background_tasks.actions.metabolize_skill import MetabolizeSkillAction
from backend.modules.background_tasks.actions.refine_belief import RefineBeliefAction
from backend.modules.background_tasks.engine import BackgroundTaskEngine
from backend.modules.commitment_store import CommitmentStore
from backend.modules.consolidation_checkpoint import ConsolidationCheckpointModule
from backend.modules.context_collector import ContextCollectorModule
from backend.modules.conversation_metrics import ConversationMetricsModule
from backend.modules.diffractive_retrieval import DiffractiveRetrievalModule
from backend.modules.embedder import EmbedderModule
from backend.modules.expertise_engine import ExpertiseEngine
from backend.modules.homeostatic_regulator import HomeostaticRegulatorModule
from backend.modules.llm_client import (
    LLMClientModule,
    ModelPoolProvider,
    OpenAICompatibleProvider,
    OpenRouterProvider,
)
from backend.modules.perception import PerceptionModule
from backend.modules.sedimentation_retrieval import SedimentationRetrievalModule
from backend.modules.structural_engine import CompositeStructuralScorer, StructuralScorerModule
from backend.modules.trait_computer import TraitComputer
from backend.modules.web_retrieval import WebRetrievalModule
from backend.personality.assembler import PromptAssemblerModule, _build_system_content
from backend.pipeline.metadata import ModuleMeta
from backend.pipeline.registry import PipelineRegistry
from backend.storage.database import get_db_path, init_db
from backend.storage.repository import (
    BeliefRepository,
    CommitmentRepository,
    ConsolidationCheckpointRepository,
    ConversationRepository,
    DreamLogRepository,
    ErrorLogRepository,
    ExpertiseRepository,
    MemoryNodeRepository,
    MessageRepository,
    MetricsRepository,
    NoteRepository,
    NotificationRepository,
    PerceptionSedimentRepository,
    PersonalityStateRepository,
    SemanticKnotRepository,
    SkillRepository,
)
from backend.utils.token_counter import estimate_tokens

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

PROVIDER_DEFAULTS = {
    "openrouter": {"model": "deepseek/deepseek-chat", "api_base": "https://openrouter.ai/api/v1"},
    "deepseek": {"model": "deepseek-v4-pro", "api_base": "https://api.deepseek.com"},
    "openai_compatible": {"model": "deepseek-v4-pro", "api_base": "https://api.deepseek.com"},
}


# ── Provider factory (merged from _create_llm_provider + _create_provider_from_config) ──

def _create_provider(cfg: dict, *, use_default_params: bool = True, label: str = ""):
    provider_name = cfg.get("provider", "openrouter")
    defaults = PROVIDER_DEFAULTS.get(provider_name, {})
    api_key = cfg.get("api_key", "")
    api_base = cfg.get("api_base") or defaults.get("api_base", "")
    model = cfg.get("model") or defaults.get("model", "deepseek-chat")
    models = cfg.get("models", [])
    thinking_cfg = cfg.get("thinking", {})
    thinking = thinking_cfg.get("enabled", False)
    reasoning_effort = thinking_cfg.get("effort", "high")
    default_params = cfg.get("default_params") if use_default_params else None

    if models:
        fallback = cfg.get("fallback_model", "openrouter/free")
        google_keys = cfg.get("google_keys", [])
        deepseek_keys = cfg.get("deepseek_keys", [])
        openrouter_keys = cfg.get("openrouter_keys", [])
        google_api_base = cfg.get("google_api_base", "https://generativelanguage.googleapis.com/v1beta/openai")
        deepseek_api_base = cfg.get("deepseek_api_base", "https://api.deepseek.com")
        cooldown_seconds = cfg.get("cooldown_seconds", 300)
        if label:
            logger.info("%s model pool: %s (fallback: %s)", label, models, fallback)
        return ModelPoolProvider(
            api_key=api_key, models=models, fallback_model=fallback, api_base=api_base,
            google_keys=google_keys, deepseek_keys=deepseek_keys, openrouter_keys=openrouter_keys,
            google_api_base=google_api_base, deepseek_api_base=deepseek_api_base,
            cooldown_seconds=cooldown_seconds, thinking=thinking, reasoning_effort=reasoning_effort,
            default_params=default_params,
        )

    effective_model = model
    if model.startswith("google_router/"):
        effective_model = model.split("google_router/", 1)[1]
        key = (cfg.get("google_keys", []) or [api_key])[0]
        return OpenAICompatibleProvider(
            api_key=key, model=effective_model,
            api_base=cfg.get("google_api_base", "https://generativelanguage.googleapis.com/v1beta/openai"),
            provider_name="google", default_params=default_params,
        )
    elif model.startswith("deepseek_router/"):
        effective_model = model.split("deepseek_router/", 1)[1]
        key = (cfg.get("deepseek_keys", []) or [api_key])[0]
        return OpenAICompatibleProvider(
            api_key=key, model=effective_model,
            api_base=cfg.get("deepseek_api_base", "https://api.deepseek.com"),
            provider_name="deepseek", default_params=default_params,
            thinking=thinking, reasoning_effort=reasoning_effort,
        )
    elif model.startswith("openrouter_router/"):
        effective_model = model.split("openrouter_router/", 1)[1]
        key = (cfg.get("openrouter_keys", []) or [api_key])[0]
        return OpenRouterProvider(
            api_key=key, model=effective_model,
            api_base=api_base or "https://openrouter.ai/api/v1",
            default_params=default_params, thinking=thinking, reasoning_effort=reasoning_effort,
        )

    if provider_name == "openrouter" or model:
        return OpenRouterProvider(
            api_key=api_key, model=model,
            api_base=api_base or "https://openrouter.ai/api/v1",
            default_params=default_params, thinking=thinking, reasoning_effort=reasoning_effort,
        )

    return OpenAICompatibleProvider(
        api_key=api_key, model=model, api_base=api_base,
        provider_name=provider_name, default_params=default_params,
        thinking=thinking, reasoning_effort=reasoning_effort,
    )


# Backward-compat wrappers
def _create_llm_provider(cfg: dict):
    return _create_provider(cfg, use_default_params=True, label="Main")

def _create_provider_from_config(cfg: dict):
    return _create_provider(cfg, use_default_params=False)


# ── Initialization factories ──

def _init_repos(config: dict) -> dict:
    db_path = config.get("database", {}).get("path", "data/aaa.db")
    full_db_path = get_db_path(db_path)
    init_conn = init_db(str(full_db_path))
    init_conn.close()
    logger.info("Database initialized at %s", full_db_path)
    path = str(full_db_path)
    return {
        "message_repo": MessageRepository(path),
        "error_repo": ErrorLogRepository(path),
        "metrics_repo": MetricsRepository(path),
        "conversation_repo": ConversationRepository(path),
        "perception_repo": PerceptionSedimentRepository(path),
        "checkpoint_repo": ConsolidationCheckpointRepository(path),
        "memory_node_repo": MemoryNodeRepository(path),
        "belief_repo": BeliefRepository(path),
        "semantic_knot_repo": SemanticKnotRepository(path),
        "note_repo": NoteRepository(path),
        "skill_repo": SkillRepository(path),
        "notification_repo": NotificationRepository(path),
        "commitment_repo": CommitmentRepository(path),
        "expertise_repo": ExpertiseRepository(path),
        "personality_state_repo": PersonalityStateRepository(path),
        "dream_log_repo": DreamLogRepository(path),
    }


def _init_embedder(config: dict):
    embed_cfg = config.get("embedding", {})
    embedder = EmbedderModule(
        model_name=embed_cfg.get("model", "all-MiniLM-L6-v2"),
        device=embed_cfg.get("device", "cpu"),
        offline=embed_cfg.get("offline", True),
        cache_dir=embed_cfg.get("cache_dir"),
    )
    logger.info("Pre-loading embedding model: %s", embed_cfg.get("model"))
    embedder.service.preload()
    return embedder


def _init_providers(config: dict):
    llm_cfg = config.get("llm", {})
    llm_provider = _create_provider(llm_cfg, use_default_params=True, label="Main")

    struct_cfg = config.get("structural_llm", {})
    if not struct_cfg.get("model") and not struct_cfg.get("models"):
        bg_cfg = config.get("background_llm", {})
        struct_cfg = {**bg_cfg, "thinking": {"enabled": False, "effort": "low"}}
    else:
        struct_cfg.setdefault("thinking", {"enabled": False, "effort": "low"})
    structural_provider = _create_provider(struct_cfg, use_default_params=False)

    vision_provider = None
    vision_llm_cfg = config.get("vision_llm", {})
    if vision_llm_cfg.get("models") or vision_llm_cfg.get("model"):
        try:
            vision_provider = _create_provider(vision_llm_cfg, use_default_params=False)
            logger.info("Vision model(s): %s", vision_llm_cfg.get("models") or vision_llm_cfg.get("model"))
        except Exception:
            logger.warning("Failed to initialize vision provider")

    return llm_provider, structural_provider, vision_provider


def _init_modules(config: dict, repos: dict, embedder, structural_provider, vision_provider):
    ctx_cfg = config.get("context", {})
    context_collector = ContextCollectorModule(
        message_repo=repos["message_repo"], note_repo=repos["note_repo"],
        max_history=ctx_cfg.get("max_history", 20),
        floating_window=ctx_cfg.get("floating_window", 8),
        caveman_enabled=ctx_cfg.get("caveman_enabled", True),
    )

    metrics_cfg = config.get("homeostasis", {})
    conversation_metrics = ConversationMetricsModule(
        message_repo=repos["message_repo"],
        pairwise_window=metrics_cfg.get("pairwise_window", 5),
        entropy_window=metrics_cfg.get("entropy_window", 5),
        agent_self_window=metrics_cfg.get("agent_self_window", 5),
    )

    homeostatic_regulator = HomeostaticRegulatorModule()

    # Dynamic personality — trait computer
    trait_cfg = config.get("dynamic_personality", {}).get("trait_computer", {})
    trait_computer = TraitComputer(
        personality_state_repo=repos["personality_state_repo"],
        config=trait_cfg,
        notification_repo=repos["notification_repo"],
    )

    # Dynamic personality — expertise engine
    from backend.modules.structural_engine import LexiconScorer
    expertise_cfg = config.get("dynamic_personality", {}).get("expertise", {})
    expert_lexicon = LexiconScorer()
    expertise_engine = ExpertiseEngine(
        expertise_repo=repos["expertise_repo"],
        config=expertise_cfg,
        lexicon_scorer=expert_lexicon,
        notification_repo=repos["notification_repo"],
    )

    # Dynamic personality — commitment store
    commitment_cfg = config.get("dynamic_personality", {}).get("commitments", {})
    commitment_store = CommitmentStore(
        commitment_repo=repos["commitment_repo"],
        belief_repo=repos["belief_repo"],
        config=commitment_cfg,
        lexicon_scorer=expert_lexicon,
        notification_repo=repos["notification_repo"],
    )

    sediment_cfg = config.get("sedimentation", {})
    sedimentation_retrieval = SedimentationRetrievalModule(
        message_repo=repos["message_repo"],
        sediment_token_budget=sediment_cfg.get("sediment_token_budget", 2000),
        sediment_count=sediment_cfg.get("sediment_count", 10),
        similarity_threshold=sediment_cfg.get("similarity_threshold", 0.3),
    )

    diffractive_cfg = config.get("diffractive_retrieval", {})
    diffractive_retrieval = DiffractiveRetrievalModule(
        message_repo=repos["message_repo"],
        perception_repo=repos["perception_repo"],
        semantic_knot_repo=repos["semantic_knot_repo"],
        enabled=diffractive_cfg.get("enabled", True),
        similarity_range_min=diffractive_cfg.get("similarity_range_min", 0.35),
        similarity_range_max=diffractive_cfg.get("similarity_range_max", 0.55),
        file_range_min=diffractive_cfg.get("file_range_min", 0.25),
        file_range_max=diffractive_cfg.get("file_range_max", 0.45),
        max_diffractive_count=diffractive_cfg.get("max_diffractive_count", 3),
        token_budget=diffractive_cfg.get("token_budget", 1500),
    )

    structural_scorer = StructuralScorerModule(
        CompositeStructuralScorer(llm_provider=structural_provider, config=config)
    )

    perception_cfg = config.get("perception", {})
    perception_module = PerceptionModule(
        perception_repo=repos["perception_repo"],
        embedding_service=embedder.service,
        file_token_budget=perception_cfg.get("file_token_budget", 3000),
        top_k_chunks=perception_cfg.get("top_k_chunks", 6),
        chunk_size=perception_cfg.get("chunk_size", 512),
        chunk_overlap=perception_cfg.get("chunk_overlap", 64),
        similarity_threshold=perception_cfg.get("similarity_threshold", 0.25),
        llm_provider=structural_provider,
        vision_provider=vision_provider,
    )

    web_retrieval = WebRetrievalModule(
        perception_repo=repos["perception_repo"],
        embedder=embedder,
        structural_scorer=structural_scorer,
        llm_provider=structural_provider,
        config=config,
    )

    consolidation_checkpoint = ConsolidationCheckpointModule(
        checkpoint_repo=repos["checkpoint_repo"],
        consolidate_threshold=ctx_cfg.get("consolidate_threshold", 15),
        memory_node_repo=repos["memory_node_repo"],
    )

    return {
        "context_collector": context_collector,
        "conversation_metrics": conversation_metrics,
        "trait_computer": trait_computer,
        "expertise_engine": expertise_engine,
        "commitment_store": commitment_store,
        "homeostatic_regulator": homeostatic_regulator,
        "sedimentation_retrieval": sedimentation_retrieval,
        "diffractive_retrieval": diffractive_retrieval,
        "structural_scorer": structural_scorer,
        "perception_module": perception_module,
        "web_retrieval": web_retrieval,
        "consolidation_checkpoint": consolidation_checkpoint,
    }


def _init_belief_engine(repos: dict, identity_path: Path, llm_provider=None):
    from backend.modules.belief_engine import BeliefDynamicsEngine
    return BeliefDynamicsEngine(
        belief_repo=repos["belief_repo"],
        message_repo=repos["message_repo"],
        identity_yaml_path=identity_path,
        llm_provider=llm_provider,
    )


def _load_identity(config: dict) -> tuple[dict, str, Path]:
    personality_cfg = config.get("personality", {})
    identity_path = Path(personality_cfg.get("path", "backend/personality/identity.yaml"))
    if not identity_path.is_absolute():
        identity_path = Path(__file__).parent.parent / identity_path

    identity_data = {}
    agent_name = "symbia"
    if identity_path.exists():
        with open(identity_path) as f:
            identity_data = yaml.safe_load(f)
            agent_name = identity_data.get("agent", {}).get("name", "symbia")
    logger.info("Agent identity: %s", agent_name)
    return identity_data, agent_name, identity_path


def _register_skills(registry: PipelineRegistry, embedder, modules: dict, belief_metabolism, llm_module):
    from backend.app_factory import register_all
    register_all(registry, embedder, modules, belief_metabolism, llm_module)


def _build_pipeline(config: dict, registry: PipelineRegistry, repos: dict, modules: dict):
    pipeline_order = config.get("pipeline", {}).get(
        "modules",
        ["embedder", "structural_scorer", "perception", "web_retrieval", "conversation_metrics",
         "trait_computer", "expertise_engine",
         "commitment_store",
         "context_collector", "consolidation_checkpoint", "sedimentation_retrieval",
         "diffractive_retrieval", "belief_metabolism", "skill_activator",
         "skill_workshop", "prompt_assembler", "homeostatic_regulator",
         "llm_client"],
    )
    pipeline_modules = registry.resolve_pipeline(pipeline_order)

    def log_pipeline_error(module_name: str, error: Exception, payload: dict):
        repos["error_repo"].log_error(
            module=module_name, error=error,
            context={"input": payload.get("content", "")[:500]},
        )

    return ProcessingPipeline(modules=pipeline_modules, error_handler=log_pipeline_error), pipeline_order


def _init_background_engine(config: dict, llm_provider, vision_provider):
    bg_cfg = config.get("background_llm", {})
    background_provider = None
    if bg_cfg.get("models") or bg_cfg.get("model"):
        try:
            background_provider = _create_provider(bg_cfg, use_default_params=False)
            logger.info("Background model: %s", bg_cfg.get("models") or bg_cfg.get("model"))
        except Exception:
            logger.warning("Failed to initialize background provider, using primary")
            background_provider = llm_provider

    engine = BackgroundTaskEngine(
        provider=background_provider or llm_provider,
        vision_provider=vision_provider,
    )
    engine.register(GenerateTitleAction())
    engine.register(SummarizeAction())
    engine.register(ConsolidateAction())
    engine.register(ConversationSummaryAction())
    engine.register(DocumentCollisionAction())
    engine.register(SemanticKnotAction())
    engine.register(DreamTopicDecisionAction())
    engine.register(ResonanceFinderAction())
    engine.register(RefineSkillAction())
    engine.register(MetabolizeSkillAction())
    engine.register(RefineBeliefAction())
    logger.info("Background task engine initialized with actions: %s", engine.list_actions())
    return engine, background_provider


def _start_background_services(app_state):
    from backend.metabolisation.scheduler import BackgroundStartupScheduler
    from backend.services.file import FileService

    scheduler = BackgroundStartupScheduler(app_state, FileService.process_and_summarize)
    app_state.startup_scheduler = scheduler
    scheduler.start()

    from backend.metabolisation.daemon import AutopoieticDreamDaemon
    dream_daemon = AutopoieticDreamDaemon(app_state)
    app_state.dream_daemon = dream_daemon
    dream_daemon.start()


# ── App lifecycle ──

@asynccontextmanager
async def lifespan(app: FastAPI):
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
        identity_path=identity_path, skill_registry=registry,
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
    background_engine, background_provider = _init_background_engine(config, llm_provider, vision_provider)
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


def create_app() -> FastAPI:
    app = FastAPI(title="AAA Backend", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    from backend.config import load_config

    try:
        config = load_config()
        server_cfg = config.get("server", {})
        host = server_cfg.get("host", "127.0.0.1")
        port = int(server_cfg.get("port", 8000))
    except Exception:
        host = os.environ.get("AAA_SERVER_HOST", "127.0.0.1")
        port = int(os.environ.get("AAA_SERVER_PORT", 8000))

    uvicorn.run("backend.main:app", host=host, port=port, reload=False)
