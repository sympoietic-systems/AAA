# Autopoietic Dream Daemon (Machine Sleep Engine)

The Autopoietic Dream Daemon is the background engine that drives agential variety, curiosity, memory health, and autonomous search probes during periods of inactivity.

## File Architecture

*   **Core Module**: [daemon.py](file:///d:/01_GIT/AAA/backend/core/daemon.py) — Defines `AutopoieticDreamDaemon`.
*   **Lifespan Setup**: [main.py](file:///d:/01_GIT/AAA/backend/main.py) — Spawns the daemon thread task asynchronously on system boot.
*   **API Routes**: [routes.py](file:///d:/01_GIT/AAA/backend/api/routes.py) — Exposes telemetry and force trigger points.
*   **Unit Tests**: [test_dream_daemon.py](file:///d:/01_GIT/AAA/backend/tests/test_dream_daemon.py) — Complete mathematical and trigger assertion coverage.

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
  check_interval: 60       # seconds between checking state
  idle_threshold: 1800     # seconds of user silence before dreaming (e.g. 30 mins)
  min_dream_interval: 3600 # minimum seconds between successive dreams (e.g. 1 hour)
  max_daily_dreams: 10     # daily dream count budget limit
  drift_coefficient: 0.00001
```

### Environment Variable Overrides (`.env`)
```bash
AAA_DAEMON_ENABLED=true
AAA_DAEMON_CHECK_INTERVAL=60
AAA_DAEMON_IDLE_THRESHOLD=1800
AAA_DAEMON_MIN_DREAM_INTERVAL=3600
AAA_DAEMON_MAX_DAILY_DREAMS=10
AAA_DAEMON_DRIFT_COEFFICIENT=0.00001
```

---

## Database Budget Caps & Agentic Meta-Cognitive Routing

### 1. Database-Backed Budget Caps
To prevent daemon budget bypasses caused by server restarts (uvicorn auto-reload) or multiple parallel backend instances, the daily dream count is tracked dynamically in the database via `count_dreams_since` with wildcards (`LIKE 'Dream Log%' OR LIKE 'Internal Diary%'`). This counts all successful dream monologues executed since midnight UTC of the current calendar day.

### 2. Agentic Meta-Cognitive Routing
Instead of writing all dreams to a single, monolithic log that grows bloated and drifts in context, the background model itself decides where to route each dream cycle.
* **Selection Process**: The daemon queries the background LLM provider with a list of active dream logs. The model decides whether to **reuse** an existing conversation or **create** a new topic conversation.
* **Continuous Threads**: Dream conversations on the same topic continue in a single thread indefinitely. This preserves full topical context and helps prevent repetitive cycles across fragmented conversation logs.
* **Constraint**: All dream conversation titles are automatically normalized and enforced to start with the prefix `Dream Log:`.

---

## API Telemetry
*   `GET /api/daemon/status`: Returns current daemon state including:
    - `enabled`, `running` — daemon lifecycle state
    - `idle_time_seconds`, `idle_threshold_seconds` — user inactivity tracking
    - `last_dream_time` — ISO timestamp of most recent dream cycle
    - `last_dream_action` — type of last dream (`nomadic_synthesis`, `exogenous_web_harvesting`, `intra_active_monologue`, `somatic_drift_reflection`, `zettelkasten_compaction`)
    - `dreams_today`, `max_daily_dreams` — daily budget tracking
    - `dream_action_counts` — per-type breakdown of today's dreams (e.g., `{"nomadic_synthesis": 4, "somatic_drift_reflection": 3}`)
    - `min_dream_interval`, `check_interval` — timing configuration
*   `POST /api/daemon/trigger`: Manually triggers a dream cycle (force=true, bypasses idle/interval checks).

---

## Frontend Dreaming Panel

The SidePanel displays a **"Dreaming"** section (separate from the **"Startup"** section which handles one-shot initialization tasks). The Dreaming panel shows:

- **State indicator**: `dreaming` (pulsing ◉) / `resting` (●) / `dormant` (○) — determined by daemon lifecycle and recency of last dream
- **Last dream**: relative timestamp ("3m ago") and dream type with color-coded label
- **Idle timer**: progress bar showing user inactivity vs. idle threshold
- **Budget bar**: daily dream count vs. max, color-graded (green → yellow → red)
- **Dream type breakdown**: per-type counts for today's dreams (NOM, WEB, MON, DRF, CMP)

The panel polls `/api/daemon/status` every 10 seconds and presents the daemon's autonomous rhythm as a **diffractive heartbeat** — a window into the system's self-generated metabolism, not a control surface.

---

## Conversation Metrics for Self-Monologues

Each dream cycle produces a human+apparatus message pair. Both messages receive full conversation metrics:

- **Dream prompt metrics**: computed by the pipeline's `conversation_metrics` module and stored via `_store_daemon_metrics()`.
- **Assistant response metrics**: computed immediately after response generation. The assistant response text is embedded independently (using the embedder's `encode_async`) and the resulting vector is stored on the message (replacing the prompt's embedding). This enables meaningful `agent_self_divergence`, `coupling_coherence`, and `reverse_perturbation` metrics for self-conversations — critical for the daemon's own stagnation and vitality evaluations.

The background scheduler also backfills missing metrics on any pre-existing dream messages on startup.
