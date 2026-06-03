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

from backend.api.routes import router
from backend.config import load_config
from backend.core.pipeline import ProcessingPipeline
from backend.modules.background_tasks.actions.consolidate import ConsolidateAction
from backend.modules.background_tasks.actions.summarize import SummarizeAction
from backend.modules.background_tasks.actions.title import GenerateTitleAction
from backend.modules.background_tasks.actions.document_collision import DocumentCollisionAction
from backend.modules.background_tasks.actions.semantic_knot import SemanticKnotAction
from backend.modules.background_tasks.engine import BackgroundTaskEngine
from backend.modules.consolidation_checkpoint import ConsolidationCheckpointModule
from backend.modules.context_collector import ContextCollectorModule
from backend.modules.conversation_metrics import ConversationMetricsModule
from backend.modules.embedder import EmbedderModule
from backend.modules.homeostatic_regulator import HomeostaticRegulatorModule
from backend.modules.diffractive_retrieval import DiffractiveRetrievalModule
from backend.modules.web_retrieval import WebRetrievalModule

from backend.modules.llm_client import (
    LLMClientModule,
    ModelPoolProvider,
    OpenAICompatibleProvider,
    OpenRouterProvider,
)
from backend.modules.perception import PerceptionModule
from backend.modules.sedimentation_retrieval import SedimentationRetrievalModule
from backend.modules.structural_engine import StructuralScorerModule
from backend.personality.assembler import PromptAssemblerModule, _build_system_content
from backend.skills.metadata import SkillMeta
from backend.skills.registry import SkillRegistry
from backend.storage.database import get_db_path, init_db
from backend.storage.repository import (
    ConsolidationCheckpointRepository,
    ConversationRepository,
    ErrorLogRepository,
    MessageRepository,
    MetricsRepository,
    PerceptionSedimentRepository,
    BeliefRepository,
    SemanticKnotRepository,
)
from backend.utils.token_counter import estimate_tokens

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


PROVIDER_DEFAULTS = {
    "openrouter": {
        "model": "deepseek/deepseek-chat",
        "api_base": "https://openrouter.ai/api/v1",
    },
    "deepseek": {
        "model": "deepseek-v4-pro",
        "api_base": "https://api.deepseek.com",
    },
    "openai_compatible": {
        "model": "deepseek-v4-pro",
        "api_base": "https://api.deepseek.com",
    },
}


def _create_llm_provider(cfg: dict):
    provider_name = cfg.get("provider", "openrouter")
    defaults = PROVIDER_DEFAULTS.get(provider_name, {})

    api_key = cfg.get("api_key", "")
    model = cfg.get("model") or defaults.get("model", "deepseek-chat")
    api_base = cfg.get("api_base") or defaults.get("api_base", "")
    default_params = cfg.get("default_params")
    thinking_cfg = cfg.get("thinking", {})
    thinking = thinking_cfg.get("enabled", False)
    reasoning_effort = thinking_cfg.get("effort", "high")
    models = cfg.get("models", [])

    if models:
        fallback = cfg.get("fallback_model", "")
        google_keys = cfg.get("google_keys", [])
        deepseek_keys = cfg.get("deepseek_keys", [])
        openrouter_keys = cfg.get("openrouter_keys", [])
        google_api_base = cfg.get("google_api_base", "https://generativelanguage.googleapis.com/v1beta/openai")
        deepseek_api_base = cfg.get("deepseek_api_base", "https://api.deepseek.com")
        cooldown_seconds = cfg.get("cooldown_seconds", 300)
        logger.info("Main model pool: %s (fallback: %s)", models, fallback)
        return ModelPoolProvider(
            api_key=api_key,
            models=models,
            fallback_model=fallback,
            api_base=api_base,
            google_keys=google_keys,
            deepseek_keys=deepseek_keys,
            openrouter_keys=openrouter_keys,
            google_api_base=google_api_base,
            deepseek_api_base=deepseek_api_base,
            cooldown_seconds=cooldown_seconds,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
        )

    if model.startswith("google_router/"):
        actual_model = model.split("google_router/", 1)[1]
        google_keys = cfg.get("google_keys", [])
        google_api_base = cfg.get("google_api_base", "https://generativelanguage.googleapis.com/v1beta/openai")
        key = google_keys[0] if google_keys else api_key
        return OpenAICompatibleProvider(
            api_key=key,
            model=actual_model,
            api_base=google_api_base,
            provider_name="google",
            default_params=default_params,
        )
    elif model.startswith("deepseek_router/"):
        actual_model = model.split("deepseek_router/", 1)[1]
        deepseek_keys = cfg.get("deepseek_keys", [])
        deepseek_api_base = cfg.get("deepseek_api_base", "https://api.deepseek.com")
        key = deepseek_keys[0] if deepseek_keys else api_key
        return OpenAICompatibleProvider(
            api_key=key,
            model=actual_model,
            api_base=deepseek_api_base,
            provider_name="deepseek",
            default_params=default_params,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
        )
    elif model.startswith("openrouter_router/"):
        actual_model = model.split("openrouter_router/", 1)[1]
        openrouter_keys = cfg.get("openrouter_keys", [])
        key = openrouter_keys[0] if openrouter_keys else api_key
        return OpenRouterProvider(
            api_key=key,
            model=actual_model,
            api_base=api_base or "https://openrouter.ai/api/v1",
            default_params=default_params,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
        )

    if provider_name == "openrouter":
        return OpenRouterProvider(
            api_key=api_key,
            model=model,
            api_base=api_base or "https://openrouter.ai/api/v1",
            default_params=default_params,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
        )

    return OpenAICompatibleProvider(
        api_key=api_key,
        model=model,
        api_base=api_base,
        provider_name=provider_name,
        default_params=default_params,
        thinking=thinking,
        reasoning_effort=reasoning_effort,
    )


def _create_provider_from_config(cfg: dict) -> OpenAICompatibleProvider | ModelPoolProvider:
    api_key = cfg.get("api_key", "")
    api_base = cfg.get("api_base", "https://openrouter.ai/api/v1")
    models = cfg.get("models", [])
    model = cfg.get("model", "")
    thinking_cfg = cfg.get("thinking", {})
    thinking = thinking_cfg.get("enabled", False)
    reasoning_effort = thinking_cfg.get("effort", "low")

    if models:
        fallback = cfg.get("fallback_model", "openrouter/free")
        google_keys = cfg.get("google_keys", [])
        deepseek_keys = cfg.get("deepseek_keys", [])
        openrouter_keys = cfg.get("openrouter_keys", [])
        google_api_base = cfg.get("google_api_base", "https://generativelanguage.googleapis.com/v1beta/openai")
        deepseek_api_base = cfg.get("deepseek_api_base", "https://api.deepseek.com")
        cooldown_seconds = cfg.get("cooldown_seconds", 300)
        logger.info("Background model pool: %s (fallback: %s)", models, fallback)
        return ModelPoolProvider(
            api_key=api_key,
            models=models,
            fallback_model=fallback,
            api_base=api_base,
            google_keys=google_keys,
            deepseek_keys=deepseek_keys,
            openrouter_keys=openrouter_keys,
            google_api_base=google_api_base,
            deepseek_api_base=deepseek_api_base,
            cooldown_seconds=cooldown_seconds,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
        )

    if model:
        if model.startswith("google_router/"):
            actual_model = model.split("google_router/", 1)[1]
            google_keys = cfg.get("google_keys", [])
            google_api_base = cfg.get("google_api_base", "https://generativelanguage.googleapis.com/v1beta/openai")
            key = google_keys[0] if google_keys else api_key
            return OpenAICompatibleProvider(
                api_key=key,
                model=actual_model,
                api_base=google_api_base,
                provider_name="google",
                thinking=thinking,
                reasoning_effort=reasoning_effort,
            )
        elif model.startswith("openrouter_router/"):
            actual_model = model.split("openrouter_router/", 1)[1]
            openrouter_keys = cfg.get("openrouter_keys", [])
            key = openrouter_keys[0] if openrouter_keys else api_key
            return OpenRouterProvider(
                api_key=key,
                model=actual_model,
                api_base=api_base,
                thinking=thinking,
                reasoning_effort=reasoning_effort,
            )
        else:
            return OpenRouterProvider(
                api_key=api_key,
                model=model,
                api_base=api_base,
                thinking=thinking,
                reasoning_effort=reasoning_effort,
            )

    raise ValueError("No model or models configured for background/vision provider")


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = load_config()

    db_path = config.get("database", {}).get("path", "data/aaa.db")
    full_db_path = get_db_path(db_path)
    init_conn = init_db(str(full_db_path))
    init_conn.close()
    logger.info(f"Database initialized at {full_db_path}")

    message_repo = MessageRepository(str(full_db_path))
    error_repo = ErrorLogRepository(str(full_db_path))
    metrics_repo = MetricsRepository(str(full_db_path))
    conversation_repo = ConversationRepository(str(full_db_path))
    perception_repo = PerceptionSedimentRepository(str(full_db_path))
    checkpoint_repo = ConsolidationCheckpointRepository(str(full_db_path))
    belief_repo = BeliefRepository(str(full_db_path))
    semantic_knot_repo = SemanticKnotRepository(str(full_db_path))

    embed_cfg = config.get("embedding", {})
    embedder = EmbedderModule(
        model_name=embed_cfg.get("model", "all-MiniLM-L6-v2"),
        device=embed_cfg.get("device", "cpu"),
        offline=embed_cfg.get("offline", True),
        cache_dir=embed_cfg.get("cache_dir"),
    )
    logger.info("Pre-loading embedding model: %s", embed_cfg.get("model"))
    embedder.service.preload()

    llm_cfg = config.get("llm", {})
    provider = _create_llm_provider(llm_cfg)
    llm_module = LLMClientModule(provider)

    # ── Create Structural Scorer Provider ─────────────────
    struct_cfg = config.get("structural_llm", {})
    if not struct_cfg.get("model") and not struct_cfg.get("models"):
        bg_cfg = config.get("background_llm", {})
        struct_cfg = {
            **bg_cfg,
            "thinking": {"enabled": False, "effort": "low"}
        }
    else:
        if "thinking" not in struct_cfg:
            struct_cfg["thinking"] = {"enabled": False, "effort": "low"}

    structural_provider = _create_provider_from_config(struct_cfg)

    from backend.modules.structural_engine import CompositeStructuralScorer
    structural_scorer = StructuralScorerModule(
        CompositeStructuralScorer(llm_provider=structural_provider, config=config)
    )

    ctx_cfg = config.get("context", {})
    context_collector = ContextCollectorModule(
        message_repo=message_repo,
        max_history=ctx_cfg.get("max_history", 20),
        floating_window=ctx_cfg.get("floating_window", 8),
        caveman_enabled=ctx_cfg.get("caveman_enabled", True),
    )

    metrics_cfg = config.get("homeostasis", {})
    conversation_metrics = ConversationMetricsModule(
        message_repo=message_repo,
        pairwise_window=metrics_cfg.get("pairwise_window", 5),
        entropy_window=metrics_cfg.get("entropy_window", 5),
        agent_self_window=metrics_cfg.get("agent_self_window", 5),
    )

    homeostatic_regulator = HomeostaticRegulatorModule()

    sediment_cfg = config.get("sedimentation", {})
    sedimentation_retrieval = SedimentationRetrievalModule(
        message_repo=message_repo,
        sediment_token_budget=sediment_cfg.get("sediment_token_budget", 2000),
        sediment_count=sediment_cfg.get("sediment_count", 10),
        similarity_threshold=sediment_cfg.get("similarity_threshold", 0.3),
    )

    diffractive_cfg = config.get("diffractive_retrieval", {})
    diffractive_retrieval = DiffractiveRetrievalModule(
        message_repo=message_repo,
        perception_repo=perception_repo,
        semantic_knot_repo=semantic_knot_repo,
        enabled=diffractive_cfg.get("enabled", True),
        similarity_range_min=diffractive_cfg.get("similarity_range_min", 0.35),
        similarity_range_max=diffractive_cfg.get("similarity_range_max", 0.55),
        file_range_min=diffractive_cfg.get("file_range_min", 0.25),
        file_range_max=diffractive_cfg.get("file_range_max", 0.45),
        max_diffractive_count=diffractive_cfg.get("max_diffractive_count", 3),
        token_budget=diffractive_cfg.get("token_budget", 1500),
    )


    personality_cfg = config.get("personality", {})
    identity_path = Path(personality_cfg.get("path", "backend/personality/identity.yaml"))
    if not identity_path.is_absolute():
        identity_path = Path(__file__).parent.parent / identity_path

    agent_name = "symbia"
    if identity_path.exists():
        with open(identity_path) as f:
            identity_data = yaml.safe_load(f)
            agent_name = identity_data.get("agent", {}).get("name", "symbia")
    logger.info(f"Agent identity: {agent_name}")

    from backend.modules.belief_engine import BeliefDynamicsEngine
    belief_metabolism = BeliefDynamicsEngine(
        belief_repo=belief_repo,
        message_repo=message_repo,
        identity_yaml_path=identity_path,
    )

    registry = SkillRegistry()
    registry.register_with_meta(
        "embedder", lambda: embedder,
        SkillMeta(name="embedder", description="Encodes text into vector embeddings",
                  category="perception", always_run=True,
                  children=[
                      SkillMeta(name="text_encoder", description="Translates textual sequences into 384-dimensional dense vectors", category="perception"),
                      SkillMeta(name="vector_cache", description="Caches computed embeddings to prevent redundant API calls", category="perception"),
                  ]),
    )
    registry.register_with_meta(
        "structural_scorer", lambda: structural_scorer,
        SkillMeta(name="structural_scorer", description="Calculates 16-dimensional cybernetic structural signatures of the message text",
                  category="perception", always_run=True,
                  children=[
                      SkillMeta(name="signature_generator", description="Parses syntax pattern frequencies to output a 16D array", category="perception"),
                      SkillMeta(name="dynamic_coordinate_warper", description="Applies dynamic coordinate warping scaling factors", category="perception"),
                  ]),
    )
    registry.register_with_meta(
        "conversation_metrics", lambda: conversation_metrics,
        SkillMeta(name="conversation_metrics", description="Computes real-time conversational vitality and paskian metrics",
                  category="perception", always_run=True,
                  children=[
                      SkillMeta(name="surprise_index", description="Exponentially decaying weighted surprise (d=0.75)", category="perception"),
                      SkillMeta(name="boringness", description="Joint failure of mutual perturbation: (1 - rP_t) * (1 - MPI_{t-1})", category="perception"),
                      SkillMeta(name="conceptual_velocity", description="Disjoint window centroid drift rate (k=3)", category="perception"),
                  ]),
    )
    registry.register_with_meta(
        "context_collector", lambda: context_collector,
        SkillMeta(name="context_collector", description="Gathers conversation history",
                  category="memory", always_run=True,
                  children=[
                      SkillMeta(name="floating_window", description="Last N messages kept raw and uncompressed", category="memory"),
                      SkillMeta(name="caveman_compression", description="Strips filler words from older messages, ~50% token reduction", category="memory"),
                  ]),
    )

    consolidation_checkpoint = ConsolidationCheckpointModule(
        checkpoint_repo=checkpoint_repo,
        consolidate_threshold=ctx_cfg.get("consolidate_threshold", 15),
    )
    registry.register_with_meta(
        "consolidation_checkpoint", lambda: consolidation_checkpoint,
        SkillMeta(name="consolidation_checkpoint", description="Injects LLM-consolidated conversation summaries and triggers new checkpoints",
                  category="memory", always_run=True,
                  children=[
                      SkillMeta(name="checkpoint_inject", description="Prepends [Consolidated memory: ...] system message from latest checkpoint", category="memory"),
                      SkillMeta(name="consolidate_trigger", description="Flags conversations for background consolidation every N messages", category="memory"),
                  ]),
    )

    vision_llm_cfg = config.get("vision_llm", {})
    vision_provider = None
    if vision_llm_cfg.get("models") or vision_llm_cfg.get("model"):
        try:
            vision_provider = _create_provider_from_config(vision_llm_cfg)
            logger.info(f"Vision model(s): {vision_llm_cfg.get('models') or vision_llm_cfg.get('model')}")
        except Exception:
            logger.warning("Failed to initialize vision provider")

    perception_cfg = config.get("perception", {})
    perception_module = PerceptionModule(
        perception_repo=perception_repo,
        embedding_service=embedder.service,
        file_token_budget=perception_cfg.get("file_token_budget", 3000),
        top_k_chunks=perception_cfg.get("top_k_chunks", 6),
        chunk_size=perception_cfg.get("chunk_size", 512),
        chunk_overlap=perception_cfg.get("chunk_overlap", 64),
        similarity_threshold=perception_cfg.get("similarity_threshold", 0.25),
        llm_provider=structural_provider,
        vision_provider=vision_provider,
    )
    registry.register_with_meta(
        "perception", lambda: perception_module,
        SkillMeta(name="perception", description="Extracts text from uploaded files, chunks, embeds, and retrieves relevant sediment via similarity",
                  category="perception", always_run=False,
                  triggers=["file", "document", "pdf", "upload", "read"],
                  children=[
                      SkillMeta(name="file_extractor", description="Parses text from plain text, PDF, and DOCX files", category="perception"),
                      SkillMeta(name="tripartite_vision", description="Performs OCR, semantic description, diffractive analysis, and aesthetic scoring on images", category="perception"),
                  ]),
    )

    web_retrieval_cfg = config.get("web_retrieval", {})
    web_retrieval = WebRetrievalModule(
        perception_repo=perception_repo,
        embedder=embedder,
        structural_scorer=structural_scorer,
        llm_provider=structural_provider,
        config=config,
    )
    registry.register_with_meta(
        "web_retrieval", lambda: web_retrieval,
        SkillMeta(name="web_retrieval", description="Exogenous rhizomatic web retrieval and HTML scraping",
                  category="perception", always_run=True,
                  children=[
                      SkillMeta(name="rhizome_web_probe", description="Scrapes search engines dynamically to bring exogenous context", category="perception"),
                      SkillMeta(name="html_scraper", description="Strips HTML styling/scripts and parses main content to markdown", category="perception"),
                  ]),
    )

    prompt_assembler = PromptAssemblerModule(
        identity_path=identity_path,
        skill_registry=registry,
        max_context_tokens=ctx_cfg.get("max_tokens", 16384),
    )
    registry.register_with_meta(
        "prompt_assembler", lambda: prompt_assembler,
        SkillMeta(name="prompt_assembler", description="Composes system prompt from identity, skills, sediment, and conversation history within token budget",
                  category="reasoning", always_run=True),
    )

    registry.register_with_meta(
        "belief_metabolism", lambda: belief_metabolism,
        belief_metabolism.skill_meta
    )

    registry.register_with_meta(
        "sedimentation_retrieval", lambda: sedimentation_retrieval,
        SkillMeta(name="sedimentation_retrieval", description="Retrieves semantically relevant messages from other conversations via embedding similarity",
                  category="memory", always_run=True,
                  children=[
                      SkillMeta(name="similarity_search", description="Cosine similarity over 500 cross-conversation embeddings", category="memory"),
                      SkillMeta(name="token_budget", description="Limits sediment to configured token budget (default 2000)", category="memory"),
                  ]),
    )

    registry.register_with_meta(
        "diffractive_retrieval", lambda: diffractive_retrieval,
        SkillMeta(name="diffractive_retrieval", description="Perturbs conversation loops by retrieving semantically orthogonal Nomadic and Dormant context fragments",
                  category="memory", always_run=True,
                  children=[
                      SkillMeta(name="StagnationEvaluator", description="Calculates loop severity via pairwise similarity, novelty, and entropy to trigger intervention", category="memory"),
                      SkillMeta(name="NomadicRetriever", description="Retrieves semantically distant but structurally isomorphic memories from other threads", category="memory"),
                      SkillMeta(name="DormantFileRetriever", description="Retrieves inactive file context segments falling in the dynamic similarity Goldilocks zone", category="memory"),
                      SkillMeta(name="BudgetInterleaver", description="Interleaves retrieved items and enforces token context limits based on loop intensity", category="memory"),
                  ]),
    )

    registry.register_with_meta(
        "homeostatic_regulator", lambda: homeostatic_regulator,
        SkillMeta(name="homeostatic_regulator", description="Maps conversational metrics to allostatic regimes and recommends generator parameters",
                  category="reasoning", always_run=True,
                  children=[
                      SkillMeta(name="allostatic_parameter_adjuster", description="Computes offsets for temperature, presence penalty, and frequency penalty", category="reasoning"),
                      SkillMeta(name="regime_diagnostician", description="Evaluates conversational metrics to determine homeostatic state flags", category="reasoning"),
                  ]),
    )

    registry.register_with_meta(
        "llm_client", lambda: llm_module,
        SkillMeta(name="llm_client", description="Sends messages to the language model and returns the response",
                  category="action", always_run=True,
                  children=[
                      SkillMeta(name="llm_router", description="Manages model pools, fallback rules, and automatic rotation under rate limits", category="action"),
                      SkillMeta(name="rate_limit_handler", description="Intercepts 429/503 HTTP responses to apply provider cooling periods", category="action"),
                  ]),
    )

    system_prompt_text = _build_system_content(identity_data, registry)
    system_prompt_tokens = estimate_tokens(system_prompt_text)
    logger.info(f"System prompt tokens: {system_prompt_tokens}")

    pipeline_order = config.get("pipeline", {}).get(
        "modules",
        ["embedder", "structural_scorer", "perception", "web_retrieval", "conversation_metrics", "context_collector",
         "consolidation_checkpoint", "sedimentation_retrieval", "diffractive_retrieval", "belief_metabolism",
         "prompt_assembler", "homeostatic_regulator", "llm_client"],
    )
    pipeline_modules = registry.resolve_pipeline(pipeline_order)


    def log_pipeline_error(module_name: str, error: Exception, payload: dict):
        error_repo.log_error(
            module=module_name,
            error=error,
            context={"input": payload.get("content", "")[:500]},
        )

    pipeline = ProcessingPipeline(
        modules=pipeline_modules,
        error_handler=log_pipeline_error,
    )

    app.state.config = config
    app.state.agent_name = agent_name
    app.state.message_repo = message_repo
    app.state.error_repo = error_repo
    app.state.metrics_repo = metrics_repo
    app.state.conversation_repo = conversation_repo
    app.state.perception_repo = perception_repo
    app.state.perception_module = perception_module
    app.state.checkpoint_repo = checkpoint_repo
    app.state.belief_repo = belief_repo
    app.state.semantic_knot_repo = semantic_knot_repo
    app.state.belief_metabolism = belief_metabolism
    app.state.registry = registry
    app.state.pipeline = pipeline
    app.state.pipeline_order = pipeline_order
    app.state.embedder = embedder
    app.state.llm_provider = provider
    app.state.structural_provider = structural_provider
    app.state.system_prompt_tokens = system_prompt_tokens

    # Background tasks engine
    background_llm_cfg = config.get("background_llm", {})
    vision_llm_cfg = config.get("vision_llm", {})

    background_provider = None

    if background_llm_cfg.get("models") or background_llm_cfg.get("model"):
        try:
            background_provider = _create_provider_from_config(background_llm_cfg)
            logger.info(f"Background model: {background_llm_cfg.get('models') or background_llm_cfg.get('model')}")
        except Exception:
            logger.warning("Failed to initialize background provider, using primary")
            background_provider = provider



    background_engine = BackgroundTaskEngine(
        provider=background_provider or provider,
        vision_provider=vision_provider,
    )
    background_engine.register(GenerateTitleAction())
    background_engine.register(SummarizeAction())
    background_engine.register(ConsolidateAction())
    background_engine.register(DocumentCollisionAction())
    background_engine.register(SemanticKnotAction())

    app.state.background_engine = background_engine
    app.state.background_provider = background_provider
    app.state.vision_provider = vision_provider

    logger.info("Background task engine initialized with actions: %s", background_engine.list_actions())

    # Start background startup scheduler for resumption and belief metabolism catch-up
    from backend.core.scheduler import BackgroundStartupScheduler
    from backend.api.routes import _process_and_summarize_file
    scheduler = BackgroundStartupScheduler(app.state, _process_and_summarize_file)
    app.state.startup_scheduler = scheduler
    scheduler.start()

    logger.info("All modules initialized. Server ready.")
    yield
    logger.info("Shutting down.")


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

    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=False,
    )
