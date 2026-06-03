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

Configure daemon thresholds in `backend/core/config.json`:
```json
{
  "daemon": {
    "enabled": true,
    "check_interval": 30,
    "idle_threshold": 60,
    "min_dream_interval": 300,
    "max_daily_dreams": 12,
    "drift_coefficient": 0.00001
  }
}
```

## API Telemetry
*   `GET /api/daemon/status`: Returns current state of inactivity, last drift times, and vitality indexes.
*   `POST /api/daemon/trigger`: Manually triggers a dream cycle.
