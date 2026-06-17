# Research Manual Mode — Step-by-Step Orchestration

When `AAA_RESEARCH_MANUAL_MODE=true` and orchestrator is enabled,
every research task runs phase-by-phase with human confirmation at each step.
This guide documents the workflow, UI, and debugging loops.

## Enabling

Set in `.env`:
```
AAA_RESEARCH_MANUAL_MODE=true
```

Or in `backend/config.yaml`:
```yaml
research_tasks:
  manual_mode: true
```

The orchestrator must also be enabled:
```yaml
research_orchestrator:
  enabled: true
```

## Orchestrator Phases

The pipeline progresses through 7 phases in order:

| # | Phase        | What it does                                    | DB Step Type     |
|---|-------------|-------------------------------------------------|------------------|
| 1 | Planning     | Generate research plan from objective via LLM   | `plan`           |
| 2 | Searching    | Web search (DuckDuckGo) for query               | `search`         |
| 3 | Parsing      | Fetch all result URLs in parallel               | `parallel_parse` |
| 4 | Digesting    | Analyze each source via LLM (node_analyzer)     | `digest`         |
| 5 | Reflecting   | Multi-round LLM reflection on findings          | `reflect`        |
| 6 | Evaluating   | Hard checks + decision (stop or continue)       | `evaluate`       |
| 7 | Synthesizing | Final synthesis + write result                  | `synthesize`     |

After Evaluating, if completeness is insufficient and depth remains,
the pipeline loops back to Searching for the next depth iteration.

## Workflow

### 1. Dispatch Research

From the Research Console or the agent page, submit a research task.
The task enters `queued` status.

### 2. First Run — Planning

Open the task detail page. The **Steps** tab shows:
- **Left:** Pipeline with `▶ Plan` highlighted as the current phase
- **Right:** Preview panel showing the Plan step's inputs:
  - Objective text
  - Depth, budget, model, temperature, max_tokens
  - System prompt (persona + planner template)
  - User prompt (formatted with parameters)

Click `▶ run` (on the pipeline or Info tab) to execute the planning phase.
The LLM generates a research plan. The phase advances to Searching.

### 3. Step-by-Step Execution

After each phase completes:
- The pipeline shows `✔` for completed phases, `▶` for the current phase
- Click `▶ run` on the current phase to execute it
- Each click runs exactly ONE phase

### 4. Inspecting Steps

Click a completed phase in the pipeline. The right panel shows **3 tabs:**

**Input tab:**
- **Live input preview** — cached after first build.  Opening the tab or switching
  between steps reads from the cache instantly (no LLM call).
- **⟳ reinitialize** button — clears the cache and regenerates prompts from scratch.
  Use this after editing backend code (prompt templates, persona builder, etc.) to
  see updated inputs.
- **Logged inputs** — the historical meta-log entries from when the step originally ran.

**Result tab:**
- Step result summary (e.g., "3 queries planned × ~2 depth")
- Source results with learnings and gaps (for digest steps)
- Raw LLM responses in collapsible `<details>` blocks

**Log tab:**
- All other meta-log entries (completions, status updates, errors)

### 5. Input Caching

Phase inputs (persona context, prompts, search queries, parsed URLs) are cached
in the `cached_inputs` column on `research_tasks` after first computation.
Tab switches and step re-execution reuse the cache — no redundant LLM calls.

The cache is keyed by phase name (`planning`, `searching`, `parsing`, `digesting`,
`reflecting`, `synthesizing`) and stores everything needed to skip the expensive
persona build (16D structural signature, skills, beliefs, commitments).

### 6. Reinitialize — Edit Code, See Changes

The debugging loop:
1. Edit backend code (prompt templates, persona builder, tool logic)
2. Click `⟳ reinitialize` on the Input tab to clear the cache and regenerate
   system/user prompts from scratch
3. Review the updated prompts
4. Click `⟳ rerun step` to re-execute that phase with the new code
5. Repeat

When you reinitialize, the cache is cleared (`cached_inputs = NULL` on the task row)
and the next preview or step execution recomputes everything fresh.

### 7. Rerun

- **Per-step:** Click `⟳ rerun step` on any completed step to re-execute ONLY that phase
  using cached inputs from the database.  Uses `?rerun_step_type=<type>` to fast-forward
  the orchestrator phase without re-running prior steps.
- **Full task:** When complete, click `⟳ rerun all` to start the entire pipeline over
- **Clone (retry):** Creates a new task with the same parameters (original task preserved)

### 8. Server Restart Resilience

Orchestrator in-memory state is lost on restart, but `resume_task()` re-hydrates it
from the database: reads completed steps to determine the next phase, loads the plan
from `research_plans`, and populates caches from `cached_inputs`. The pipeline picks
up right where it left off — no need to cancel and re-queue.

### 9. Thinking Mode (per-request override)

The planner prompt (`orchestrator_planner.yaml`) enables DeepSeek thinking mode via
`thinking: {enabled: true, effort: "high"}`. The orchestrator passes `thinking_override`
to the LLM client, which takes precedence over the global config. Other phases
(synthesize, reflect, digest) run without thinking for speed. Add the same
`thinking:` block to other prompt YAMLs to enable it for those phases too.

## APIs (for reference)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/research/dispatch` | POST | Create a research task |
| `/research/tasks/{id}/run` | POST | Queue → Active (auto mode) |
| `/research/tasks/{id}/step` | POST | Execute next phase. `?rerun_step_type=X` re-runs only that phase |
| `/research/tasks/{id}/rerun` | POST | Reset + re-queue (terminal states) |
| `/research/tasks/{id}/reinitialize` | POST | Clear cached phase inputs |
| `/research/tasks/{id}/phase` | GET | Current orchestrator phase (auto-resumes on restart) |
| `/research/tasks/{id}/preview/{phase}` | GET | Prompts/inputs from cache (no LLM) |
| `/research/tasks/{id}/meta-log?step_id=X` | GET | Per-step meta log (use step_id, not branch_id) |

## Backend Architecture

Key files:

| File | Role |
|------|------|
| `backend/services/research_orchestrator.py` | Phase-based state machine, step execution, preview, resume |
| `backend/services/research_task_manager.py` | Task lifecycle, manual vs auto routing |
| `backend/api/routes/research.py` | REST endpoints for step/run/rerun/preview/log |
| `backend/storage/repositories/research_step.py` | DB step records (includes step_data for LLM responses) |
| `backend/storage/repositories/research_meta_log.py` | Per-step traceability log (step_id column) |
| `backend/prompts/research/orchestrator_planner.yaml` | Planning prompt with thinking mode override |
| `backend/modules/llm_client.py` | LLM client with per-request thinking_override |

## Configuration

```yaml
research_tasks:
  manual_mode: false          # true = queue but don't auto-execute
  max_concurrent: 2
  max_queue_size: 10

research_orchestrator:
  enabled: true
  max_reflect_rounds: 3
  default_top_n: 3
  satisfaction_threshold: 0.7
  early_stop_threshold: 0.8
  max_concurrent_parses: 3
```
