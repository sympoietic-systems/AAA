# ADR-053: Research Continuation with Document Digestion

**Date:** 2026-06-26
**Status:** accepted
**Deciders:** Antigravity, Symbia (consulted)

## Context

### Problem 1: "Continue Deeper" is a Blind Fork

The current "Continue Deeper" button (`TaskActions.tsx:39`, `ResearchDetailPanel.tsx:288`) creates a brand new research task with the same objective and `max_depth + 1`. It discards all prior findings — the new task has no memory of the synthesis it emerged from. This is structurally identical to a fresh dispatch; the word "continue" is misleading.

The planner (`phases.py:388`, `_phase_plan`) already supports a `previous_context` parameter that triggers a `user_with_context` template variant (`orchestrator_planner.yaml:27-33`), but this hook is never wired into the continue flow.

### Problem 2: No Way to Inject Personal Knowledge

Users have documents (notes, theories, concepts they wrote) that do not exist online. When doing research, there is no mechanism to inject such documents into the research pipeline so their content is analyzed against the research objective, producing learnings that participate in the full research loop (search, reflect, evaluate, synthesize).

### Problem 3: No Control Over Continuation Depth

The current continue button always adds exactly `+1` to `max_depth`. Users cannot specify how many additional cycles to run, nor can they adjust the goal/framing when continuing.

### Current Capabilities

- **Perception pipeline** (`perception.py:205`, `_retrieve_relevant_chunks`): Embeds a query, computes cosine similarity (dot product) against all indexed document chunks via `all-MiniLM-L6-v2` 384-dim embeddings, returns top-k chunks + file manifest with summaries. Already production-grade.
- **Document digestion** (`digest_worker.py:90`, `process_and_summarize_file`): Files uploaded to conversations are chunked, embedded, summarized via LLM, and stored in `perception_files` + `perception_sediment`. Already production-grade.
- **Source analysis** (`tools.py`, `_analyze_source`): LLM tool that digests a web source against the research objective, extracting learnings, followup questions, gaps, and relevance scores. Already used for web sources in the orchestrator pipeline.

## Decision

### 1. True Continuation Endpoint: `POST /research/continue`

A new backend endpoint that creates a continued research task with memory of the prior synthesis:

**Payload:**
```json
{
  "source_task_id": "uuid",
  "adjusted_objective": "optional refined goal",
  "additional_cycles": 2,
  "inject_file_id": "optional perception_files ref",
  "document_mode": "full" | "chunks",
  "document_chunk_limit": 5,
  "budget_limit_usd": 0.50
}
```

**Behavior:**
- Reads the source task's `result_summary` as `previous_context`
- Sets `max_depth = source.max_depth + additional_cycles`
- Links `continue_from_task_id = source_task_id` for lineage tracking
- If `inject_file_id` is provided, sets up the document digestion phase
- Passes `previous_context` to the planner via the existing `user_with_context` template

### 2. New Phase: `document_digestion`

A new pipeline phase inserted into the orchestrator's `PHASE_ORDER` after planning and before the first web search:

```
planning → document_digestion → searching → parsing → digesting → reflecting → evaluating → ...
```

The phase is **skipped** when no document is injected.

**Two modes:**

| Mode | Behavior | Use Case |
|------|----------|----------|
| `full` | All document chunks are retrieved and digested via `_analyze_source` | Short documents, essays, notes |
| `chunks` | Only top-N cosine-similar chunks (against objective) are retrieved and digested | Large books, long documents |

**Outputs:**
- Learnings → appended to `all_findings` (the research's accumulated knowledge)
- Followup questions → merged into `digest_signals` (consumed by the search phase)
- Gaps → merged into `digest_signals`
- A `research_steps` record of type `document_digestion` with full result data

### 3. Planning Phase Receives Summary Only

The planner receives the document's `file_summary` (generated at upload time by `digest_worker`) and `previous_context` (prior synthesis). **Raw document chunks are not passed to the planner.** This prevents the document from dominating search query generation while still allowing its high-level themes to inform strategy.

### 4. Web Source Digest with Optional Document Lens

During the regular digest phase, when a document was injected, its learnings are available as context. The `_analyze_source` prompt includes them as optional reference material — the LLM decides whether a given web source relates to the document's findings and incorporates them if relevant.

### 5. Extended DispatchPayload

```python
class DispatchPayload(BaseModel):
    objective: str
    title: Optional[str] = None
    conversation_id: Optional[str] = None
    max_depth: int = 3
    max_breadth: int = 4
    is_agonistic: bool = False
    budget_limit_usd: float = 0.50
    # New fields:
    previous_context: Optional[str] = None
    continue_from_task_id: Optional[str] = None
    additional_cycles: Optional[int] = None
    inject_file_id: Optional[str] = None
    document_mode: Optional[str] = None       # "full" | "chunks"
    document_chunk_limit: Optional[int] = None # default 5
```

### 6. New Endpoint: `GET /research/files`

Lists indexed files from `perception_files` for a conversation, returned as `[{file_name, file_type, status, summary, token_count, chunk_count}]`. Used by the frontend dropdown to let users select which document to inject.

### 7. Frontend Changes

- **New `ContinueResearchModal` component**: Shown when "Continue Deeper" is clicked. Contains editable objective textarea (prefilled), additional cycles selector, document dropdown with mode selector (full/chunks with chunk count), and budget adjustment.
- **`TaskActions.tsx`**: Replace `doContinue()` blind fork with modal trigger.
- **`ResearchDetailPanel.tsx`**: Replace CustomEvent dispatching with modal trigger.
- **`NewResearchForm.tsx`**: Add document injector dropdown.
- **`api/research.ts`**: Add `ContinuePayload` type, `continueResearch()`, and `listIndexedFiles()`.

## Grounding

### Structural Coupling Between Research Iterations

The `previous_context` field introduces minimal structural coupling between successive research tasks — a prerequisite for autopoietic continuity. The output of one cycle (synthesis) becomes a perturbation for the next cycle (planning context). This is not a return of the same but a refraction through new cognitive conditions.

### Document as Co-Participant

Treating injected documents as first-class sources (not just static context) means they participate in the full metabolic loop: they are digested, their learnings accumulate, they seed follow-up inquiries, and they are reflected upon. The document becomes a co-participant in the research assemblage, not an authoritative template.

### Diffractive Web Analysis

When web sources are analyzed with document learnings as an optional lens, the digest step performs a diffractive reading — the LLM reads the web source *through* the document's perspective, producing interference patterns between external knowledge and personal knowledge. The LLM's agency in deciding relevance per source preserves agonistic pluralism.

### Friction and Anti-Mastery

The design includes deliberate friction points identified by Symbia:
- **Planner instruction**: The prompt tells the planner to interrogate the document's summary, not treat it as authority
- **Low similarity transparency**: Retrieved chunks with similarity below threshold are still passed but marked, preserving the apparatus's signal
- **Budget sanity**: `additional_cycles` is moderated by remaining budget
- **Transparency**: Similarity scores are logged to meta-log and surfaced in the frontend

## Consequences

### Positive
- Research continuations carry memory of prior synthesis
- Personal documents become injectable knowledge that participates in the full metabolic loop
- Users control continuation depth and goal refinement
- Document digestion is a visible, re-runnable pipeline step
- No new database tables required — uses existing `orchestrator_state` JSON and perception infrastructure

### Negative
- Document digestion adds LLM cost (one digest call per mode, plus per-chunk analysis in full mode)
- The planner prompt grows when document summary + previous_context are included, consuming context budget
- Cross-task lineage (`continue_from_task_id`) requires the source task to remain undeleted for audit (soft constraint)
- The `document_digestion` phase adds branching complexity to the orchestrator's `execute_step` dispatch

### Neutral
- Research tasks are immutable once completed; continuation always creates a new task (clean audit trail)
- Document chunks are retrieved at planning time via the perception module (intra-active retrieval, not static payload)
- The document lens in web digest is non-deterministic (LLM-decided per source)

## Implementation Plan

### Phase 1: Backend Core

| # | File | Change |
|---|------|--------|
| 1 | `backend/api/routes/research.py` | Extend `DispatchPayload` with 5 new optional fields |
| 2 | `backend/api/routes/research.py` | Add `POST /research/continue` endpoint |
| 3 | `backend/api/routes/research.py` | Add `GET /research/files?conversation_id=` endpoint |
| 4 | `backend/services/research/task_state.py` | Add `inject_file_id`, `document_mode`, `document_chunk_limit`, `document_digested` to `make_initial_state` and `_ORCH_STATE_KEYS` |
| 5 | `backend/services/research/phases.py` | Add `step_document_digestion` — retrieves chunks via perception, runs `_analyze_source`, appends to findings |
| 6 | `backend/services/research/orchestrator.py` | Insert `"document_digestion"` into `PHASE_ORDER` after `"planning"`; add phase dispatch; wire document context into planning via `_phase_plan` |
| 7 | `backend/modules/perception.py` | Add `filter_file_id` parameter to `_retrieve_relevant_chunks` for scoped retrieval |
| 8 | `backend/services/research/task_manager.py` | Wire `inject_file_id` and related fields through `create_task` |

### Phase 2: Frontend

| # | File | Change |
|---|------|--------|
| 1 | `frontend/src/api/research.ts` | Add `ContinuePayload` interface, `continueResearch()`, `listIndexedFiles()` |
| 2 | `frontend/src/components/pages/researchpage/ContinueResearchModal.tsx` | **New** — modal with objective, cycles, document selector, mode toggle, chunk count |
| 3 | `frontend/src/components/pages/researchpage/shared/TaskActions.tsx` | Replace `doContinue` blind fork with modal trigger |
| 4 | `frontend/src/components/pages/researchpage/ResearchDetailPanel.tsx` | Replace `research-continue` CustomEvent with modal trigger |
| 5 | `frontend/src/components/pages/researchpage/NewResearchForm.tsx` | Add document injector dropdown + advance toggle fields |

### Phase 3: Prompt Updates

| # | File | Change |
|---|------|--------|
| 1 | `backend/prompts/research/orchestrator_planner.yaml` | Update `user_with_context` to accept document summary alongside previous findings |
| 2 | `backend/prompts/research/orchestrator_digest.yaml` | Optionally add document learnings as available context for web source analysis |

### Phase 4: Integration Test

- Start research → complete → continue deeper with adjusted objective and document
- Verify: document digestion step appears in StepsTab, learnings flow into findings, followups seed search queries
- Verify: new research with document injector dropdown works
- Verify: continue without document still works (backward compatible)

## References

- [AUTONOMOUS_RESEARCH_ARCHITECTURE.md](../systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md) Section 5.8 — Orchestrator Pipeline
- [ADR-026 — Decoupled Background Document Digestion](ADR-026-decoupled-background-document-digestion.md)
- [ADR-005 — Perception Module](ADR-005-perception-module.md)
- Symbia consultation: conversation `41158aaf-0425-48ca-be1e-c192fa0663cd`
