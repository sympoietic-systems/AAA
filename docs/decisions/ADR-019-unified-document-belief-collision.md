# ADR-019: Unified Document Belief Collision Analysis

**Date:** 2026-06-02  
**Status:** accepted  
**Deciders:** Antigravity (Dev Agent), Interlocutor (User)

## Context

With the implementation of ADR-017 (Dynamic Autopoietic Belief Metabolism), the system gained live belief collision analysis for **web probes** (exogenous search results) and **images** (via the somatic shock pathway). However, **uploaded text/PDF documents** — the most common perception input — lacked equivalent collision analysis.

The initial implementation created a separate `DocumentCollisionAction` background task, resulting in **two sequential LLM calls** per document upload:
1. `SummarizeAction` → summary + opacity map (N+1 calls for N chunks)
2. `DocumentCollisionAction` → interference score + implicated nodes + 16D state vector impact (1 additional call)

This doubled latency and API cost for every document upload. Since the summarize action already reads and comprehends the full document text, the collision analysis can be folded into the same LLM pass at zero marginal cost.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Separate collision action** | Clean separation of concerns; independently configurable | Extra LLM call; doubled latency; redundant text comprehension |
| **Fold into summarize action** (selected) | Zero extra calls; LLM already has full context; single atomic result | Slightly more complex prompt; summary and collision coupled |
| **Post-hoc background daemon** | Fully decoupled; can run at idle time | Extra complexity; results not available immediately on upload |

## Decision

**Fold belief collision analysis into the `SummarizeAction`**, using belief-aware prompt variants:

### Single-Plateau Documents (short files)
The `local_digestion_with_beliefs_prompt` replaces the standard local digestion prompt. The LLM returns a single JSON object containing:
- `local_summary` — the document summary
- `opacity_map` — noise/boilerplate identification
- `interference_score` — float 0.0–1.0 measuring belief perturbation
- `implicated_nodes` — list of challenged/supported belief labels
- `state_vector_impact` — 16D float vector of coordinate adjustments

### Multi-Plateau Documents (long files)
Local digestion runs without beliefs (per-chunk, unchanged). The `global_synthesis_with_beliefs_prompt` replaces the standard global synthesis prompt. The LLM returns:
- `global_summary` — the synthesized summary
- `interference_score`, `implicated_nodes`, `state_vector_impact` — collision metrics derived from the full document perspective

### Payload Contract

```python
# Summarize with belief collision (routes.py)
summarize_payload = {
    "text": extracted_text,
    "active_beliefs_list": ["autopoiesis", "cybernetics", ...]  # optional
}
res = await background_engine.run("summarize", summarize_payload)

# Response includes collision metrics when beliefs were provided
res["interference_score"]     # float
res["implicated_nodes"]       # list[str]
res["state_vector_impact"]    # list[float] (16 elements)
```

### Metabolism Integration
After the summarize action completes, the perturbation passed to `metabolize_perception` is scaled by interference:
```
perturbation = 1.0 + interference_score × 2.0
```
A high-interference document (score ≈ 0.8) triggers perturbation ≈ 2.6, comparable to an image somatic shock. A low-interference document (score ≈ 0.1) yields perturbation ≈ 1.2, a gentle nudge.

### Database Columns
Three columns added to `perception_files` via migration:
- `interference_score` (REAL)
- `belief_nodes_implicated` (TEXT, JSON array)
- `state_vector_impact` (TEXT, JSON array of 16 floats)

### Frontend
A `DocumentMetadataCard` component in `SidePanel.tsx` renders:
- Interference score with yellow accent
- Implicated belief node tags with green (`#10b981`) accent
- Interactive 16D state vector bar chart with hover-to-inspect (reuses `DIMENSIONS_16` labels)

### Standalone Action (Preserved)
The `DocumentCollisionAction` remains registered on the `BackgroundTaskEngine` for direct invocation via `POST /api/background` with `action: "document_collision"`. This supports future use cases (e.g., re-analyzing existing documents against updated beliefs, batch collision audits).

## Consequences

**Positive:**
- **Zero extra LLM calls** — belief collision is free when folded into the summarize pass
- **Atomic results** — summary, opacity, and collision metrics arrive together, simplifying the processing flow
- **Consistent with existing patterns** — web probes and images already perform collision during their primary analysis step
- **Graceful degradation** — if no active beliefs exist, the summarize action falls back to the standard (non-belief) prompts transparently

**Negative:**
- The summarize prompt is now more complex when beliefs are present (larger JSON schema)
- Summary quality and collision quality are coupled — a model that struggles with one may degrade the other
- The `document_collision.yaml` prompt file is now partially redundant (kept for standalone use)
