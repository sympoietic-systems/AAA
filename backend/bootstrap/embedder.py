"""Embedder initialization.

Extracted from backend/main.py.
"""

import logging

logger = logging.getLogger(__name__)


def _init_embedder(config: dict):
    """Create and pre-load the sentence-transformers embedding model."""
    embed_cfg = config.get("embedding", {})
    from backend.modules.embedder import EmbedderModule

    embedder = EmbedderModule(
        model_name=embed_cfg.get("model", "all-MiniLM-L6-v2"),
        device=embed_cfg.get("device", "cpu"),
        offline=embed_cfg.get("offline", True),
        cache_dir=embed_cfg.get("cache_dir"),
    )
    logger.info("Pre-loading embedding model: %s", embed_cfg.get("model"))
    embedder.service.preload()
    return embedder
