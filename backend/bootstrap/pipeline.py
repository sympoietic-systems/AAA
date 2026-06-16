"""Pipeline construction and skill registration.

Extracted from backend/main.py.
"""

import logging

logger = logging.getLogger(__name__)


def _register_skills(registry, embedder, modules: dict, belief_metabolism, llm_module):
    """Register all skill modules into the pipeline registry."""
    from backend.app_factory import register_all
    register_all(registry, embedder, modules, belief_metabolism, llm_module)


def _build_pipeline(config: dict, registry, repos: dict, modules: dict):
    """Build the ProcessingPipeline from the registry with the configured order."""
    pipeline_order = config.get("pipeline", {}).get(
        "modules",
        [
            "embedder",
            "structural_scorer",
            "perception",
            "rhizome_web_probe",
            "web_retrieval",
            "conversation_metrics",
            "trait_computer",
            "expertise_engine",
            "commitment_store",
            "context_collector",
            "consolidation_checkpoint",
            "sedimentation_retrieval",
            "diffractive_retrieval",
            "belief_metabolism",
            "skill_activator",
            "skill_workshop",
            "prompt_assembler",
            "homeostatic_regulator",
            "llm_client",
        ],
    )
    pipeline_modules = registry.resolve_pipeline(pipeline_order)

    def log_pipeline_error(module_name: str, error: Exception, payload: dict):
        repos["error_repo"].log_error(
            module=module_name,
            error=error,
            context={"input": payload.get("content", "")[:500]},
        )

    from backend.metabolisation.pipeline import ProcessingPipeline
    return (
        ProcessingPipeline(
            modules=pipeline_modules,
            error_handler=log_pipeline_error,
        ),
        pipeline_order,
    )
