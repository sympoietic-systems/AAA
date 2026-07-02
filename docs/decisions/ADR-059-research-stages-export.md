# ADR-059: Research Stages Export (Clean Process Trace)

**Date:** 2026-07-02
**Status:** accepted
**Deciders:** opencode

---

## Context

The existing research Markdown export (`GET /api/research/tasks/{id}/export`) produces
a complete data dump including raw scraped source content (up to 5000 chars per asset).
This is useful for archival but creates large, unwieldy files and embeds harvested
web content that may not be appropriate for sharing.

There is no export format that captures the *research process itself* — the stages,
findings, gaps, reflections, and source attribution — without the raw harvested material.
The Report tab already exports the final synthesis report, but this omits the
intermediate cycles, consolidation reasoning, and methodological reflections that
constitute the actual research trace.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| Extend the existing `/export` endpoint with a `?mode=` query param | Minimal new surface area | Pollutes a single endpoint with divergent output shapes |
| New endpoint `/export/stages` | Clean separation of concerns; each format is independently maintainable | One more route |
| Generate from frontend by assembling API responses | No backend changes | Requires loading all step/result data client-side; fragile to schema changes |

## Decision

Add a dedicated `GET /api/research/tasks/{task_id}/export/stages` endpoint that produces
a clean Markdown document organized by research cycle, containing only the process trace —
no raw source content, only source links with names.

**Rationale:**
- The export format is fundamentally different from the full data dump — it's a
  *narrative* of the research process, not a data archive
- Keeping it as a separate endpoint allows each format to evolve independently
- The frontend already has separate export buttons for the final report; a stages
  export complements this with per-cycle granularity

## Implementation

- **`ExportService.build_research_stages_export()`** — new static method in
  `backend/services/export.py` that builds the Markdown document from steps,
  step results, and task metadata
- **Route** — `GET /api/research/tasks/{task_id}/export/stages` in
  `backend/api/routes/research.py`
- **Frontend** — `downloadResearchStagesExport()` in `frontend/src/api/research.ts`,
  with an "export stages" button in `TaskActions` for completed/failed/cancelled tasks

### Export Structure

```markdown
# Research: [Title]

## OBJECTIVES
## LIMITS (depth, breadth, budget)
## DOCUMENT DIGESTION (learnings, follow-ups, gaps — if present)

## Cycle N
### Sources (links with names only)
### Findings (learnings per source)
### Consolidation (completeness score, key insights, remaining gaps, next queries)
### Meta-Reflection (biases, cognitive metrics)
### Evaluation (stop/continue decision)

## SYNTHESIS (final report)
```

## Consequences

- **Easier**: Sharing research process traces without embedding harvested content;
  reviewing methodology per cycle; comparing consolidation reasoning across cycles
- **Harder**: Nothing. The endpoint is additive and doesn't modify any existing behavior
- **No migration needed**: Reads from existing `research_steps` and `research_step_results`
  tables — no schema changes
