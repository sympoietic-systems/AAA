import os
import re
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

CONFIG_DIR = Path(__file__).parent
DEFAULT_CONFIG_PATH = CONFIG_DIR / "config.yaml"


def _resolve_env(value: str) -> str:
    if isinstance(value, str):
        matches = re.findall(r"\$\{([^}]+)\}", value)
        for var_name in matches:
            var_value = os.environ.get(var_name, "")
            value = value.replace(f"${{{var_name}}}", var_value)
    return value


def _resolve_env_recursive(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _resolve_env_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env_recursive(v) for v in obj]
    if isinstance(obj, str):
        return _resolve_env(obj)
    return obj


def _apply_env_overrides(config: dict) -> dict:
    """Apply all AAA_* environment variable overrides using declarative schema."""
    from backend.config_schema import ENV_OVERRIDES

    for override in ENV_OVERRIDES:
        override.apply(config)

    # ── Thinking / effort overrides (nested dict, needs special handling) ──
    thinking_env = os.environ.get("AAA_LLM_THINKING")
    if thinking_env is not None:
        thinking_cfg = config.setdefault("llm", {}).setdefault("thinking", {})
        thinking_cfg["enabled"] = thinking_env.lower() in ("true", "1", "yes")

    effort_env = os.environ.get("AAA_LLM_REASONING_EFFORT")
    if effort_env is not None:
        thinking_cfg = config.setdefault("llm", {}).setdefault("thinking", {})
        thinking_cfg["effort"] = effort_env

    # ── API key resolution ──────────────────────────────────────────────
    provider = config.get("llm", {}).get("provider", "openrouter")
    provider_key_env = {
        "openrouter": "AAA_LLM_API_KEY",
        "deepseek": "AAA_DEEPSEEK_API_KEY",
    }

    api_key_env = provider_key_env.get(provider, "AAA_LLM_API_KEY")
    api_key = os.environ.get(api_key_env)
    if api_key:
        config.setdefault("llm", {})["api_key"] = api_key

    background_api_key = os.environ.get("AAA_BACKGROUND_API_KEY") or os.environ.get("AAA_LLM_API_KEY")
    if background_api_key:
        config.setdefault("background_llm", {})["api_key"] = background_api_key

    vision_api_key = os.environ.get("AAA_VISION_API_KEY") or os.environ.get("AAA_LLM_API_KEY")
    if vision_api_key:
        config.setdefault("vision_llm", {})["api_key"] = vision_api_key

    structural_api_key = (
        os.environ.get("AAA_STRUCTURAL_API_KEY")
        or os.environ.get("AAA_BACKGROUND_API_KEY")
        or os.environ.get("AAA_LLM_API_KEY")
    )
    if structural_api_key:
        config.setdefault("structural_llm", {})["api_key"] = structural_api_key

    # ── Provider-specific keys and API bases ─────────────────────────────
    google_api_key = os.environ.get("AAA_GOOGLE_API_KEY")
    google_keys = [k.strip() for k in google_api_key.split(",") if k.strip()] if google_api_key else []

    deepseek_api_key = os.environ.get("AAA_DEEPSEEK_API_KEY")
    deepseek_keys = [k.strip() for k in deepseek_api_key.split(",") if k.strip()] if deepseek_api_key else []

    openrouter_api_keys = os.environ.get("AAA_BACKGROUND_API_KEY") or os.environ.get("AAA_LLM_API_KEY")
    openrouter_keys = [k.strip() for k in openrouter_api_keys.split(",") if k.strip()] if openrouter_api_keys else []

    google_api_base = os.environ.get("AAA_GOOGLE_API_BASE")
    deepseek_api_base = os.environ.get("AAA_DEEPSEEK_API_BASE") or os.environ.get("AAA_LLM_API_BASE")

    for section in ("llm", "background_llm", "vision_llm", "structural_llm"):
        cfg = config.setdefault(section, {})
        if google_keys:
            cfg["google_keys"] = google_keys
        if deepseek_keys:
            cfg["deepseek_keys"] = deepseek_keys
        if openrouter_keys:
            cfg["openrouter_keys"] = openrouter_keys
        if google_api_base:
            cfg["google_api_base"] = google_api_base
        if deepseek_api_base:
            cfg["deepseek_api_base"] = deepseek_api_base

    # ── Propagate timeout to other LLM configs ──────────────────────────
    llm_timeout = config.get("llm", {}).get("timeout")
    if llm_timeout is not None:
        for section in ("background_llm", "vision_llm", "structural_llm"):
            cfg = config.setdefault(section, {})
            if "timeout" not in cfg:
                cfg["timeout"] = llm_timeout

    return config


def load_config(path: Path | None = None) -> dict:
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    config = _resolve_env_recursive(config)
    config = _apply_env_overrides(config)
    return config
