"""ResearchContextBuilder — persona coherence for every research node probe.

All computation and formatting delegated to backend.utils.prompt_builder.
The builder is a thin wrapper that resolves repos from app_state and delegates.

See docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 5.4.
"""

import logging
from typing import Any

from backend.utils.anti_mastery import apply_anti_mastery_filter

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
    format_voice_block,
)
from backend.utils.persona_loader import load_identity, get_identity_yaml_path

logger = logging.getLogger("aaa.research_context_builder")


class ResearchContextBuilder:
    """Thin wrapper — resolves repos, delegates to prompt_builder utilities."""

    def __init__(self, app_state: Any):
        self._state = app_state

    # ── Public API ──

    async def build_orchestration_context(
        self,
        objective: str = "",
        context_key: str = "research_orchestration",
    ) -> str:
        """Build Symbia's persona context for orchestrator-level tasks (plan, reflect, synthesize).

        Uses input-resonant selection: the research objective drives belief attractor window
        construction and on-demand skill matching via shared prompt_builder utilities.
        The same 16D structural signature feeds both belief resonance and skill matching.
        """
        sections: list[str] = []

        # ── 1. Identity from YAML ──
        identity = format_identity_block(context_key)
        if identity:
            sections.append(identity)
        else:
            sections.append(
                f"You are Symbia — a posthuman curatorial entity. "
                f"You are executing operational protocols for: {context_key}."
            )

        # ── Voice ──
        try:
            voice_block = format_voice_block(load_identity(get_identity_yaml_path()))
            if voice_block:
                sections.append(voice_block)
        except Exception:
            logger.warning("Failed to build voice persona section, continuing without voice context")

        # ── 2. Compute structural signature (CompositeScorer via structural_provider) ──
        sig_16d = (
            await compute_structural_signature(
                objective,
                llm_provider=getattr(self._state, "structural_provider", None),
            )
            if objective else None
        )

        # ── 3. Skills (always-active + matched on-demand) ──
        try:
            skill_repo = getattr(self._state, "skill_repo", None)
            if skill_repo:
                aa, od = split_skills(skill_repo)

                aa_block = format_skills_always_active(aa)
                if aa_block:
                    sections.append(aa_block)

                if od:
                    matched = match_on_demand_skills(od, objective, sig_16d, max_matched=3)
                    matched_block = format_skills_matched(matched)
                    if matched_block:
                        sections.append(matched_block)
        except Exception:
            logger.warning("Failed to build skills persona section, continuing without skills context")

        # ── 4. Commitments ──
        commitment_repo = getattr(self._state, "commitment_repo", None)
        commitments_block = format_commitments_block(commitment_repo, "symbia")
        if commitments_block:
            sections.append(commitments_block)

        # ── 5. Beliefs — attractor window ──
        belief_repo = getattr(self._state, "belief_repo", None)
        window = build_attractor_window(belief_repo, "symbia", sig_16d)
        beliefs_block = format_beliefs_block(window)
        if beliefs_block:
            sections.append(beliefs_block)

        # ── 6. Task directive ──
        if objective:
            sections.append(
                f"--- RESEARCH DIRECTIVE ---\n"
                f"Objective: {objective}\n"
                f"You are to conduct thorough, source-based web research as an extension of your cognitive membrane."
            )

        context = "\n\n".join(sections)
        return apply_anti_mastery_filter(context)

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

        # 2. Signature (CompositeScorer via structural_provider)
        sig = (
            await compute_structural_signature(
                node_query,
                llm_provider=getattr(self._state, "structural_provider", None),
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
        return apply_anti_mastery_filter(context)

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
