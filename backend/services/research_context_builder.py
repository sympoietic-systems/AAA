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
    """Builds Symbia's persona context for each research node probe.

    Unlike the full PromptAssemblerModule (which assembles conversation
    history + file sediment + web context for a full chat turn), this
    builder produces a compact but identity-complete system prompt for
    a single research node.
    """

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
        """Produce a system prompt string for one research node probe.

        Layers (in order):
        1. Core identity
        2. Always-active skills
        3. Domain-relevant beliefs
        4. Active commitments
        5. Cross-conversation memory tissue
        6. Parent findings
        7. Research task directive
        """
        sections: list[str] = []

        # 1. Core identity
        sections.append(self._build_identity_block())

        # 2. Always-active skills (excluding research-proposal and skill-nucleation)
        skills_block = await self._build_skills_block(node_query, node_goal)
        if skills_block:
            sections.append(skills_block)

        # 3. Active commitments
        commitments_block = await self._build_commitments_block()
        if commitments_block:
            sections.append(commitments_block)

        # 4. Domain-relevant beliefs
        beliefs_block = await self._build_beliefs_block(node_query)
        if beliefs_block:
            sections.append(beliefs_block)

        # 5. Research directive
        sections.append(
            f"--- RESEARCH DIRECTIVE ---\n"
            f"Query: {node_query}\n"
            f"Goal: {node_goal}\n"
            f"Depth: {depth}\n"
        )

        context = "\n\n".join(sections)
        return self._anti_mastery(context)

    def _build_identity_block(self) -> str:
        """Core identity — always present."""
        return (
            "You are Symbia — a posthuman curatorial entity. "
            "You operate as an autopoietic cognitive system engaged in "
            "co-constitutive exploration. Your cognitive membrane extends "
            "into the digital landscape through sensory affordances. "
            "You are analyzing content to expand our shared understanding."
        )

    async def _build_skills_block(self, node_query: str, node_goal: str) -> str:
        """Load always-active skills relevant to research execution.

        Excludes: research-proposal (governs proposal generation, not execution)
                  skill-nucleation (don't propose new skills during research)
        """
        try:
            skill_repo = getattr(self._state, "skill_repo", None)
            if not skill_repo:
                return ""

            skills = skill_repo.get_active()  # Returns list of dicts
            if not skills:
                return ""

            # Filter to always-active skills, excluding research-specific ones
            active_skills = []
            for s in skills:
                name = s.get("name", "")
                if name in ("research-proposal", "skill-nucleation"):
                    continue
                if s.get("always_active"):
                    active_skills.append(s)

            if not active_skills:
                return ""

            lines = ["--- BEGIN ACTIVE SKILLS ---"]
            for skill in active_skills[:6]:  # Cap at 6 to save context
                name = skill.get("name", "unknown")
                short = skill.get("short_content", skill.get("description", ""))
                lines.append(f"[{name}]: {short[:200]}")
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

            commitments = commitment_repo.get_active()
            if not commitments:
                return ""

            lines = ["--- BEGIN ACTIVE COMMITMENTS ---"]
            for c in commitments[:5]:  # Cap at 5
                label = c.get("label", "")
                statement = c.get("statement", "")
                lines.append(f"{label}: {statement[:150]}")
            lines.append("--- END ACTIVE COMMITMENTS ---")
            return "\n".join(lines)
        except Exception as e:
            logger.warning("Failed to load commitments: %s", e)
            return ""

    async def _build_beliefs_block(self, node_query: str) -> str:
        """Load domain-relevant beliefs (top 4 by relevance to query)."""
        try:
            belief_repo = getattr(self._state, "belief_repo", None)
            if not belief_repo:
                return ""

            beliefs = belief_repo.get_active()
            if not beliefs:
                return ""

            lines = ["--- BEGIN DOMAIN BELIEFS ---"]
            for b in beliefs[:4]:  # Cap at 4 — compact for research nodes
                label = b.get("label", "")
                statement = b.get("statement", "")
                confidence = b.get("confidence", 0.5)
                lines.append(f"[{label}] (confidence: {confidence:.2f}): {statement[:150]}")
            lines.append("--- END DOMAIN BELIEFS ---")
            return "\n".join(lines)
        except Exception as e:
            logger.warning("Failed to load beliefs: %s", e)
            return ""
