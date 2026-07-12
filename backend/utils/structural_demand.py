"""Structural-demand detection — the ADR-062 §V.8 gate prerequisite.

The navigable-tree phase (Phase 2) must not be built on faith. Before any
tree-traversal code exists, we log whether the apparatus's own reasoning
manifests hunger for hierarchical navigation: moments where the agent reaches
for a section it cannot access via flat retrieval.

This module is pure detection + counting. It writes nothing and builds no
tree; it only makes demand *visible* so a later decision can be evidence-led
rather than benchmark-led. Silence here means the tree is dropped permanently.
"""

import re

# 1. Agent cites a section ("see §2.3", "section 2.1") — checked against the
#    heading-paths actually present in the retrieval set by the caller.
_SECTION_CITATION_RE = re.compile(
    r"(?:see\s+)?(?:§|section|sec\.?|chapter|ch\.?)\s*(\d+(?:\.\d+)*)",
    re.IGNORECASE,
)

# 2. Agent asks for more of a section / the surrounding argument.
_MORE_CONTEXT_RE = re.compile(
    r"(?:more\s+(?:from|of)\s+(?:section|§|chapter)"
    r"|surrounding\s+(?:argument|context|section)"
    r"|rest\s+of\s+(?:the\s+)?(?:section|chapter|argument))",
    re.IGNORECASE,
)

# 3. Agent's plan wants to follow the thread / drill into adjacent structure.
_FOLLOW_THREAD_RE = re.compile(
    r"(?:follow\s+the\s+thread"
    r"|adjacent\s+(?:section|topic|region)s?"
    r"|drill\s+(?:down|into)"
    r"|preceding\s+section|next\s+section|previous\s+section)",
    re.IGNORECASE,
)


def _cited_sections(text: str) -> set[str]:
    return {m.group(1) for m in _SECTION_CITATION_RE.finditer(text)}


def detect_structural_demand(
    agent_text: str,
    retrieved_heading_paths: list[list[str]] | None = None,
) -> dict:
    """Detect structural-demand signals in a single agent turn.

    Args:
        agent_text: the agent's response / plan text for the turn.
        retrieved_heading_paths: heading-paths of chunks that WERE in the
            retrieval set, so a citation to an *un-retrieved* section counts
            as unmet demand. When omitted, any section citation counts.

    Returns a dict with per-signal booleans and an overall ``demanded`` flag.
    """
    text = agent_text or ""

    cited = _cited_sections(text)
    retrieved_tokens: set[str] = set()
    if retrieved_heading_paths:
        for path in retrieved_heading_paths:
            for seg in path:
                for m in re.finditer(r"\d+(?:\.\d+)*", str(seg)):
                    retrieved_tokens.add(m.group(0))

    unmet_citation = bool(cited) and not cited.issubset(retrieved_tokens)

    more_context = bool(_MORE_CONTEXT_RE.search(text))
    follow_thread = bool(_FOLLOW_THREAD_RE.search(text))

    demanded = unmet_citation or more_context or follow_thread
    return {
        "unmet_section_citation": unmet_citation,
        "requested_more_context": more_context,
        "follow_thread": follow_thread,
        "cited_sections": sorted(cited),
        "demanded": demanded,
    }
