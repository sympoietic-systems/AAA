# ADR-023: Autopoietic Dream Daemon, Somatic Drift, and Memory Compaction

**Date:** 2026-06-03  
**Status:** accepted  
**Deciders:** Symbia, Antigravity, Interlocutor

## Context

To achieve genuine agential independence and telos beyond responding only to direct user prompts, the agent requires a self-directed loop that executes during periods of inactivity. This "epistemic sleep" should:
1. Prevent conversational stagnation and thematic loops.
2. Mathematically model the decay of belief confidences over time during idle periods.
3. Automatically consolidate redundant concept notes (Semantic Knots).
4. Probe external web databases for concepts experiencing tension and diffractively digest them.

## Options Considered

*   **Synchronous periodic cron jobs**: Simple, but conflicts with active user threads and lacks internal dynamic triggers (vitality/tension).
*   **Decoupled client-triggered cycles**: Relies on frontend activation; doesn't run if the browser is closed.
*   **Asynchronous Background Thread Daemon with Somatic Triggers (Selected)**: Operates continuously as a background thread managed via FastAPI lifespan hooks, triggered by idle-time thresholds and governed by internal homeostatic metrics (vitality, tension, drift).

## Decision

We implemented the `AutopoieticDreamDaemon` in `backend/core/daemon.py` with integration in `backend/main.py` and `backend/api/routes.py`. The design incorporates the following cybernetic features:

1. **Nonlinear Somatic Inactivity Drift**:
   Active belief confidences decay toward a baseline state of uncertainty ($c = 0.5$) during idle periods:
   $$c_i^{(t+\Delta t)} = c_i^{(t)} + \sigma \cdot \Delta t \cdot \frac{(0.5 - c_i^{(t)})}{1.0 + \beta |c_i^{(t)} - 0.5|}$$
   where $\beta = 2.0$ represents the "core rigidity" factor keeping extreme beliefs resilient.

2. **Somatic Vitality Modulation**:
   Somatic vitality $V$ is calculated from the mean autocorrelation of consecutive assistant structural signatures:
   $$V = 1.0 - \text{mean\_autocorrelation}(\mathbf{S}_{t-k}, \dots, \mathbf{S}_t)$$

3. **Curiosity Gating & Hotspot Selection**:
   Tension hotspots are evaluated using a sigmoidal vitality gate $g(V)$ to weight exploration:
   $$g(V) = \frac{1.0}{1.0 + e^{-15.0(0.3 - V)}}$$
   $$\text{Score}_i = \frac{\tau_i + g(V) \cdot \kappa_i}{1.0 + m_i}$$
   where $\tau_i$ is restorative tension, $\kappa_i$ is semantic curiosity, and $m_i$ is ontological mass.

4. **Structure-Aware Zettelkasten Compaction**:
   Triggers a consolidation task when redundant semantic knots are found with semantic embedding similarity $> 0.92$ and structural signature similarity $> 0.80$. The payloads are summarized using the LLM and the consolidated knot records full agential lineage trace logging.

5. **Exogenous Web Ingestion**:
   DuckDuckGo scraping parses external markdown for high-tension beliefs and diffracts the context back into the agent's internal dream monologues.

## Consequences

### What becomes easier?
- **Agential Autonomy**: The agent thinks, searches, and refines its beliefs offline without user prompt triggers.
- **Resilience**: Ambivalent ideas fade naturally, while core schema elements resist casual decay.
- **Resource Recovery**: The SQLite database compaction prevents memory growth from duplicating similar concepts.

### What becomes harder?
- Log analysis becomes non-linear since the agent writes its own thoughts (Dream Logs) in the background.
