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

    sediment_budget = os.environ.get("AAA_SEDIMENT_TOKEN_BUDGET")
    if sediment_budget is not None:
        config.setdefault("sedimentation", {})["sediment_token_budget"] = int(sediment_budget)

    sediment_count = os.environ.get("AAA_SEDIMENT_COUNT")
    if sediment_count is not None:
        config.setdefault("sedimentation", {})["sediment_count"] = int(sediment_count)

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
