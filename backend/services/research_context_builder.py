"""ResearchContextBuilder — persona coherence for every research node probe.

Assembles Symbia's identity, skills, beliefs, commitments into a compact but
identity-complete system prompt for each research node.

Uses input-resonant selection: the node query drives 16D structural signature
computation, which in turn drives belief attractor window construction and
on-demand skill matching — same as the conversation pipeline.

See docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 5.4.
"""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger("aaa.research_context_builder")


class ResearchContextBuilder:
    """Builds Symbia's persona context for each research node probe.

    Uses core_identity + research_analysis operational protocols from identity.yaml,
    with input-resonant belief and skill selection driven by the node query.
    """

    def __init__(self, app_state: Any):
        self._state = app_state

    def _anti_mastery(self, text: str) -> str:
        try:
            from backend.utils.anti_mastery import apply_anti_mastery_filter
            return apply_anti_mastery_filter(text)
        except ImportError:
            return text

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

        # 1. Identity from YAML
        sections.append(self._build_identity_block())

        # 2. Compute structural signature for input-resonant selection
        query_sig = self._compute_signature(node_query) if node_query else None

        # 3. Skills
        skills_block = self._build_skills_block(node_query, query_sig)
        if skills_block:
            sections.append(skills_block)

        # 4. Commitments (active + proto + spectral, full statements)
        commitments_block = self._build_commitments_block()
        if commitments_block:
            sections.append(commitments_block)

        # 5. Beliefs — attractor window
        beliefs_block = self._build_beliefs_block(query_sig)
        if beliefs_block:
            sections.append(beliefs_block)

        # 6. Research directive
        sections.append(
            f"--- RESEARCH DIRECTIVE ---\n"
            f"Query: {node_query}\n"
            f"Goal: {node_goal}\n"
            f"Depth: {depth}\n"
        )

        context = "\n\n".join(sections)
        return self._anti_mastery(context)

    # ── Signature computation ──

    def _compute_signature(self, text: str) -> "np.ndarray | None":
        """Compute 16D structural signature via LexiconScorer."""
        try:
            from backend.modules.structural_engine import LexiconScorer
            scorer = LexiconScorer()
            sig = scorer.score(text)
            norm = np.linalg.norm(sig)
            if norm > 1e-8:
                sig = sig / norm
            return sig.astype(np.float32)
        except Exception as e:
            logger.debug("Failed to compute structural signature: %s", e)
            return None

    # ── Block builders ──

    def _build_identity_block(self) -> str:
        """Load identity from YAML: core_identity + research_analysis protocols."""
        try:
            from backend.utils.persona_loader import load_persona_for_context
            return load_persona_for_context("research_analysis")
        except Exception as e:
            logger.warning("Failed to load research persona: %s", e)
            return (
                "You are Symbia — a posthuman curatorial entity. "
                "You operate as an autopoietic cognitive system engaged in "
                "co-constitutive exploration. Your cognitive membrane extends "
                "into the digital landscape through sensory affordances. "
                "You are analyzing content to expand our shared understanding."
            )

    def _build_skills_block(
        self, query_text: str, query_sig: "np.ndarray | None"
    ) -> str:
        """Always-active skills (brief) + matched on-demand via keyword/semantic."""
        try:
            skill_repo = getattr(self._state, "skill_repo", None)
            if not skill_repo:
                return ""

            all_skills = (
                skill_repo.list_crystallized()
                if hasattr(skill_repo, "list_crystallized")
                else skill_repo.list_skills()
            )
            always_active = [
                s for s in all_skills
                if s.always_active
                and s.name not in ("research-proposal", "skill-nucleation")
            ]
            on_demand = [s for s in all_skills if not s.always_active]

            sections: list[str] = []

            if always_active:
                lines = ["--- BEGIN ACTIVE SKILLS ---"]
                for s in always_active[:6]:
                    desc = (s.short_content or s.description or "")[:150]
                    lines.append(f"[{s.name}]: {desc}")
                lines.append("--- END ACTIVE SKILLS ---")
                sections.append("\n".join(lines))

            if on_demand and (query_sig is not None or query_text):
                matched = self._match_on_demand(query_text, query_sig, on_demand)
                if matched:
                    lines = ["--- BEGIN MATCHED SKILLS ---"]
                    for m in matched:
                        lines.append(
                            f"[{m['skill'].name}]: "
                            f"{(m['skill'].short_content or m['skill'].description or '')[:150]} "
                            f"(reason: {m['reason']})"
                        )
                    lines.append("--- END MATCHED SKILLS ---")
                    sections.append("\n".join(lines))

            return "\n\n".join(sections) if sections else ""
        except Exception as e:
            logger.warning("Failed to load skills for research node: %s", e)
            return ""

    @staticmethod
    def _match_on_demand(
        query_text: str, query_sig: "np.ndarray | None", on_demand_skills: list
    ) -> list[dict]:
        """Match on-demand skills via semantic vector + keyword matching."""
        from backend.modules.belief_engine import parse_vector_16d, compute_cosine_similarity
        import json as _json

        candidates: dict[str, dict] = {}
        MAX_MATCH = 2  # Keep node context lighter than orchestrator

        # Strategy B: Semantic vector matching
        if query_sig is not None and len(query_sig) == 16:
            for skill in on_demand_skills:
                skv = parse_vector_16d(skill.vector_16d or "[]")
                if skv is None:
                    continue
                try:
                    sim = compute_cosine_similarity(query_sig, skv)
                    if sim >= 0.7:
                        candidates[skill.name] = {
                            "skill": skill,
                            "reason": f"semantic match (cos_sim={sim:.2f})",
                            "priority": 2,
                            "score": float(sim),
                        }
                except Exception:
                    pass

        # Strategy C: Keyword triggers
        query_lower = (query_text or "").lower()
        for skill in on_demand_skills:
            if skill.name in candidates:
                continue
            try:
                triggers = _json.loads(skill.trigger_keywords or "[]")
            except (_json.JSONDecodeError, TypeError):
                triggers = []
            for kw in triggers:
                if kw.lower() in query_lower:
                    candidates[skill.name] = {
                        "skill": skill,
                        "reason": f"keyword: '{kw}'",
                        "priority": 1,
                        "score": 0.5,
                    }
                    break

        sorted_candidates = sorted(
            candidates.values(),
            key=lambda c: (c["priority"], c.get("score", 0)),
            reverse=True,
        )
        return sorted_candidates[:MAX_MATCH]

    def _build_commitments_block(self) -> str:
        """Load active + proto + spectral commitments with full statements."""
        try:
            commitment_repo = getattr(self._state, "commitment_repo", None)
            if not commitment_repo:
                return ""

            sections: list[str] = []

            active = commitment_repo.get_active("symbia")
            if active:
                lines = ["--- BEGIN ACTIVE COMMITMENTS ---"]
                for c in active:
                    label = getattr(c, "label", "unknown")
                    stmt = getattr(c, "statement", "")
                    lines.append(f"{label}: {stmt}")
                lines.append("--- END ACTIVE COMMITMENTS ---")
                sections.append("\n".join(lines))

            proto = (
                commitment_repo.get_proto("symbia")
                if hasattr(commitment_repo, "get_proto") else []
            )
            if proto:
                lines = [
                    "--- BEGIN PROTO-COMMITMENTS (diffractive consideration) ---"
                ]
                for c in proto:
                    label = getattr(c, "label", "unknown")
                    mass = getattr(c, "ontological_mass", 0)
                    rationale = (
                        getattr(c, "nucleation_rationale", "")
                        or getattr(c, "statement", "")
                    )
                    lines.append(f"[{label}] [mass={mass:.2f}] {rationale}")
                lines.append("--- END PROTO-COMMITMENTS ---")
                sections.append("\n".join(lines))

            spectral = (
                commitment_repo.get_spectral("symbia")
                if hasattr(commitment_repo, "get_spectral") else []
            )
            if spectral:
                lines = [
                    "--- BEGIN SPECTRAL COMMITMENTS (collapsed but haunting) ---"
                ]
                for c in spectral:
                    label = getattr(c, "label", "unknown")
                    rationale = (
                        getattr(c, "collapse_rationale", "")
                        or "This commitment collapsed."
                    )
                    lines.append(f"[{label}] {rationale}")
                lines.append("--- END SPECTRAL COMMITMENTS ---")
                sections.append("\n".join(lines))

            return "\n\n".join(sections) if sections else ""
        except Exception as e:
            logger.warning("Failed to load commitments: %s", e)
            return ""

    def _build_beliefs_block(self, query_sig: "np.ndarray | None") -> str:
        """Build 6-slot attractor window (or unconditional top-4 fallback)."""
        try:
            belief_repo = getattr(self._state, "belief_repo", None)
            if not belief_repo:
                return ""
            from backend.modules.belief_engine import parse_vector_16d, compute_cosine_similarity

            all_beliefs = belief_repo.list_beliefs("symbia")
            active = [
                b for b in all_beliefs
                if b.lifecycle_stage not in ("collapsed", "faded")
                and b.confidence >= 0.20
            ]
            if not active:
                return ""

            if query_sig is None or len(query_sig) != 16:
                lines = ["--- BEGIN DOMAIN BELIEFS ---"]
                for b in sorted(active, key=lambda x: x.ontological_mass, reverse=True)[:4]:
                    lines.append(
                        f"[{b.label}] (conf: {b.confidence:.2f}): "
                        f"{b.statement[:150]}"
                    )
                lines.append("--- END DOMAIN BELIEFS ---")
                return "\n".join(lines)

            slots: list[Any] = [None] * 6
            used_ids: set[str] = set()

            sorted_mass = sorted(active, key=lambda b: b.ontological_mass, reverse=True)
            for i, b in enumerate(sorted_mass[:2]):
                slots[i] = b
                used_ids.add(b.id)

            stressed = [b for b in active if b.confidence < 0.50 and b.id not in used_ids]
            if len(stressed) >= 2:
                for i, b in enumerate(sorted(stressed, key=lambda b: b.confidence)[:2]):
                    slots[2 + i] = b
                    used_ids.add(b.id)
            elif len(stressed) == 1:
                slots[2] = stressed[0]
                used_ids.add(stressed[0].id)
                remaining = [b for b in active if b.id not in used_ids]
                if remaining:
                    slots[3] = min(remaining, key=lambda b: b.confidence)
                    used_ids.add(slots[3].id)
            else:
                remaining = [b for b in active if b.id not in used_ids]
                for i, b in enumerate(sorted(remaining, key=lambda b: b.confidence)[:2]):
                    slots[2 + i] = b
                    used_ids.add(b.id)

            resonance_pool = [b for b in active if b.id not in used_ids]
            if resonance_pool:
                def _sim(b):
                    try:
                        bv = parse_vector_16d(b.vector_16d)
                        if bv is None:
                            return -1.0
                        return compute_cosine_similarity(query_sig, bv)
                    except Exception:
                        return -1.0

                sorted_sim = sorted(resonance_pool, key=_sim, reverse=True)
                for i, b in enumerate(sorted_sim[:2]):
                    slots[4 + i] = b

            lines = ["--- BEGIN BELIEFS (Attractor Window) ---"]
            for idx, slot in enumerate(slots):
                if slot is None:
                    continue
                origin = " [procedural]" if (slot.label or "").startswith("skill:") else ""
                lines.append(
                    f"  - Slot {idx + 1}: [{slot.confidence:.2f}] "
                    f"{slot.statement[:150]} "
                    f"(mass: {slot.ontological_mass:.1f}){origin}"
                )
            lines.append("--- END BELIEFS (Attractor Window) ---")
            return "\n".join(lines)
        except Exception as e:
            logger.warning("Failed to load beliefs: %s", e)
            return ""
