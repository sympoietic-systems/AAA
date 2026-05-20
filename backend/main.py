import logging
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.config import load_config
from backend.core.pipeline import ProcessingPipeline
from backend.modules.context_collector import ContextCollectorModule
from backend.modules.embedder import EmbedderModule
from backend.modules.llm_client import (
    LLMClientModule,
    OpenAICompatibleProvider,
    OpenRouterProvider,
)
from backend.personality.assembler import PromptAssemblerModule
from backend.skills.metadata import SkillMeta
from backend.skills.registry import SkillRegistry
from backend.storage.database import get_db_path, init_db
from backend.storage.repository import ErrorLogRepository, MessageRepository

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = load_config()

    db_path = config.get("database", {}).get("path", "data/aaa.db")
    full_db_path = get_db_path(db_path)
    init_db(str(full_db_path))
    logger.info(f"Database initialized at {full_db_path}")

    message_repo = MessageRepository(str(full_db_path))
    error_repo = ErrorLogRepository(str(full_db_path))

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

    ctx_cfg = config.get("context", {})
    context_collector = ContextCollectorModule(
        message_repo=message_repo,
        max_history=ctx_cfg.get("max_history", 20),
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

    registry = SkillRegistry()
    registry.register_with_meta(
        "embedder", lambda: embedder,
        SkillMeta(name="embedder", description="Encodes text into vector embeddings",
                  category="perception", always_run=True),
    )
    registry.register_with_meta(
        "context_collector", lambda: context_collector,
        SkillMeta(name="context_collector", description="Gathers conversation history",
                  category="memory", always_run=True),
    )

    prompt_assembler = PromptAssemblerModule(
        identity_path=identity_path,
        skill_registry=registry,
    )
    registry.register_with_meta(
        "prompt_assembler", lambda: prompt_assembler,
        SkillMeta(name="prompt_assembler", description="Composes system prompt from identity and skills",
                  category="reasoning", always_run=True),
    )

    registry.register_with_meta(
        "llm_client", lambda: llm_module,
        SkillMeta(name="llm_client", description="Sends messages to the language model and returns the response",
                  category="action", always_run=True),
    )

    pipeline_order = config.get("pipeline", {}).get(
        "modules",
        ["embedder", "context_collector", "prompt_assembler", "llm_client"],
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
    app.state.registry = registry
    app.state.pipeline = pipeline
    app.state.pipeline_order = pipeline_order
    app.state.embedder = embedder

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

    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
