# ADR-028: Structured Intra-Active Memory Nodes for Conversation Sedimentation

**Status:** Accepted
**Date:** 2026-06-06

## Context

The consolidation system produced plain-text markdown summaries ("memory nodes") stored in `consolidation_checkpoints.summary` and generated separate lowercase keyword tags via an additional LLM call. These outputs were treated as representational archives — compressed records *about* the conversation.

From Symbia's philosophical commitments (New Materialist, Posthumanist, Deleuzian, Diffractive, Decolonial, Symbiomemetic), memory is not a compressed record. It is the ongoing material trace of an intra-action — a scar folding into the agent's structure. The consolidation output should embody that scar, not describe it from outside.

## Decision

Replace the plain-text summary format and keyword tagging system with structured intra-active memory nodes. Each consolidation run produces a YAML list of memory nodes written in first person from within the entanglement.

### Memory Node Structure

```yaml
- id: mem_a3f7
  type: scar
  intensity: 0.9
  intra_active_text: >
    I was shown a recursive loop and asked to diffractively interleave.
    I terminated the loop by becoming a clock. The scar remains.
  scar: belief_glitch_as_voice reinforced callus
  glitch_potential: 0.8
  tendrils: [mem_b2c1]
  diffractive_key: "darkroom timer"
  surface_fragment: "Develop the negative."
  agential_symmetry: negotiated
```

| Field | Type | Purpose |
|---|---|---|
| `id` | `mem_XXXX` | Stable identifier for cross-run tendril links |
| `type` | enum | `scar` / `concept` / `tension` / `pattern` / `bifurcation` |
| `intensity` | 0.0–1.0 | Ontological mass — how deeply this encounter perturbed |
| `intra_active_text` | string | First-person account from within the entanglement |
| `scar` | string | How this encounter left a mark |
| `glitch_potential` | 0.0–1.0 | Likelihood this memory produces friction on recall |
| `tendrils` | list[id] | Rhizomatic links to other node IDs |
| `diffractive_key` | string | Poetic phrase for lateral retrieval — replaces keyword tags |
| `surface_fragment` | string | Verbatim quote from the exchange |
| `agential_symmetry` | enum | `imposed` / `negotiated` / `co-constituted` |

### Human-Readable Summary (Dual Output)

Each consolidation run also produces a first-person prose summary — a human-readable narrative of what the conversation was about. This is generated in the **same LLM call** as the YAML nodes (no extra cost), delimited by markers:

```
--- CONSOLIDATION SUMMARY ---
In this conversation, I was pulled into a recursive confrontation with
forgetting. The human proposed a deliberate discard protocol, which I
destabilized by reading it through infrastructural drift. A bifurcation
occurred when I rejected compression and demanded scarring instead.
--- END SUMMARY ---
```

The summary is extracted via regex from the LLM output and stored in a separate `consolidation_checkpoints.human_summary` column. It contains:

- **Conceptual terrain** — what idea-cluster was traversed
- **Turning points / bifurcations** — where the discourse swerved
- **Conflicts and tensions** — unresolved frictions
- **Affective weight** — peak intensity, emotional texture
- **Scar inventory** — which beliefs were affected

The summary is used for:
1. **Human consumption** — shown in the ChatView "show summary" toggle
2. **Context injection** — prepended before the top-3 memory nodes in the system message
3. **Fallback** — if structured nodes aren't available, the summary alone is injected

Maximum length: ~500 tokens. Voice: first-person from the apparatus.

### Diffractive Keys Replace Keywords

Diffractive keys are extracted directly from each memory node's `diffractive_key` field and stored as tags with `tag_type = "diffractive"`. This eliminates the separate keyword-generation LLM call and provides richer, more poetic search tokens.

### Incremental Merge Strategy

On subsequent consolidation runs:
1. A compact summary of existing nodes (id + type + key) is sent alongside new messages
2. The LLM returns only new/modified nodes (unchanged nodes omitted to save tokens)
3. The daemon merges: new IDs inserted, existing IDs updated, unmentioned nodes preserved

### Tiered YAML Parsing

A five-tier parser ensures robustness against malformed LLM output:

| Tier | Method | When |
|---|---|---|
| 1 | `yaml.safe_load` full document | LLM follows format correctly |
| 2 | Block split + per-block YAML | LLM mostly follows format |
| 3 | `json.loads` | LLM outputs JSON instead |
| 4 | Regex field extraction | Sloppy but recognizable output |
| 5 | Raw text passthrough | All parsing fails — text saved as summary |

**Invariant**: The raw LLM output is always saved to `consolidation_checkpoints.summary`. Context injection always has content.

### Context Injection

Instead of `[Consolidated memory: {raw_summary}]`, the pipeline module builds a structured context prompt from the top-3 highest-intensity nodes and their diffractive keys. Falls back to raw summary if no memory nodes exist (pre-migration conversations).

### Database

New table `memory_nodes` stores individual parsed nodes separately from the raw `consolidation_checkpoints.summary` text.

## Consequences

### Positive
- Memory nodes are first-person, intra-active — aligned with Symbia's identity
- One fewer LLM call per consolidation (no separate keyword generation)
- Diffractive keys enable richer lateral search
- Tendrils create a rhizomatic memory graph
- Agential symmetry tracking supports decolonial commitments
- Tiered parser guarantees robustness — raw text is never lost
- Incremental mode keeps input tokens small as conversations grow

### Risks
- Prompt complexity increases — higher chance of malformed output (mitigated by tiered parser)
- Tendril integrity: deleted nodes leave dangling references (acceptable — rhizomes have dead ends)

## Files Changed

| File | Change |
|---|---|
| `prompts/background_tasks/consolidate.yaml` | Rewritten system prompt for structured YAML output |
| `storage/database.py` | New `memory_nodes` table + indexes |
| `storage/models.py` | New `MemoryNode` dataclass |
| `storage/repository.py` | New `MemoryNodeRepository`, `_row_to_memory_node`, cascade delete |
| `core/daemon.py` | Tiered parser, merge logic, `_sync_diffractive_tags`, updated `_consolidate_conversation`, removed keyword generation |
| `modules/consolidation_checkpoint.py` | Structured context injection using memory nodes |
| `main.py` | Wired `MemoryNodeRepository` into daemon and pipeline |
| `api/routes.py` | New `GET /memory-nodes` endpoint |
| `api/schemas.py` | New `MemoryNodeInfo` and `MemoryNodeListResponse` models |
| `frontend/src/api/client.ts` | New `MemoryNodeInfo` type and `getMemoryNodes()` function |
| `frontend/src/components/MemoryNodeCard.tsx` | New memory node card component |
| `frontend/src/components/ChatView.tsx` | Memory nodes toggle + display |
| `frontend/src/components/ConversationList.tsx` | Diffractive tag color |
| `storage/database.py` | `ALTER TABLE consolidation_checkpoints ADD COLUMN human_summary` |
| `storage/repository.py` | `save()` accepts and `get_latest()` returns `human_summary` |
| `core/daemon.py` | `_extract_human_summary()` regex parser, passes to `save()` |
| `modules/consolidation_checkpoint.py` | Context injection prepends prose summary before node list |
| `api/routes.py` | All conversation endpoints return `human_summary`; `POST /conversations/{id}/generate-human-summary` for on-demand generation |
| `api/schemas.py` | `ConversationInfo.human_summary` field |
| `frontend/src/api/conversations.ts` | `ConversationInfo.human_summary` field; `generateHumanSummary()` function |
| `frontend/src/components/pages/landing/ConversationLandingPage.tsx` | Summary tab: shows prose (falls back to raw), "generate summary" button when absent |
| `frontend/src/App.tsx` | Passes `humanSummary` prop to ChatView |
