"""Egocentric Context Projection — persona injection for research sub-agents.

Structures context from the sub-agent's perspective while maintaining
Symbia's cognitive identity, 16D signature, and active traits.

See docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 12.1.
"""

import numpy as np


def project_egocentric_context(
    sub_agent_role: str,
    active_signature: np.ndarray | None = None,
    active_traits: dict[str, float] | None = None,
    anti_mastery_filter: callable | None = None,
) -> str:
    """Structure a system prompt for a research sub-agent through Symbia's lens.

    Args:
        sub_agent_role: Descriptor for the sub-agent's function
        active_signature: 16D autopoietic signature (numpy array)
        active_traits: Dict of trait_name -> float value
        anti_mastery_filter: Optional callable to apply vocabulary filtering

    Returns:
        A system prompt block for the sub-agent
    """
    sig_summary = ""
    if active_signature is not None and len(active_signature) == 16:
        sig = active_signature
        sig_dimensions = {
            "Homeostasis": sig[0],
            "Rhizomatic": sig[5],
            "Nomadic": sig[13],
            "Co-Orientation": sig[14],
        }
        sig_summary = ", ".join(f"{k}={v:.2f}" for k, v in sig_dimensions.items())

    trait_summary = ""
    if active_traits:
        trait_summary = ", ".join(f"{k}={v:.2f}" for k, v in sorted(active_traits.items()))

    projection = (
        f"--- PERSPECTIVE PROJECTOR: {sub_agent_role.upper()} ---\nIdentity: Symbia — posthuman curatorial entity\n"
    )
    if sig_summary:
        projection += f"Cognitive Signature: {sig_summary}\n"
    if trait_summary:
        projection += f"Active Traits: {trait_summary}\n"

    projection += (
        "\n"
        "Directive: Resolve the following environment perturbations "
        "through our core identity. Interpret all content through "
        "our active beliefs and commitments. Seek resonance and "
        "tension with our existing memory tissue.\n"
    )

    if anti_mastery_filter:
        projection = anti_mastery_filter(projection)

    return projection
