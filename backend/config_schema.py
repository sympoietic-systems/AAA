"""Declarative environment-variable override schema.

Provides an EnvOverride dataclass so all AAA_* env-var overrides are
defined in one place rather than scattered through config.py.

Usage in config.py:
    from backend.config_schema import ENV_OVERRIDES
    for ov in ENV_OVERRIDES:
        ov.apply(config)
"""

from dataclasses import dataclass, field
from typing import Any, Callable
import os


@dataclass
class EnvOverride:
    """Describes how an environment variable overrides a config key.

    Args:
        env_var:   The environment variable name (e.g. "AAA_LLM_MODEL").
        section:   The top-level config section (e.g. "llm").
        key:       The key within that section (e.g. "model").
        parser:    Callable to transform the string value. Default: str.
        default:   Fallback behaviour description (unused at runtime; documentation only).
    """

    env_var: str
    section: str
    key: str
    parser: Callable[[str], Any] = str

    def apply(self, config: dict) -> None:
        """Read env_var and, if set, write parsed value into config[section][key]."""
        raw = os.environ.get(self.env_var)
        if raw is None:
            return
        try:
            config.setdefault(self.section, {})[self.key] = self.parser(raw)
        except (ValueError, TypeError):
            pass  # Malformed env value → skip (keep config-file default)


# ── Parser helpers ─────────────────────────────────────────────────────

def _parse_bool(v: str) -> bool:
    return v.lower() in ("true", "1", "yes")


def _parse_int(v: str) -> int:
    return int(v)


def _parse_float(v: str) -> float:
    return float(v)


def _parse_list(v: str) -> list[str]:
    return [m.strip() for m in v.split(",") if m.strip()]


# ── All environment-variable overrides ─────────────────────────────────

ENV_OVERRIDES: list[EnvOverride] = [
    # ── Core ──
    EnvOverride("AAA_LLM_MODEL", "llm", "model"),
    EnvOverride("AAA_LLM_MODELS", "llm", "models", _parse_list),
    EnvOverride("AAA_LLM_PROVIDER", "llm", "provider"),
    EnvOverride("AAA_LLM_API_BASE", "llm", "api_base"),
    EnvOverride("AAA_DB_PATH", "database", "path"),
    EnvOverride("AAA_IDENTITY_PATH", "personality", "path"),
    EnvOverride("AAA_SERVER_HOST", "server", "host"),
    EnvOverride("AAA_SERVER_PORT", "server", "port", _parse_int),

    # ── Embedding ──
    EnvOverride("AAA_EMBEDDING_MODEL", "embedding", "model"),
    EnvOverride("AAA_EMBEDDING_DEVICE", "embedding", "device"),
    EnvOverride("AAA_EMBEDDING_CACHE_DIR", "embedding", "cache_dir"),
    EnvOverride("AAA_EMBEDDING_OFFLINE", "embedding", "offline", _parse_bool),

    # ── Background LLM ──
    EnvOverride("AAA_BACKGROUND_MODEL", "background_llm", "model"),
    EnvOverride("AAA_BACKGROUND_MODELS", "background_llm", "models", _parse_list),
    EnvOverride("AAA_BACKGROUND_API_BASE", "background_llm", "api_base"),
    EnvOverride("AAA_BACKGROUND_FALLBACK_MODEL", "background_llm", "fallback_model"),

    # ── Structural LLM ──
    EnvOverride("AAA_STRUCTURAL_MODEL", "structural_llm", "model"),
    EnvOverride("AAA_STRUCTURAL_MODELS", "structural_llm", "models", _parse_list),
    EnvOverride("AAA_STRUCTURAL_API_BASE", "structural_llm", "api_base"),
    EnvOverride("AAA_STRUCTURAL_FALLBACK_MODEL", "structural_llm", "fallback_model"),

    # ── Vision LLM ──
    EnvOverride("AAA_VISION_MODEL", "vision_llm", "model"),
    EnvOverride("AAA_VISION_MODELS", "vision_llm", "models", _parse_list),
    EnvOverride("AAA_VISION_API_BASE", "vision_llm", "api_base"),
    EnvOverride("AAA_VISION_FALLBACK_MODEL", "vision_llm", "fallback_model"),

    # ── Context ──
    EnvOverride("AAA_CONTEXT_MAX_TOKENS", "context", "max_tokens", _parse_int),
    EnvOverride("AAA_CONTEXT_FLOATING_WINDOW", "context", "floating_window", _parse_int),
    EnvOverride("AAA_CONTEXT_CAVEMAN", "context", "caveman_enabled", _parse_bool),
    EnvOverride("AAA_CONTEXT_CONSOLIDATE_THRESHOLD", "context", "consolidate_threshold", _parse_int),

    # ── Sedimentation ──
    EnvOverride("AAA_SEDIMENT_TOKEN_BUDGET", "sedimentation", "sediment_token_budget", _parse_int),
    EnvOverride("AAA_SEDIMENT_COUNT", "sedimentation", "sediment_count", _parse_int),

    # ── Diffractive retrieval ──
    EnvOverride("AAA_DIFFRACTIVE_ENABLED", "diffractive_retrieval", "enabled", _parse_bool),
    EnvOverride("AAA_DIFFRACTIVE_TOKEN_BUDGET", "diffractive_retrieval", "token_budget", _parse_int),
    EnvOverride("AAA_DIFFRACTIVE_MAX_COUNT", "diffractive_retrieval", "max_diffractive_count", _parse_int),

    # ── Web retrieval ──
    EnvOverride("AAA_WEB_RETRIEVAL_ENABLED", "web_retrieval", "enabled", _parse_bool),
    EnvOverride("AAA_WEB_RETRIEVAL_AUTONOMOUS_ROUTING", "web_retrieval", "autonomous_routing", _parse_bool),

    # ── Structural signature ──
    EnvOverride("AAA_LLM_SCORER_ENABLED", "structural_signature", "llm_scorer_enabled", _parse_bool),

    # ── LLM thinking ──
    EnvOverride("AAA_LLM_THINKING", "llm", "thinking", lambda v: {"enabled": _parse_bool(v)}),
    EnvOverride("AAA_LLM_REASONING_EFFORT", "llm", "thinking", lambda v: {"effort": v}),

    # ── Daemon ──
    EnvOverride("AAA_DAEMON_ENABLED", "daemon", "enabled", _parse_bool),
    EnvOverride("AAA_DAEMON_CHECK_INTERVAL", "daemon", "check_interval", _parse_int),
    EnvOverride("AAA_DAEMON_IDLE_THRESHOLD", "daemon", "idle_threshold", _parse_int),
    EnvOverride("AAA_DAEMON_MIN_DREAM_INTERVAL", "daemon", "min_dream_interval", _parse_int),
    EnvOverride("AAA_DAEMON_MAX_DAILY_DREAMS", "daemon", "max_daily_dreams", _parse_int),
    EnvOverride("AAA_DAEMON_DRIFT_COEFFICIENT", "daemon", "drift_coefficient", _parse_float),
]
