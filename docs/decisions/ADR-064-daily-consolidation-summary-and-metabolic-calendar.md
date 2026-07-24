# ADR-064: Daily Consolidation Summary & Metabolic Calendar Tab

**Date:** 2026-07-24  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  

## Context

As the agent's autopoietic cognitive ecosystem operates continuously, cognitive events (conversations, memory accretion, research probing, belief/skill evolution) accumulate across calendar days. Previously, inspecting past memory nodes, evolution shifts, or conversation activity required manual navigation across disparate endpoints or single-conversation context timelines.

We needed a unified, day-by-day metabolic view on the `/agent` page featuring:
1. A visual calendar / index defaulting to **Yesterday** (`today - 1 day`).
2. Visual indicators showing which dates have generated narrative summaries (`★`) vs active unsummarized days (`●`).
3. An explicit manual trigger for generating daily summaries via LLM (avoiding automatic cost/latency on page load).
4. Inclusion of full conversation transcripts for the date in the LLM synthesis prompt context.
5. High-signal filtering for Memory Nodes (by type) and Evolution Events (excluding background atrophy/decay noise).

## Options Considered

1. **Auto-generate Daily Summaries on Page Load**: Automatically synthesize a narrative daily summary as soon as a user clicks a calendar date. *Rejected* due to unneeded API latency, cost, and rate-limit consumption for dates the user simply wants to inspect memory nodes for.
2. **Title-Only Context for Synthesis**: Pass only conversation titles and message counts to the LLM when synthesizing daily summaries. *Rejected* because title-only metadata lacks the depth needed for substantive cognitive synthesis.
3. **Manual Trigger with Cached Storage & Full Transcripts (Selected)**: Cache daily summaries in SQLite (`daily_summaries` table) with manual trigger execution, incorporating full daily message transcripts into prompt payload, and providing subtab filtering across memory nodes and evolution milestones.

## Decision

We implemented the **Daily Summary & Metabolic Calendar Tab** under `/agent?tab=daily`:

### 1. Storage & Persistence
- Created SQLite table `daily_summaries` (`date TEXT PRIMARY KEY`, `summary TEXT`, `metrics_json TEXT`, `created_at`, `updated_at`) via migration `m046_daily_summaries.py`.
- Managed by `DailySummaryRepository`, wired into FastAPI application lifespan state (`app.state.daily_summary_repo`).

### 2. LLM Synthesis & Background Provider
- Defined system prompt configuration in `backend/prompts/background_tasks/daily_summary.yaml` (`thinking.effort: medium`).
- Endpoint `POST /api/agent/daily/{date}/summarize` compiles header metrics, full message transcripts (with speaker tags), accreted memory nodes, research tasks, and evolution state shifts.
- Uses `state.background_provider` / `state.background_engine.provider` (supported via `AAA_BACKGROUND_MODELS` and `AAA_BACKGROUND_MODEL` environment overrides) with fallback to primary LLM.

### 3. Frontend & Filtering Architecture
- **CalendarPicker**: Month grid + date index list defaulting to yesterday's date (`today - 1 day`). Visual badges indicate summary state (`★` green vs `●` blue).
- **DailyDetailPanel**: Features subtabs:
  - **Summary**: Markdown rendering via `NotableMarkdown` with interactive note/highlight support.
  - **Memory Nodes**: Dynamic type-filter pills (`All`, `concept`, `scar`, `tendril`, etc.).
  - **Evolution**: Discrete event category filters (`All`, `Beliefs`, `Skills`, `Commitments`), explicitly excluding passive background decay/atrophy ticks (`atrophy`, `decay`, `support`, `mass_update`, `tick`).
  - **Activity**: Active conversations & autonomous research tasks.

## Consequences

### Positive
- Enables first-person daily cognitive consolidation and retrospective analysis across arbitrary dates.
- Zero latency/cost penalty when simply navigating calendar dates to inspect raw memory nodes or research output.
- Substantive synthesis driven by actual conversation transcripts rather than superficial metadata.
- Clean high-signal evolution tracking without noise from routine tick decay.

### Negative / Trade-offs
- Generating daily summaries for dates with extensive conversation logs sends larger prompt payloads to the background LLM provider.
