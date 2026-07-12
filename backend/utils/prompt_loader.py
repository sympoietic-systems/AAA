"""Shared YAML prompt loader.

Provides a single utility for loading prompt YAML files with fallback defaults,
eliminating duplicated yaml.safe_load / Path / open boilerplate across modules.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Project root: backend/utils/prompt_loader.py → parent.parent = backend/
# Prompt files live under backend/prompts/
_PROMPTS_ROOT = Path(__file__).resolve().parent.parent / "prompts"


def _load_prompts_file(relative_path: str) -> dict[str, Any]:
    """Load a YAML prompt file, returning {} on failure."""
    path = _PROMPTS_ROOT / relative_path
    try:
        if not path.exists():
            logger.warning("Prompt file not found: %s", path)
            return {}
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning("Failed to load prompt file %s: %s", path, e)
        return {}


def get_prompt(relative_path: str, key: str, default: str = "") -> str:
    """Load a single prompt string from a YAML file.

    Args:
        relative_path: Path relative to backend/prompts/ (e.g. "dreams/resonance_guide.yaml")
        key: The YAML key to extract.
        default: Fallback string if the key is missing.

    Returns:
        The prompt string, or default if not found.
    """
    data = _load_prompts_file(relative_path)
    val = data.get(key, default)
    return val.strip() if isinstance(val, str) else default


def get_prompts_dict(relative_path: str) -> dict[str, Any]:
    """Load the entire prompt YAML file as a dict.

    Args:
        relative_path: Path relative to backend/prompts/ (e.g. "dreams/prompt_generator.yaml")

    Returns:
        The full YAML contents as a dict, or {} on failure.
    """
    return _load_prompts_file(relative_path)
