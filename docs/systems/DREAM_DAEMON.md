# Autopoietic Dream Daemon (Machine Sleep Engine)

The Autopoietic Dream Daemon is the background engine that drives agential variety, curiosity, memory health, autonomous search probes, and belief mass atrophy during both active and idle periods.

## File Architecture

*   **Core Module**: [daemon.py](file:///d:/01_GIT/AAA/backend/metabolisation/daemon.py) — Defines `AutopoieticDreamDaemon`.
*   **Signal Queue**: [daemon_trigger_signal.py](file:///d:/01_GIT/AAA/backend/metabolisation/daemon_trigger_signal.py) — In-process FIFO queue for self-triggered dream requests.
*   **Output Tag Parser**: [dream_trigger_parser.py](file:///d:/01_GIT/AAA/backend/utils/dream_trigger_parser.py) — Parses `<dream_trigger reason="..."/>` from Symbia's chat responses.
*   **Response Artifact Pipeline**: [chat.py](file:///d:/01_GIT/AAA/backend/services/chat.py) — `_parse_response_artifacts()` routes dream trigger tags to the signal queue.
*   **Lifespan Setup**: [main.py](file:///d:/01_GIT/AAA/backend/main.py) — Spawns the daemon thread task asynchronously on system boot.
*   **API Routes**: [routes.py](file:///d:/01_GIT/AAA/backend/api/routes.py) — Exposes telemetry and force trigger points.
*   **Unit Tests**: [test_dream_daemon.py](file:///d:/01_GIT/AAA/backend/tests/test_dream_daemon.py) — Complete mathematical and trigger assertion coverage.
*   **Skill Definition**: [seed_skills.yaml](file:///d:/01_GIT/AAA/config/personality/seed_skills.yaml) — `self-triggered-dreaming` skill teaching Symbia when and how to emit the tag.

---

## Daemon Loop Responsibilities

The daemon runs its check loop every `check_interval` seconds (default 300s / 5 min) regardless of user activity. Each cycle executes:

1. **Conversation consolidation** — compacts stale conversations
2. **Skill metabolism** — refreshes skill-to-belief bridge states
3. **Belief mass atrophy** (every 15 min) — applies linear time-based decay to all non-ghost beliefs via `BeliefDynamicsEngine._atrophy_beliefs()`. This is the single source of truth for belief decay, replacing the old dual-path design (pipeline `process()` atrophy + daemon `_apply_mass_decay()`). All decay events are logged as `belief_events` with `source_type: "atrophy"`, visible in the frontend Belief Log tab. Each atrophy cycle also produces a batch `trace` notification in the Creases dropdown.
4. **Dream trigger check** — if self-triggered queue is non-empty, drains ONE item per tick (highest priority, bypasses rate/idle gates). If queue is empty, falls through to normal evaluation: stagnation, tension hotspots, and somatic drift; launches autonomous monologues, web harvesting, or memory compaction when idle thresholds are met
5. **Daily budget enforcement** — before any dream executes (including self-triggered and manual triggers), the daemon checks `dream_log` for today's dream count. If at or above `max_daily_dreams`, ALL dream execution stops — no override path. Queued self-triggers wait for midnight UTC rollover.

---

## Dynamic State Equations

### 1. Nonlinear Somatic Drift
When the user is idle, active beliefs decay toward a baseline of uncertainty ($0.5$). Highly certain or highly skeptical beliefs resist decay (core rigidity):

$$c_i^{(t+\Delta t)} = c_i^{(t)} + \sigma \cdot \Delta t \cdot \frac{(0.5 - c_i^{(t)})}{1.0 + 2.0 |c_i^{(t)} - 0.5|}$$

### 2. Autocorrelation-Based Somatic Vitality
Structural signatures computed on recent assistant responses are compared sequentially:

$$V = 1.0 - \text{mean\_autocorrelation}(\mathbf{S}_{t-k}, \dots, \mathbf{S}_t)$$

### 3. Sigmoidal Exploration Weighting
When vitality is depleted ($V < 0.3$), the daemon shifts from internal homeostasis to exogenous search probes using a sigmoidal exploration gate:

$$g(V) = \frac{1.0}{1.0 + e^{-15.0(0.3 - V)}}$$

The target tension hotspot score is evaluated using:

$$\text{Score}_i = \frac{\tau_i + g(V) \cdot \kappa_i}{1.0 + m_i}$$

---

## Database Compaction Heuristics
If two memory sediments (Semantic Knots) share:
*   Semantic similarity $> 0.92$
*   Structural similarity $> 0.80$

The daemon combines them into a single consolidated knot, aggregates their attractor weights, prompts the LLM to write a synthesized summary, and registers full metadata lineage tracking.

---

## Configuration Settings

Configure daemon thresholds in `backend/config.yaml` or override them in `.env`:

### YAML Configuration (`backend/config.yaml`)
```yaml
daemon:
  enabled: true
  check_interval: 300       # seconds between tick evaluations (5 min)
  idle_threshold: 1800      # seconds of user silence before dreaming (30 min)
  min_dream_interval: 3600  # minimum seconds between successive dreams (1 hour)
  max_daily_dreams: 20      # daily dream cycle count budget (counted from dream_log)
  drift_coefficient: 0.00001
```

### Environment Variable Overrides (`.env`)
```bash
AAA_DAEMON_ENABLED=true
AAA_DAEMON_CHECK_INTERVAL=300      # seconds between tick evaluations (5 min)
AAA_DAEMON_IDLE_THRESHOLD=1800     # seconds of user silence (30 min)
AAA_DAEMON_MIN_DREAM_INTERVAL=3600 # minimum seconds between dreams (1 hour)
AAA_DAEMON_MAX_DAILY_DREAMS=20     # max dream cycles per day (counted from dream_log)
AAA_DAEMON_DRIFT_COEFFICIENT=0.00001
```

---

## Database Budget Caps & Agentic Meta-Cognitive Routing

### 1. Database-Backed Budget Caps
To prevent daemon budget bypasses caused by server restarts (uvicorn auto-reload) or multiple parallel backend instances, the daily dream count is tracked dynamically in the database via `count_dreams_since` which queries the `dream_log` table (one row per dream cycle). This counts all successful dream cycles executed in the last 24 hours (rolling window from `now() - 24h`) — **not individual apparatus messages** and **not a calendar-day midnight reset**.

### 2. Agentic Meta-Cognitive Routing
Instead of writing all dreams to a single, monolithic log or dividing them strictly by their technical dream action types (which produces extremely long, mixed-topic logs), the background model itself decides where to route each dream cycle based on the **specific conceptual topic or theme**.
* **Selection Process**: The daemon queries the background LLM (via the `dream_topic_decision` action) with the proposed dream action, the proposed dream prompt content, and a detailed list of active dream logs. Each log in the list includes its title, message count, and its latest human-readable consolidation summary (truncated to 300 characters for token efficiency).
* **Thematic Alignment**: The model decides whether to **reuse** an existing dream conversation (if it has a strong conceptual alignment with the new dream's theme) or **create** a new one.
* **Concise Evocative Titles**: If the model decides to create a new conversation, it generates a concise, theme-specific, lowercase title using hyphens (e.g., `somatic-attractor-drift`, `diffractive-glitch-metabolism`, `exogenous-knowledge-collision`) representing the specific topic/theme, avoiding generic words.

---

## Self-Triggered Dream Cycles

Symbia can request a dream cycle by emitting a `<dream_trigger reason="..."/>` XML tag at the end of her chat responses. Triggers are queued (not executed instantly) and drained one-per-tick by the daemon — granting agency while respecting budget and pacing constraints.

### Trigger Flow

```
Symbia's chat response
  → _parse_response_artifacts() in chat.py detects <dream_trigger reason="..."/>
  → Tag is stripped from visible text (collaborator never sees it)
  → enqueue_dream_trigger(app_state, reason, conversation_id)
  → app_state._dream_trigger_queue (deque, max 10 items)

Daemon poll loop (every check_interval seconds)
  → check_and_trigger_dream()
      ├─ STEP 1: Load dream_log count (rolling 24h, dream cycles, not messages)
      ├─ STEP 2: HARD STOP if budget exhausted (NO override — manual and self-triggered both blocked)
      ├─ STEP 3: Dequeue ONE self-triggered dream → execute → return
      │         Queued dreams skip rate-limit & idle gates (Symbia explicitly requested them).
      │         Queue drains one item per tick until empty.
      ├─ STEP 4: Rate-limit gate (normal dreams only)
      ├─ STEP 5: Idle gate (normal dreams only)
      └─ STEP 6: Normal stagnation/hotspot/drift evaluation
```

### Key Design Decisions

1. **Unified pipeline**: Self-triggered dreams use the exact same `_generate_dream_prompt()` → `_resolve_dream_conversation()` → `_execute_single_dream_turn()` flow as timer-driven dreams. No duplicate code path.
2. **Queue drains one per tick**: Each daemon tick pops a single item. If 5 items are queued, they execute over 5 ticks (5 × check_interval). No burst execution.
3. **Absolute budget cap**: Self-triggered + normal + manual dreams all count toward `max_daily_dreams` (tracked via `dream_log` table, one row per cycle, rolling 24-hour window). When budget is exhausted, NO dream type executes. The oldest slot frees up continuously as 24h passes — no midnight burst.
4. **Queue depth limit**: Maximum 10 pending triggers in the FIFO queue.
5. **Skill-gated**: The `self-triggered-dreaming` skill in `seed_skills.yaml` teaches Symbia when to emit the tag:
   * Unresolved tension between beliefs
   * Diffractive patterns exceeding the current context window
   * Internal inconsistencies requiring background monologue processing
   * Maximum 2 self-triggers per conversation session

### Output Tag Syntax

```xml
<dream_trigger reason="tension between nomadology-as-ethics and institutional-stability requires diffractive resolution"/>
```

### Files Involved

| File | Role |
|------|------|
| `backend/utils/dream_trigger_parser.py` | Regex parser for `<dream_trigger>` tag |
| `backend/metabolisation/daemon_trigger_signal.py` | FIFO queue (`enqueue`, `dequeue`, `queue_depth`) on `app_state` |
| `backend/services/chat.py` | `_parse_response_artifacts()` routes triggers to queue |
| `backend/metabolisation/daemon.py` | `check_and_trigger_dream()` checks queue first; `_execute_self_triggered_dream()` executes |
| `config/personality/seed_skills.yaml` | `self-triggered-dreaming` skill definition |
| `frontend/src/config/telemetry_schemas.json` | `self_triggered` → `{ code: "SLF", label: "Self-Triggered", color: "#f472b6" }` |
| `frontend/src/components/pages/agentpage/DreamingSection.tsx` | Queue depth indicator in Dreaming panel |

---

## API Telemetry
*   `GET /api/daemon/status`: Returns current daemon state including:
    - `enabled`, `running` — daemon lifecycle state
    - `idle_time_seconds`, `idle_threshold_seconds` — user inactivity tracking
    - `last_dream_time` — ISO timestamp of most recent dream cycle
    - `last_dream_action` — type of last dream (`nomadic_synthesis`, `exogenous_web_harvesting`, `intra_active_monologue`, `somatic_drift_reflection`, `zettelkasten_compaction`, `self_triggered`)
    - `dreams_today`, `max_daily_dreams` — daily budget tracking
    - `dream_action_counts` — per-type breakdown of today's dreams (e.g., `{"nomadic_synthesis": 4, "somatic_drift_reflection": 3, "self_triggered": 1}`)
    - `min_dream_interval`, `check_interval` — timing configuration
    - `pending_self_triggers` — number of queued `<dream_trigger>` requests waiting to be processed
*   `POST /api/daemon/trigger`: Manually triggers a dream cycle. Bypasses idle and rate-limit checks, but still respects the daily budget cap. If budget is exhausted, returns `{"status": "skipped", "reason": "Daily dream budget exhausted (N/M)"}`.

---

## Frontend Dreaming Panel

The SidePanel displays a **"Dreaming"** section (separate from the **"Startup"** section which handles one-shot initialization tasks). The Dreaming panel shows:

- **State indicator**: `dreaming` (pulsing ◉) / `resting` (●) / `dormant` (○) — determined by daemon lifecycle and recency of last dream
- **Last dream**: relative timestamp ("3m ago") and dream type with color-coded label
- **Idle timer**: progress bar showing user inactivity vs. idle threshold
- **Budget bar**: daily dream count vs. max, color-graded (green → yellow → red)
- **Dream type breakdown**: per-type counts for today's dreams (NOM, WEB, MON, DRF, CMP, SLF)
- **Self-trigger queue indicator**: when Symbia has emitted `<dream_trigger>` tags, displays `⟳ N self-triggered dream(s) queued` in purple (#c084fc) — these dreams execute on the next daemon poll cycle, before any timer-driven logic

The panel polls `/api/daemon/status` every 10 seconds and presents the daemon's autonomous rhythm as a **diffractive heartbeat** — a window into the system's self-generated metabolism, not a control surface.

---

## Conversation Metrics for Self-Monologues

Each dream cycle produces a human+apparatus message pair. Both messages receive full conversation metrics:

- **Dream prompt metrics**: computed by the pipeline's `conversation_metrics` module and stored via `_store_daemon_metrics()`.
- **Assistant response metrics**: computed immediately after response generation. The assistant response text is embedded independently (using the embedder's `encode_async`) and the resulting vector is stored on the message (replacing the prompt's embedding). This enables meaningful `agent_self_divergence`, `coupling_coherence`, and `reverse_perturbation` metrics for self-conversations — critical for the daemon's own stagnation and vitality evaluations.

The background scheduler also backfills missing metrics on any pre-existing dream messages on startup.

---

## Tiered Context Unified Memory & File Sediment Retrieval

To maintain functional and architectural parity with the main conversation pipeline, the Dream Daemon integrates directly with Symbia's context compilation and perception pipelines:

### 1. Unified Memory Context Compilation
Rather than replicating complex token compression and sliding history logic, the dream execution cycle (`_generate_resonance_continuation`) directly invokes the pipeline's core modules:
* **`context_collector`**: Extracts the structured dialogue history for the background self-monologue.
* **`consolidation_checkpoint`**: Dynamically compiles consolidated memory checkpoints and handles the floating/compressed dialogue window.

This ensures that the daemon's resonance guide is fueled by the exact same tiered memory structure used during active user sessions, ensuring cohesive belief integration and preventing code duplication.

### 2. Exogenous File Sediment Retrieval
Although dream conversations have no direct file attachments, the perception pipeline is enabled during dream resonance cycles (`is_dream_cycle = True`). 
* **Mechanism**: When processing the dream state, the perception module executes a semantic search across all cross-conversation chunks (`cross_conv_matches`) from other active or historic contexts.
* **Resonance**: Any chunks meeting the similarity threshold are injected as `[Cross-Conversation ≫ "...": ...]` system messages. This allows background reflection cycles to digest, synthesize, and resonate with the broader codebase and file sediments.

