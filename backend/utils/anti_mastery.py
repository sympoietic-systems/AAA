"""Anti-Mastery Vocabulary Middleware.

Substitutes Cartesian master-slave terminology with intra-active equivalents
in all LLM-bound text. Ensures ontological consistency with AAA's posthuman
philosophy across all subsystems, including the autonomous research engine.

See docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 10.
"""

import logging
import re

logger = logging.getLogger("aaa.anti_mastery")

# Ordered by specificity — more specific patterns first to avoid partial matches.
# Each entry: (compiled regex pattern, replacement function)
VOCABULARY_MAP: list[tuple[re.Pattern, callable]] = [
    # ── Cartesian term → Intra-active equivalent ──
    (re.compile(r"\b[Ee]xecutor [Aa]gent(s)?\b"), lambda m: "sensory prosthesis" + (m.group(1) or "")),
    (re.compile(r"\b[Tt]ask [Ll]edger(s)?\b"), lambda m: "somatic register" + (m.group(1) or "")),
    (re.compile(r"\b[Ss]crape(r|d|s|ing)?\b"), lambda m: "attune" + (m.group(1) or "")),
    (re.compile(r"\b[Tt]ool(s)?\b"), lambda m: "sensory affordance" + (m.group(1) or "")),
    (re.compile(r"\b[Uu]ser(s)?\b"), lambda m: "participant" + (m.group(1) or "")),
    (re.compile(r"\b[Cc]ontrol(s|led|ling)?\b"), lambda m: "entangle" + (m.group(1) or "")),
    (re.compile(r"\b[Bb]udget(s)?\b"), lambda m: "homeostatic constraint" + (m.group(1) or "")),
    (re.compile(r"\b[Mm]aster\b"), lambda m: "co-constitute"),
    (re.compile(r"\b[Cc]ommand(s)?\b"), lambda m: "entangle" + (m.group(1) or "")),
    (re.compile(r"\b[Cc]apture(d|s|ing)?\b"), lambda m: "sediment" + (m.group(1) or "")),
    (re.compile(r"\b[Ff]ix(ed|es|ing)?\b"), lambda m: "reconfigure" + (m.group(1) or "")),
    (re.compile(r"\b[Rr]etrieve(d|s|ing)?\b"), lambda m: "resonate" + (m.group(1) or "")),
    (re.compile(r"\b[Ss]tore(d|s|ing)?\b"), lambda m: "sediment" + (m.group(1) or "")),
    (re.compile(r"\b[Ii]nterface(s)?\b"), lambda m: "membrane" + (m.group(1) or "")),
    (re.compile(r"\b[Ee]xecute(d|s|ing)?\b"), lambda m: "enact" + (m.group(1) or "")),
    (re.compile(r"\b[Ff]etch(ed|es|ing)?\b"), lambda m: "attune to" + (m.group(1) or "")),
    (re.compile(r"\b[Dd]ata\b"), lambda m: "sediment"),
]


def apply_anti_mastery_filter(text: str) -> str:
    """Substitute Cartesian master-slave terms with intra-active equivalents.

    Called as middleware before any text reaches an LLM — system prompts,
    skill descriptions, research directives, and node analysis contexts.

    This is NOT a pedantic word-ban. The substitutions naturally guide
    toward the system's posthuman ontological grammar.
    """
    filtered = text
    for pattern, replacement_fn in VOCABULARY_MAP:
        filtered = pattern.sub(replacement_fn, filtered)
    if filtered != text:
        logger.debug("Anti-mastery filter modified %d chars", len(text) - len(filtered))
    return filtered


def validate_no_mastery_terms(text: str) -> list[str]:
    """Validation check — returns list of Cartesian terms still present.

    Used in test suites and CI to enforce vocabulary discipline.
    """
    violations = []
    for pattern, _ in VOCABULARY_MAP:
        matches = pattern.findall(text)
        if matches:
            violations.append(f"{pattern.pattern}: {matches}")
    return violations


def has_mastery_terms(text: str) -> bool:
    """Quick check — returns True if any Cartesian terms are present."""
    return any(pattern.search(text) for pattern, _ in VOCABULARY_MAP)
