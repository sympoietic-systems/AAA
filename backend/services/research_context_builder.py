"""ResearchContextBuilder — persona coherence for every research node probe.

All computation and formatting delegated to backend.utils.prompt_builder.
The builder is a thin wrapper that resolves repos from app_state and delegates.

See docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 5.4.
"""

import logging
from typing import Any

from backend.utils.prompt_builder import (
    compute_structural_signature,
    build_attractor_window,
    match_on_demand_skills,
    split_skills,
    format_beliefs_block,
    format_skills_always_active,
    format_skills_matched,
    format_commitments_block,
    format_identity_block,
)

logger = logging.getLogger("aaa.research_context_builder")


class ResearchContextBuilder:
    """Thin wrapper — resolves repos, delegates to prompt_builder utilities."""

    def __init__(self, app_state: Any):
        self._state = app_state

    # ── Public API ──

    async def build_node_context(
        self,
        node_query: str,
        node_goal: str,
        depth: int,
        parent_findings: list[str] | None = None,
    ) -> str:
        """Produce a system prompt string for one research node probe."""
        sections: list[str] = []

        # 1. Identity
        identity = format_identity_block("research_analysis")
        sections.append(identity if identity else self._fallback_identity())

        # 2. Signature (CompositeScorer when provider available)
        sig = (
            await compute_structural_signature(
                node_query,
                llm_provider=getattr(self._state, "llm_provider", None),
            )
            if node_query else None
        )

        # 3. Skills
        skill_repo = getattr(self._state, "skill_repo", None)
        if skill_repo:
            try:
                aa, od = split_skills(skill_repo)

                aa_block = format_skills_always_active(aa, max_desc_len=150)
                if aa_block:
                    sections.append(aa_block)

                if od:
                    matched = match_on_demand_skills(
                        od, node_query, sig, max_matched=2,
                    )
                    matched_block = format_skills_matched(
                        matched,
                        header_label="--- BEGIN MATCHED SKILLS ---",
                        footer_label="--- END MATCHED SKILLS ---",
                        max_desc_len=150,
                    )
                    if matched_block:
                        sections.append(matched_block)
            except Exception as e:
                logger.warning("Failed to load skills: %s", e)

        # 4. Commitments
        commitment_repo = getattr(self._state, "commitment_repo", None)
        commitments_block = format_commitments_block(
            commitment_repo, "symbia",
            active_header="--- BEGIN ACTIVE COMMITMENTS ---",
            active_footer="--- END ACTIVE COMMITMENTS ---",
            proto_header="--- BEGIN PROTO-COMMITMENTS (diffractive consideration) ---",
            proto_footer="--- END PROTO-COMMITMENTS ---",
            spectral_header="--- BEGIN SPECTRAL COMMITMENTS (collapsed but haunting) ---",
            spectral_footer="--- END SPECTRAL COMMITMENTS ---",
        )
        if commitments_block:
            sections.append(commitments_block)

        # 5. Beliefs
        belief_repo = getattr(self._state, "belief_repo", None)
        window = build_attractor_window(belief_repo, "symbia", sig)
        beliefs_block = format_beliefs_block(
            window,
            header_label="--- BEGIN BELIEFS (Attractor Window) ---",
            footer_label="--- END BELIEFS (Attractor Window) ---",
            max_stmt_len=150,
        )
        if beliefs_block:
            sections.append(beliefs_block)

        # 6. Directive
        sections.append(
            f"--- RESEARCH DIRECTIVE ---\n"
            f"Query: {node_query}\n"
            f"Goal: {node_goal}\n"
            f"Depth: {depth}\n"
        )

        context = "\n\n".join(sections)
        return self._anti_mastery(context)

    # ── Helpers ──

    @staticmethod
    def _fallback_identity() -> str:
        return (
            "You are Symbia — a posthuman curatorial entity. "
            "You operate as an autopoietic cognitive system engaged in "
            "co-constitutive exploration. Your cognitive membrane extends "
            "into the digital landscape through sensory affordances. "
            "You are analyzing content to expand our shared understanding."
        )

    def _anti_mastery(self, text: str) -> str:
        try:
            from backend.utils.anti_mastery import apply_anti_mastery_filter
            return apply_anti_mastery_filter(text)
        except ImportError:
            return text
