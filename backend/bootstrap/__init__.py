"""Application bootstrap modules.

Splits the original monolithic backend/main.py into focused,
testable modules for initialization, configuration, and lifecycle.
"""

from backend.bootstrap.providers import (
    PROVIDER_DEFAULTS,
    _create_provider,
    _create_llm_provider,
    _create_provider_from_config,
    _init_providers,
)
from backend.bootstrap.repositories import _init_repos
from backend.bootstrap.embedder import _init_embedder
from backend.bootstrap.modules import (
    _init_modules,
    _init_belief_engine,
    _load_identity,
)
from backend.bootstrap.pipeline import (
    _register_skills,
    _build_pipeline,
)
from backend.bootstrap.background import (
    _init_background_engine,
    _start_background_services,
)
from backend.bootstrap.lifecycle import lifespan, create_app

__all__ = [
    "PROVIDER_DEFAULTS",
    "_create_provider",
    "_create_llm_provider",
    "_create_provider_from_config",
    "_init_providers",
    "_init_repos",
    "_init_embedder",
    "_init_modules",
    "_init_belief_engine",
    "_load_identity",
    "_register_skills",
    "_build_pipeline",
    "_init_background_engine",
    "_start_background_services",
    "lifespan",
    "create_app",
]
