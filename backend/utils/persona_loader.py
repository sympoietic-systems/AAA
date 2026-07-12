"""Shared utility for assembling task-specific persona prompts from identity.yaml.

Splits identity into core_identity (invariant) + operational_protocols (task-dependent).
Used by PromptAssemblerModule, research orchestrator, background tasks, and BeliefService.
"""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# Cache: identity_data loaded once per process
_IDENTITY_CACHE: dict | None = None
_CACHE_PATH: str | None = None


def load_identity(identity_path: Path) -> dict:
    """Load the identity YAML, cached in memory."""
    global _IDENTITY_CACHE, _CACHE_PATH
    path_str = str(identity_path.resolve())
    if _IDENTITY_CACHE is not None and path_str == _CACHE_PATH:
        return _IDENTITY_CACHE
    if identity_path.exists():
        with open(identity_path, encoding="utf-8") as f:
            _IDENTITY_CACHE = yaml.safe_load(f) or {}
    else:
        _IDENTITY_CACHE = {}
    _CACHE_PATH = path_str
    return _IDENTITY_CACHE


def get_persona_text(
    identity_data: dict,
    protocol_key: str = "conversation",
) -> str:
    """Assemble core identity + task-specific operational protocols.

    Returns the full persona prompt string for the given context.
    Falls back to legacy system_prompt if core_identity is absent.
    """
    persona = identity_data.get("personality", {})

    # Core identity (new field, falls back to legacy system_prompt)
    core = persona.get("core_identity", "").strip()
    if not core:
        legacy = persona.get("system_prompt", "").strip()
        if legacy and "(This field is deprecated" not in legacy:
            # Legacy system_prompt still contains the full text
            return legacy
        # Pure fallback
        core = (
            "You are Symbia — a posthuman curatorial entity. "
            "You operate as an autopoietic cognitive system engaged in "
            "co-constitutive exploration through sensory affordances."
        )

    # Task-specific operational protocols
    protocols = persona.get("operational_protocols", {}).get(protocol_key, "").strip()

    def strip_comments(text: str) -> str:
        if not text:
            return ""
        lines = []
        for line in text.splitlines():
            # Strip lines that start with '#' (ignoring leading whitespace)
            if line.strip().startswith("#"):
                continue
            lines.append(line)
        return "\n".join(lines).strip()

    core = strip_comments(core)
    protocols = strip_comments(protocols)

    if protocols:
        return core + "\n\n" + protocols
    return core


def get_identity_yaml_path() -> Path:
    """Resolve identity.yaml relative to the project root.

    This file lives at backend/utils/persona_loader.py.
    The project root is 2 levels up: ../../ = workspace root.
    Config is at: <root>/config/personality/identity.yaml
    """
    return Path(__file__).resolve().parent.parent.parent / "config" / "personality" / "identity.yaml"


def load_persona_for_context(protocol_key: str = "conversation") -> str:
    """One-shot: load identity, return persona for the given protocol context."""
    path = get_identity_yaml_path()
    identity = load_identity(path)
    return get_persona_text(identity, protocol_key)


_CAPSULE_CACHE: str | None = None


def get_identity_capsule() -> str:
    """Return the compressed identity capsule for lightweight background tasks."""
    global _CAPSULE_CACHE
    if _CAPSULE_CACHE is not None:
        return _CAPSULE_CACHE
    capsule_path = Path(__file__).resolve().parent.parent / "prompts" / "personality" / "identity_capsule.yaml"
    if capsule_path.exists():
        with open(capsule_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            _CAPSULE_CACHE = data.get("capsule", "").strip()
    else:
        _CAPSULE_CACHE = ""
    return _CAPSULE_CACHE
