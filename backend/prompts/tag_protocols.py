"""Unified Autopoietic Tag Protocols & Inscriptional Grammar.

Consolidates the procedural tag specifications into an ultra-compact,
ontologically rigorous block loaded directly from:
    backend/prompts/personality/tag_protocols.yaml
"""

from backend.utils.prompt_loader import get_prompt


def get_tag_protocols_prompt() -> str:
    """Return the compact tag protocols block loaded from YAML."""
    return get_prompt(
        "personality/tag_protocols.yaml",
        "tag_protocols_block",
        default="",
    )


def get_skill_blueprint_prompt() -> str:
    """Return the canonical 5-phase skill blueprint specification loaded from YAML."""
    return get_prompt(
        "personality/tag_protocols.yaml",
        "skill_blueprint_specification",
        default="",
    )

