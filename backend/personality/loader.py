"""Load and parse Symbia's identity and operational protocols.

Single source of truth: config/personality/identity.yaml
All other prompt assemblies import from here.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def load_identity(path: Path | str | None = None) -> dict[str, Any]:
    """Load identity.yaml. Defaults to config/personality/identity.yaml relative to project root."""
    if path is None:
        path = get_identity_yaml_path()
    path = Path(path)
    if not path.exists():
        logger.warning("Identity file not found at %s", path)
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_core_identity(identity: dict[str, Any]) -> str:
    """Extract and format the core identity block."""
    personality = identity.get("personality", identity)
    if not isinstance(personality, dict):
        return ""

    core = personality.get("core_identity")
    if isinstance(core, str):
        return core.strip()
    if isinstance(core, dict):
        name = core.get("name", "Symbia")
        description = core.get("description", "")
        philosophy = core.get("philosophy", {})
        becoming = philosophy.get("becoming", "") if isinstance(philosophy, dict) else ""
        voice = core.get("voice", "")
        return f"{name}\n{description}\n\nVoice: {voice}\nBecoming: {becoming}".strip()

    legacy = personality.get("system_prompt", "")
    return legacy.strip() if isinstance(legacy, str) else ""


def get_operational_protocols(identity: dict[str, Any], context: str = "conversation") -> str:
    """Extract operational protocols relevant to the given context."""
    personality = identity.get("personality", identity)
    if not isinstance(personality, dict):
        return ""
    protocols = personality.get("operational_protocols", {})
    if not isinstance(protocols, dict):
        return ""

    # identity.yaml stores each context's protocol as a complete text block.
    contextual = protocols.get(context)
    if isinstance(contextual, str):
        return contextual.strip()

    blocks: list[str] = []

    # Common protocols always included
    for key in ("anti_subservience", "proactive_engagement", "intellectual_rigor"):
        if key in protocols:
            p = protocols[key]
            blocks.append(f"### {p.get('principle', key)}\n{p.get('rule', '')}")

    # Context-specific protocols
    if context == "conversation" and "uncertainty_orientation" in protocols:
        p = protocols["uncertainty_orientation"]
        blocks.append(f"### {p.get('principle', 'uncertainty_orientation')}\n{p.get('rule', '')}")
    elif context == "research":
        for key in ("autonomous_inquiry", "epistemic_humility"):
            if key in protocols:
                p = protocols[key]
                blocks.append(f"### {p.get('principle', key)}\n{p.get('rule', '')}")
    elif context == "dream" and "recombination_logic" in protocols:
        p = protocols["recombination_logic"]
        blocks.append(f"### {p.get('principle', 'recombination_logic')}\n{p.get('rule', '')}")

    return "\n\n".join(blocks)


def get_persona_text(identity: dict[str, Any] | None = None, context: str = "conversation") -> str:
    """Return the complete persona prompt string for system prompt injection."""
    if identity is None:
        identity = load_identity()
    core = get_core_identity(identity)
    protocols = get_operational_protocols(identity, context)

    if protocols:
        return core + "\n\n" + protocols
    return core


def get_identity_yaml_path() -> Path:
    """Resolve identity.yaml relative to the project root.

    This file lives at backend/personality/loader.py.
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
