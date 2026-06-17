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
- **Live input preview** — regenerated on-demand via `⟳ reinitialize` button.
  Fetches fresh prompts from the backend, reflecting any code changes you've made.
- **Logged inputs** — the historical meta-log entries from when the step originally ran.

**Result tab:**
- Step result summary (e.g., "3 queries planned × ~2 depth")
- Source results with learnings and gaps (for digest steps)
- Raw LLM responses in collapsible `<details>` blocks

**Log tab:**
- All other meta-log entries (completions, status updates, errors)

### 5. Reinitialize — Edit Code, See Changes

The debugging loop:
1. Edit backend code (prompt templates, persona builder, tool logic)
2. Click `⟳ reinitialize` on the Input tab to regenerate system/user prompts
3. Review the updated prompts
4. Click `⟳ rerun step` to re-execute that phase with the new code
5. Repeat

### 6. Rerun

- **Per-step:** Click `⟳ rerun step` on any completed step to re-execute that phase
  (resets the task and re-runs up to that phase, preserving the task ID)
- **Full task:** When complete, click `⟳ rerun all` to start the entire pipeline over
- **Clone (retry):** Creates a new task with the same parameters (original task preserved)

## APIs (for reference)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/research/dispatch` | POST | Create a research task |
| `/research/tasks/{id}/run` | POST | Queue → Active (auto mode) |
| `/research/tasks/{id}/step` | POST | Execute next phase (manual mode) |
| `/research/tasks/{id}/rerun` | POST | Reset + re-queue (terminal states) |
| `/research/tasks/{id}/phase` | GET | Current orchestrator phase |
| `/research/tasks/{id}/preview/{phase}` | GET | Prompts/inputs without executing |
| `/research/tasks/{id}/meta-log?branch_id=X` | GET | Per-step meta log |

## Backend Architecture

Key files:

| File | Role |
|------|------|
| `backend/services/research_orchestrator.py` | Phase-based state machine, step execution, preview |
| `backend/services/research_task_manager.py` | Task lifecycle, manual vs auto routing |
| `backend/api/routes/research.py` | REST endpoints for step/run/rerun/preview/log |
| `backend/storage/repositories/research_step.py` | DB step records |
| `backend/storage/repositories/research_meta_log.py` | Per-step traceability log |

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
