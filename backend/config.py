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
    }

    for env_var, (section, key) in env_mapping.items():
        value = os.environ.get(env_var)
        if value is not None:
            if key == "port":
                value = int(value)
            config.setdefault(section, {})[key] = value

    thinking_env = os.environ.get("AAA_LLM_THINKING")
    if thinking_env is not None:
        thinking_cfg = config.setdefault("llm", {}).setdefault("thinking", {})
        thinking_cfg["enabled"] = thinking_env.lower() in ("true", "1", "yes")

    effort_env = os.environ.get("AAA_LLM_REASONING_EFFORT")
    if effort_env is not None:
        thinking_cfg = config.setdefault("llm", {}).setdefault("thinking", {})
        thinking_cfg["effort"] = effort_env

    provider = config.get("llm", {}).get("provider", "openrouter")
    provider_key_env = {
        "openrouter": "AAA_LLM_API_KEY",
        "deepseek": "AAA_DEEPSEEK_API_KEY",
    }

    api_key_env = provider_key_env.get(provider, "AAA_LLM_API_KEY")
    api_key = os.environ.get(api_key_env)
    if api_key:
        config.setdefault("llm", {})["api_key"] = api_key

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
