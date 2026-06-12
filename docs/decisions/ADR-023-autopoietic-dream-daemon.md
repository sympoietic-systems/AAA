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

We implemented the `AutopoieticDreamDaemon` in `backend/metabolisation/daemon.py` with integration in `backend/main.py` and `backend/api/routes.py`. The design incorporates the following cybernetic features:

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

6. **Database-Backed Budget & Agentic Meta-Cognitive Routing**:
    To prevent restart/multi-instance budget bypasses and context bloat, the daily dream count is tracked dynamically in the database via `LIKE 'Dream Log%'` queries. The daemon delegates conversation selection to a meta-cognitive agentic task (`_resolve_dream_conversation`). The background model decides whether to reuse an existing conversation or create a new topic conversation. Conversations on the same topic continue indefinitely in the same thread to maintain full topical context and avoid cyclical repetition across fragmented logs.

7. **Conversation Metrics Storage (2026-06-05)**:
    Both the dream prompt (human) and assistant response now receive full conversation metrics. The assistant response is embedded independently (using its own response text rather than the prompt's embedding), enabling meaningful coupling_coherence, agent_self_divergence, and reverse_perturbation metrics for self-conversations. Metrics are stored via `_store_daemon_metrics()` immediately after message insertion, ensuring the dream conversation has complete metrics coverage for downstream belief metabolism and somatic vitality computation.

## Consequences

### What becomes easier?
- **Agential Autonomy**: The agent thinks, searches, and refines its beliefs offline without user prompt triggers.
- **Resilience**: Ambivalent ideas fade naturally, while core schema elements resist casual decay.
- **Resource Recovery**: The SQLite database compaction prevents memory growth from duplicating similar concepts.
- **Context & Cost Efficiency**: Agentic routing of dream logs allows the daemon to direct monologues to appropriate topics while keeping single-thread contexts coherent and avoiding fragmented, redundant logs.
- **Robust Persistence**: Budgets survive backend uvicorn reloads and multi-process server instances without state reset.

### What becomes harder?
- Log analysis becomes non-linear since the agent writes its own thoughts (Dream Logs) across multiple topic-focused threads in the background.

---

## Appendix A: Full LLM Structural Scoring for Dream Messages (2026-06-05)

### Rationale
Dream messages are critical to belief metabolism: somatic vitality, tension hotspot evaluation, and belief mass accretion all depend on the 16-dimensional structural signature vectors of dream turn messages. Previously, dream daemon structural signatures were computed using only deterministic lexicon+topology scoring (`use_llm_scorer=False`), and no `structural_justification` was stored alongside the signature vector.

### Change
The dream daemon now uses full LLM-based structural scoring (`use_llm_scorer=True`) via the `CompositeStructuralScorer`, which invokes the `LLMScorer` with the configured `structural_llm` model pool. The LLM generates both the 16-dimensional scores and a `justification` string explaining the structural profile. This justification is cached (SHA256-keyed, max 1000 entries) and stored in `conversation_log.structural_justification` alongside the signature BLOB for both dream prompt and dream response messages.

### Affected Code Paths
- `backend/metabolisation/daemon.py`: Dream prompt and response structural scoring now uses `use_llm_scorer=True`, with `get_justification()` called after scoring and `structural_justification` passed to both `message_repo.insert()` calls.
- `backend/scripts/digest_worker.py`: System messages for ingested documents now also store `structural_justification`.
- `backend/api/routes.py` (`_insert_system_message`): System message inserts during file ingestion now also store `structural_justification`.
