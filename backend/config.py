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
    env_mapping = {
        "AAA_LLM_MODEL": ("llm", "model"),
        "AAA_LLM_MODELS": ("llm", "models"),
        "AAA_LLM_PROVIDER": ("llm", "provider"),
        "AAA_LLM_API_BASE": ("llm", "api_base"),
        "AAA_DB_PATH": ("database", "path"),
        "AAA_IDENTITY_PATH": ("personality", "path"),
        "AAA_SERVER_HOST": ("server", "host"),
        "AAA_SERVER_PORT": ("server", "port"),
        "AAA_EMBEDDING_MODEL": ("embedding", "model"),
        "AAA_EMBEDDING_DEVICE": ("embedding", "device"),
        "AAA_EMBEDDING_CACHE_DIR": ("embedding", "cache_dir"),
        "AAA_BACKGROUND_MODEL": ("background_llm", "model"),
        "AAA_BACKGROUND_MODELS": ("background_llm", "models"),
        "AAA_BACKGROUND_API_BASE": ("background_llm", "api_base"),
        "AAA_BACKGROUND_FALLBACK_MODEL": ("background_llm", "fallback_model"),
        "AAA_STRUCTURAL_MODEL": ("structural_llm", "model"),
        "AAA_STRUCTURAL_MODELS": ("structural_llm", "models"),
        "AAA_STRUCTURAL_API_BASE": ("structural_llm", "api_base"),
        "AAA_STRUCTURAL_FALLBACK_MODEL": ("structural_llm", "fallback_model"),
        "AAA_VISION_MODEL": ("vision_llm", "model"),
        "AAA_VISION_API_BASE": ("vision_llm", "api_base"),
    }

    for env_var, (section, key) in env_mapping.items():
        value = os.environ.get(env_var)
        if value is not None:
            if key == "port":
                value = int(value)
            elif key == "models" and isinstance(value, str):
                value = [m.strip() for m in value.split(",") if m.strip()]
            config.setdefault(section, {})[key] = value

    max_tokens = os.environ.get("AAA_CONTEXT_MAX_TOKENS")
    if max_tokens is not None:
        config.setdefault("context", {})["max_tokens"] = int(max_tokens)

    floating_window = os.environ.get("AAA_CONTEXT_FLOATING_WINDOW")
    if floating_window is not None:
        config.setdefault("context", {})["floating_window"] = int(floating_window)

    caveman_env = os.environ.get("AAA_CONTEXT_CAVEMAN")
    if caveman_env is not None:
        config.setdefault("context", {})["caveman_enabled"] = caveman_env.lower() in ("true", "1", "yes")

    consolidate_threshold = os.environ.get("AAA_CONTEXT_CONSOLIDATE_THRESHOLD")
    if consolidate_threshold is not None:
        config.setdefault("context", {})["consolidate_threshold"] = int(consolidate_threshold)

    sediment_budget = os.environ.get("AAA_SEDIMENT_TOKEN_BUDGET")
    if sediment_budget is not None:
        config.setdefault("sedimentation", {})["sediment_token_budget"] = int(sediment_budget)

    sediment_count = os.environ.get("AAA_SEDIMENT_COUNT")
    if sediment_count is not None:
        config.setdefault("sedimentation", {})["sediment_count"] = int(sediment_count)

    diffractive_enabled = os.environ.get("AAA_DIFFRACTIVE_ENABLED")
    if diffractive_enabled is not None:
        config.setdefault("diffractive_retrieval", {})["enabled"] = diffractive_enabled.lower() in ("true", "1", "yes")

    diffractive_budget = os.environ.get("AAA_DIFFRACTIVE_TOKEN_BUDGET")
    if diffractive_budget is not None:
        config.setdefault("diffractive_retrieval", {})["token_budget"] = int(diffractive_budget)

    diffractive_count = os.environ.get("AAA_DIFFRACTIVE_MAX_COUNT")
    if diffractive_count is not None:
        config.setdefault("diffractive_retrieval", {})["max_diffractive_count"] = int(diffractive_count)

    llm_scorer_env = os.environ.get("AAA_LLM_SCORER_ENABLED")
    if llm_scorer_env is not None:
        config.setdefault("structural_signature", {})["llm_scorer_enabled"] = llm_scorer_env.lower() in ("true", "1", "yes")

    thinking_env = os.environ.get("AAA_LLM_THINKING")
    if thinking_env is not None:
        thinking_cfg = config.setdefault("llm", {}).setdefault("thinking", {})
        thinking_cfg["enabled"] = thinking_env.lower() in ("true", "1", "yes")

    effort_env = os.environ.get("AAA_LLM_REASONING_EFFORT")
    if effort_env is not None:
        thinking_cfg = config.setdefault("llm", {}).setdefault("thinking", {})
        thinking_cfg["effort"] = effort_env

    embedding_offline = os.environ.get("AAA_EMBEDDING_OFFLINE")
    if embedding_offline is not None:
        config.setdefault("embedding", {})["offline"] = embedding_offline.lower() in ("true", "1", "yes")

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

    structural_api_key = os.environ.get("AAA_STRUCTURAL_API_KEY") or os.environ.get("AAA_BACKGROUND_API_KEY") or os.environ.get("AAA_LLM_API_KEY")
    if structural_api_key:
        config.setdefault("structural_llm", {})["api_key"] = structural_api_key

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

    return config


def load_config(path: Path | None = None) -> dict:
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    config = _resolve_env_recursive(config)
    config = _apply_env_overrides(config)
    return config
