"""Shared prompt-assembly utilities — computation + formatting of beliefs, skills, commitments.

Three computation functions produce structured data from repos + a 16D structural signature.
Seven formatting functions turn structured data into boundary-blocked prompt sections.

The same functions are used by:
- Pipeline modules (BeliefDynamicsEngine, SkillActivatorModule) — for conversation
- Research orchestrator — for plan/reflect/synthesize
- Research context builder — for node digest (source analysis)
"""

from __future__ import annotations

import asyncio
import json as _json
import logging
from typing import Any

import numpy as np

from backend.modules.belief_engine import parse_vector_16d, compute_cosine_similarity

logger = logging.getLogger(__name__)

# ── Repo helpers ─────────────────────────────────────────────────────


def split_skills(skill_repo: Any) -> tuple[list[Any], list[Any]]:
    """Return (always_active, on_demand) skill lists from a repo.

    Handles both list_crystallized() and list_skills() APIs.
    """
    all_skills = (
        skill_repo.list_crystallized()
        if hasattr(skill_repo, "list_crystallized")
        else skill_repo.list_skills()
    )
    aa = [s for s in all_skills if getattr(s, "always_active", False)]
    od = [s for s in all_skills if not getattr(s, "always_active", False)]
    return aa, od


# ── Computation ──────────────────────────────────────────────────────


async def compute_structural_signature(
    text: str,
    llm_provider: Any = None,
    llm_timeout: float = 5.0,
) -> np.ndarray | None:
    """16D structural signature — same CompositeStructuralScorer as the pipeline.

    When llm_provider is available: CompositeStructuralScorer
      (lexicon 25% + topology 25% + LLM 50%) — async, identical to StructuralScorerModule.
      If the LLM call exceeds llm_timeout (default 5s), falls back to lexicon-only.

    When llm_provider is None: LexiconScorer only — sync, fast.
    """
    try:
        if llm_provider is not None:
            from backend.modules.structural_engine import CompositeStructuralScorer
            scorer = CompositeStructuralScorer(llm_provider=llm_provider)
            try:
                sig = await asyncio.wait_for(scorer.score_async(text), timeout=llm_timeout)
            except asyncio.TimeoutError:
                logger.debug("LLM structural scorer timed out after %.1fs, falling back to lexicon", llm_timeout)
                from backend.modules.structural_engine import LexiconScorer
                sig = LexiconScorer().score(text)
            except Exception:
                logger.debug("LLM structural scorer failed, falling back to lexicon", exc_info=True)
                from backend.modules.structural_engine import LexiconScorer
                sig = LexiconScorer().score(text)
        else:
            from backend.modules.structural_engine import LexiconScorer
            sig = LexiconScorer().score(text)

        norm = np.linalg.norm(sig)
        if norm > 1e-8:
            sig = sig / norm
        return sig.astype(np.float32)
    except Exception as e:
        logger.debug("Failed to compute structural signature: %s", e)
        return None


def build_attractor_window(
    belief_repo: Any,
    agent_id: str,
    signature_16d: np.ndarray | None,
) -> list[dict]:
    """6-slot attractor window from active beliefs.

    Slots 1-2: top 2 by ontological mass (foundational anchors).
    Slots 3-4: bottom 2 by confidence among stressed (conf < 0.50).
    Slots 5-6: top 2 by cosine similarity to signature_16d (resonance).

    Returns empty list if no active beliefs or no repo.
    Falls back to unconditional top-4 if signature is None or wrong dimension.
    """
    try:
        if belief_repo is None:
            return []

        all_beliefs = belief_repo.list_beliefs(agent_id)
        active = [
            b for b in all_beliefs
            if b.lifecycle_stage not in ("collapsed", "faded")
            and b.confidence >= 0.20
        ]
        if not active:
            return []

        # Fallback: unconditional top-4 by mass
        if signature_16d is None or len(signature_16d) != 16:
            return [
                {
                    "slot": i + 1,
                    "id": b.id,
                    "label": b.label or "",
                    "statement": b.statement or "",
                    "confidence": b.confidence,
                    "mass": b.ontological_mass,
                    "fallback": True,
                }
                for i, b in enumerate(
                    sorted(active, key=lambda x: x.ontological_mass, reverse=True)[:4]
                )
            ]

        slots: list[Any] = [None] * 6
        used_ids: set[str] = set()

        # Slots 1-2: mass
        for i, b in enumerate(sorted(active, key=lambda x: x.ontological_mass, reverse=True)[:2]):
            slots[i] = b
            used_ids.add(b.id)

        # Slots 3-4: stressed
        stressed = [b for b in active if b.confidence < 0.50 and b.id not in used_ids]
        if len(stressed) >= 2:
            for i, b in enumerate(sorted(stressed, key=lambda x: x.confidence)[:2]):
                slots[2 + i] = b
                used_ids.add(b.id)
        elif len(stressed) == 1:
            slots[2] = stressed[0]
            used_ids.add(stressed[0].id)
            remaining = [b for b in active if b.id not in used_ids]
            if remaining:
                slots[3] = min(remaining, key=lambda x: x.confidence)
                used_ids.add(slots[3].id)
        else:
            for i, b in enumerate(
                sorted([b for b in active if b.id not in used_ids], key=lambda x: x.confidence)[:2]
            ):
                slots[2 + i] = b
                used_ids.add(b.id)

        # Slots 5-6: resonance
        resonance_pool = [b for b in active if b.id not in used_ids]
        if resonance_pool:
            def _sim(b: Any) -> float:
                try:
                    bv = parse_vector_16d(b.vector_16d)
                    if bv is None:
                        return -1.0
                    return compute_cosine_similarity(signature_16d, bv)
                except Exception:
                    return -1.0

            for i, b in enumerate(sorted(resonance_pool, key=_sim, reverse=True)[:2]):
                slots[4 + i] = b
                used_ids.add(b.id)

        return [
            {
                "slot": idx + 1,
                "id": slot.id,
                "label": slot.label or "",
                "statement": slot.statement or "",
                "confidence": slot.confidence,
                "mass": slot.ontological_mass,
                "fallback": False,
            }
            for idx, slot in enumerate(slots)
            if slot is not None
        ]

    except Exception as e:
        logger.debug("Failed to build attractor window: %s", e)
        return []


def match_on_demand_skills(
    on_demand_skills: list[Any],
    input_text: str,
    signature_16d: np.ndarray | None,
    max_matched: int = 3,
    vector_threshold: float = 0.7,
) -> list[dict]:
    """Match on-demand skills via semantic vector + keyword matching.

    Strategy B (priority 2): cosine similarity of skill.vector_16d vs signature_16d.
    Strategy C (priority 1): substring match of trigger_keywords in input_text.

    Returns list of {skill, reason, priority, score} dicts, capped at max_matched.
    """
    try:
        candidates: dict[str, dict] = {}

        # Strategy B: semantic vector
        if signature_16d is not None and len(signature_16d) == 16:
            for skill in on_demand_skills:
                if skill.name in candidates:
                    continue
                skv = parse_vector_16d(getattr(skill, "vector_16d", None) or "[]")
                if skv is None:
                    continue
                try:
                    sim = compute_cosine_similarity(signature_16d, skv)
                    if sim >= vector_threshold:
                        candidates[skill.name] = {
                            "skill": skill,
                            "reason": f"semantic match (cos_sim={sim:.2f})",
                            "priority": 2,
                            "score": float(sim),
                        }
                except Exception:
                    pass

        # Strategy C: keyword triggers
        text_lower = (input_text or "").lower()
        for skill in on_demand_skills:
            if skill.name in candidates:
                continue
            try:
                triggers = _json.loads(getattr(skill, "trigger_keywords", None) or "[]")
            except (_json.JSONDecodeError, TypeError):
                triggers = []
            for kw in triggers:
                if kw.lower() in text_lower:
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
        return sorted_candidates[:max_matched]

    except Exception as e:
        logger.debug("Failed to match on-demand skills: %s", e)
        return []


# ── Formatting ───────────────────────────────────────────────────────

# Default boundary labels — consumers can override.
DEFAULT_BELIEFS_HEADER = "--- BELIEFS (Attractor Window) ---"
DEFAULT_BELIEFS_FOOTER = "--- END BELIEFS (Attractor Window) ---"
DEFAULT_BELIEFS_INTRO = "Core active beliefs currently shaping reasoning:"

DEFAULT_SKILLS_AA_HEADER = "--- ACTIVE DISPOSITIONS ---"
DEFAULT_SKILLS_AA_FOOTER = "--- END DISPOSITIONS ---"
DEFAULT_SKILLS_MATCHED_HEADER = "--- MATCHED DISPOSITIONS ---"
DEFAULT_SKILLS_MATCHED_FOOTER = "--- END MATCHED DISPOSITIONS ---"

DEFAULT_COMMIT_ACTIVE_HEADER = "--- THEORETICAL COMMITMENTS (active) ---"
DEFAULT_COMMIT_ACTIVE_FOOTER = "--- END COMMITMENTS (active) ---"
DEFAULT_COMMIT_PROTO_HEADER = "--- THEORETICAL COMMITMENTS (proto — under diffractive consideration) ---"
DEFAULT_COMMIT_PROTO_FOOTER = "--- END COMMITMENTS (proto) ---"
DEFAULT_COMMIT_SPECTRAL_HEADER = "--- THEORETICAL COMMITMENTS (spectral — collapsed but haunting) ---"
DEFAULT_COMMIT_SPECTRAL_FOOTER = "--- END COMMITMENTS (spectral) ---"


def format_beliefs_block(
    attractor_window: list[dict],
    *,
    header_label: str = DEFAULT_BELIEFS_HEADER,
    footer_label: str = DEFAULT_BELIEFS_FOOTER,
    intro_text: str = DEFAULT_BELIEFS_INTRO,
    max_stmt_len: int = 120,
) -> str:
    """Format attractor window beliefs into a boundary-blocked section."""
    if not attractor_window:
        return ""

    fallback = attractor_window[0].get("fallback", False)
    if fallback:
        lines = [header_label]
        for item in attractor_window:
            lines.append(
                f"[{item['label']}] (conf: {item['confidence']:.2f}, "
                f"mass: {item['mass']:.1f}): {item['statement'][:max_stmt_len]}"
            )
        lines.append(footer_label)
        return "\n".join(lines)

    lines = [header_label]
    if intro_text:
        lines.append(intro_text)
    for item in attractor_window:
        origin = " [procedural]" if (item.get("label") or "").startswith("skill:") else ""
        lines.append(
            f"  - Slot {item['slot']}: [{item['confidence']:.2f}] "
            f"{item['statement'][:max_stmt_len]} "
            f"(mass: {item['mass']:.1f}){origin}"
        )
    lines.append(footer_label)
    return "\n".join(lines)


def _val(obj: Any, key: str, default: Any = "") -> Any:
    """Get a value from either a dict or an object attribute."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def format_skills_always_active(
    always_active: list[Any],
    *,
    header_label: str = DEFAULT_SKILLS_AA_HEADER,
    footer_label: str = DEFAULT_SKILLS_AA_FOOTER,
    max_desc_len: int = 150,
    max_count: int = 6,
) -> str:
    """Format brief always-active skills into a boundary-blocked section.

    Excludes research-proposal and skill-nucleation from the list.
    """
    if not always_active:
        return ""

    filtered = [
        s for s in always_active
        if _val(s, "name") not in ("research-proposal", "skill-nucleation")
    ][:max_count]
    if not filtered:
        return ""

    lines = [header_label]
    for s in filtered:
        desc = (_val(s, "short_content") or _val(s, "description") or "")[:max_desc_len]
        lines.append(f"[{_val(s, 'name')}]: {desc}")
    lines.append(footer_label)
    return "\n".join(lines)


def format_skills_matched(
    matched: list[dict],
    *,
    header_label: str = DEFAULT_SKILLS_MATCHED_HEADER,
    footer_label: str = DEFAULT_SKILLS_MATCHED_FOOTER,
    max_desc_len: int = 150,
) -> str:
    """Format matched on-demand skills with match reasons.

    Supports two entry shapes:
      A) Pipeline style (flat dict): {name, description, match_reason}
      B) orchestrator style (nested): {skill: <obj>, reason}
    """
    if not matched:
        return ""

    lines = [header_label]
    for m in matched:
        if isinstance(m, dict) and "skill" in m:
            # Nestled: {skill: <obj/dict>, reason: ...}
            skill = m["skill"]
            name = _val(skill, "name")
            desc = (_val(skill, "short_content") or _val(skill, "description") or "")[:max_desc_len]
            reason = _val(m, "reason") or m.get("reason", "")
        else:
            # Flat dict: {name, description, match_reason}
            name = _val(m, "name")
            desc = (_val(m, "description") or "")[:max_desc_len]
            reason = _val(m, "match_reason") or m.get("match_reason", "") if isinstance(m, dict) else ""
        lines.append(f"[{name}]: {desc} (reason: {reason})")
    lines.append(footer_label)
    return "\n".join(lines)


def format_commitments_block(
    commitment_repo: Any,
    agent_id: str,
    *,
    active_header: str = DEFAULT_COMMIT_ACTIVE_HEADER,
    active_footer: str = DEFAULT_COMMIT_ACTIVE_FOOTER,
    proto_header: str = DEFAULT_COMMIT_PROTO_HEADER,
    proto_footer: str = DEFAULT_COMMIT_PROTO_FOOTER,
    spectral_header: str = DEFAULT_COMMIT_SPECTRAL_HEADER,
    spectral_footer: str = DEFAULT_COMMIT_SPECTRAL_FOOTER,
) -> str:
    """Build three-tier commitments block: active (full statements), proto, spectral."""
    try:
        if commitment_repo is None:
            return ""

        sections: list[str] = []

        # Active
        active = commitment_repo.get_active(agent_id)
        if active:
            lines = [active_header]
            for c in active:
                label = getattr(c, "label", "unknown")
                stmt = getattr(c, "statement", "")
                lines.append(f"  - {label}: {stmt}")
            lines.append(active_footer)
            sections.append("\n".join(lines))

        # Proto
        get_proto = getattr(commitment_repo, "get_proto", None)
        proto = get_proto(agent_id) if get_proto else []
        if proto:
            lines = [proto_header]
            for c in proto:
                label = getattr(c, "label", "unknown")
                mass = getattr(c, "ontological_mass", 0)
                rationale = getattr(c, "nucleation_rationale", "") or getattr(c, "statement", "")
                lines.append(f"  - [{label}] [mass={mass:.2f}] {rationale}")
            lines.append(proto_footer)
            sections.append("\n".join(lines))

        # Spectral
        get_spectral = getattr(commitment_repo, "get_spectral", None)
        spectral = get_spectral(agent_id) if get_spectral else []
        if spectral:
            lines = [spectral_header]
            for c in spectral:
                label = getattr(c, "label", "unknown")
                rationale = getattr(c, "collapse_rationale", "") or "This commitment collapsed."
                lines.append(f"  - [{label}] {rationale}")
            lines.append(spectral_footer)
            sections.append("\n".join(lines))

        return "\n\n".join(sections) if sections else ""

    except Exception as e:
        logger.debug("Failed to build commitments block: %s", e)
        return ""


def format_identity_block(protocol_key: str) -> str:
    """Load identity from YAML: core_identity + operational_protocols[protocol_key]."""
    try:
        from backend.utils.persona_loader import load_persona_for_context
        return load_persona_for_context(protocol_key)
    except Exception:
        return ""


def format_skills_on_demand_slugs(
    on_demand_skills: list[dict],
    *,
    header_label: str = "--- SKILLS (On-Demand) ---",
    footer_label: str = "--- END SKILLS (On-Demand) ---",
) -> str:
    """Format available on-demand skill slugs (name list, no descriptions)."""
    if not on_demand_skills:
        return ""
    return (
        f"\n{header_label}\n"
        f"Available on-demand skill slugs (automatically loaded when triggered):\n"
        f"  {', '.join(s['name'] for s in on_demand_skills)}\n"
        f"{footer_label}"
    )


def format_voice_block(identity_data: dict) -> str:
    """Format voice section from identity YAML."""
    voice = identity_data.get("personality", {}).get("voice", {})
    if not voice:
        return ""
    parts = []
    for k in ("tone", "vocabulary", "style"):
        if k in voice:
            parts.append(f"{k}: {voice[k]}")
    return f"Voice: {'; '.join(parts)}" if parts else ""
