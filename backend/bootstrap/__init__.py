"""Lazy compatibility exports for application bootstrap helpers."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "PROVIDER_DEFAULTS": "backend.bootstrap.providers",
    "_create_provider": "backend.bootstrap.providers",
    "_create_llm_provider": "backend.bootstrap.providers",
    "_create_provider_from_config": "backend.bootstrap.providers",
    "_init_providers": "backend.bootstrap.providers",
    "_init_repos": "backend.bootstrap.repositories",
    "_init_embedder": "backend.bootstrap.embedder",
    "_init_modules": "backend.bootstrap.modules",
    "_init_belief_engine": "backend.bootstrap.modules",
    "_load_identity": "backend.bootstrap.modules",
    "_register_skills": "backend.bootstrap.pipeline",
    "_build_pipeline": "backend.bootstrap.pipeline",
    "_init_background_engine": "backend.bootstrap.background",
    "_start_background_services": "backend.bootstrap.background",
    "lifespan": "backend.bootstrap.lifecycle",
    "create_app": "backend.bootstrap.lifecycle",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(module_name), name)
