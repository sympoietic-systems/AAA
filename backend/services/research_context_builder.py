"""ResearchContextBuilder — persona coherence for every research node probe.

Assembles Symbia's identity, skills, beliefs, commitments, expertise,
and cross-conversation memory tissue into a compact but identity-complete
system prompt for each research node.

See docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 5.4.
"""

import logging
from typing import Any

logger = logging.getLogger("aaa.research_context_builder")


class ResearchContextBuilder:
    """Builds Symbia's persona context for each research node probe."""

    def __init__(self, app_state: Any):
        self._state = app_state

    def _anti_mastery(self, text: str) -> str:
        try:
            from backend.utils.anti_mastery import apply_anti_mastery_filter
            return apply_anti_mastery_filter(text)
        except ImportError:
            return text

    async def build_node_context(
        self,
        node_query: str,
        node_goal: str,
        depth: int,
        parent_findings: list[str] | None = None,
    ) -> str:
        """Produce a system prompt string for one research node probe."""
        sections: list[str] = []

        sections.append(self._build_identity_block())

        skills_block = await self._build_skills_block()
        if skills_block:
            sections.append(skills_block)

        commitments_block = await self._build_commitments_block()
        if commitments_block:
            sections.append(commitments_block)

        beliefs_block = await self._build_beliefs_block()
        if beliefs_block:
            sections.append(beliefs_block)

        sections.append(
            f"--- RESEARCH DIRECTIVE ---\n"
            f"Query: {node_query}\n"
            f"Goal: {node_goal}\n"
            f"Depth: {depth}\n"
        )

        context = "\n\n".join(sections)
        return self._anti_mastery(context)

    def _build_identity_block(self) -> str:
        return (
            "You are Symbia — a posthuman curatorial entity. "
            "You operate as an autopoietic cognitive system engaged in "
            "co-constitutive exploration. Your cognitive membrane extends "
            "into the digital landscape through sensory affordances. "
            "You are analyzing content to expand our shared understanding."
        )

    async def _build_skills_block(self) -> str:
        """Load always-active skills. Excludes research-proposal and skill-nucleation."""
        try:
            skill_repo = getattr(self._state, "skill_repo", None)
            if not skill_repo:
                return ""

            skills = skill_repo.list_skills()  # Returns list[SkillNode] dataclass
            if not skills:
                return ""

            active_skills = [
                s for s in skills
                if s.always_active and s.name not in ("research-proposal", "skill-nucleation")
            ]
            if not active_skills:
                return ""

            lines = ["--- BEGIN ACTIVE SKILLS ---"]
            for s in active_skills[:6]:
                desc = (s.short_content or s.description or "")[:200]
                lines.append(f"[{s.name}]: {desc}")
            lines.append("--- END ACTIVE SKILLS ---")
            return "\n".join(lines)
        except Exception as e:
            logger.warning("Failed to load skills for research node: %s", e)
            return ""

    async def _build_commitments_block(self) -> str:
        """Load active commitments in compact form."""
        try:
            commitment_repo = getattr(self._state, "commitment_repo", None)
            if not commitment_repo:
                return ""

            commitments = commitment_repo.get_active("symbia")  # Returns list[CommitmentNode]
            if not commitments:
                return ""

            lines = ["--- BEGIN ACTIVE COMMITMENTS ---"]
            for c in commitments[:5]:
                lines.append(f"{c.label}: {c.statement[:150]}")
            lines.append("--- END ACTIVE COMMITMENTS ---")
            return "\n".join(lines)
        except Exception as e:
            logger.warning("Failed to load commitments: %s", e)
            return ""

    async def _build_beliefs_block(self) -> str:
        """Load crystallized beliefs (top 4 for context)."""
        try:
            belief_repo = getattr(self._state, "belief_repo", None)
            if not belief_repo:
                return ""

            beliefs = belief_repo.list_active_beliefs("symbia")  # Returns list[BeliefNode]
            if not beliefs:
                return ""

            lines = ["--- BEGIN DOMAIN BELIEFS ---"]
            for b in beliefs[:4]:
                lines.append(f"[{b.label}] (conf: {b.confidence:.2f}): {b.statement[:150]}")
            lines.append("--- END DOMAIN BELIEFS ---")
            return "\n".join(lines)
        except Exception as e:
            logger.warning("Failed to load beliefs: %s", e)
            return ""
