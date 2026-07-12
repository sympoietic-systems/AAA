"""AAA Backend — Application entry point.

Orchestrates application creation through the bootstrap package.
See backend/bootstrap/ for individual initialization modules:
  - providers.py   — LLM provider factory functions
  - repositories.py — Database and repository initialization
  - embedder.py    — Sentence-transformers embedding model
  - modules.py     — Pipeline module construction
  - pipeline.py    — Pipeline registry and skill wiring
  - background.py  — Background task engine and daemon
  - lifecycle.py   — FastAPI lifespan and app factory
"""

import os

from dotenv import load_dotenv

# ── Load .env BEFORE any module imports ──────────────────────────────
# Modules like deps.py and auth.py read env vars at import time (module-level).
# If load_dotenv() runs after those imports, AAA_PASSWORD etc. are empty.
load_dotenv()

# Disable Windows Console QuickEdit mode to prevent suspension when clicking in terminal
from backend.utils.console import disable_quick_edit  # noqa: E402

disable_quick_edit()

# Bypass system registry proxy settings
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"
for k in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]:
    if k in os.environ:
        del os.environ[k]

# ── Re-export from bootstrap for backward compatibility ────────────────
# External scripts and tests depend on these being importable from backend.main
from backend.bootstrap.lifecycle import create_app  # noqa: E402
from backend.bootstrap.modules import (  # noqa: E402, F401
    _init_belief_engine,
)
from backend.bootstrap.providers import (  # noqa: E402, F401
    _create_llm_provider,
    _create_provider_from_config,
    _init_providers,
)

# ── Module-level FastAPI app instance ──────────────────────────────────
app = create_app()

if __name__ == "__main__":
    import uvicorn

    from backend.config import load_config

    try:
        config = load_config()
        server_cfg = config.get("server", {})
        host = server_cfg.get("host", "127.0.0.1")
        port = int(server_cfg.get("port", 8499))
    except Exception:
        host = os.environ.get("AAA_SERVER_HOST", "127.0.0.1")
        port = int(os.environ.get("AAA_SERVER_PORT", 8499))

    uvicorn.run("backend.main:app", host=host, port=port, reload=False)
