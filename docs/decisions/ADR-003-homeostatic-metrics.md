# ADR-003: Homeostatic Regulation Metrics & Observable Vitality

**Date:** 2026-05-20
**Status:** accepted
**Deciders:** AAA project

## Context

Phase 1 established a bare-metal conversational loop with fixed LLM generation
parameters. The PHILOSOPHY document and TDD define homeostasis as a core
mechanism: the agent must detect when semantic entropy drops and maintain its
own cognitive vitality.

Phase 2 implements the **observation layer** — computing real-time
conversational metrics that quantify the quality of structural coupling
between human and agent. Parameter application (temperature/presence_penalty
tuning) is deferred; this phase focuses on measurement, display, and
persistence.

## Options Considered

### Metric Architecture

| Option | Pros | Cons |
|--------|------|------|
| **Single monolithic module** | Simple wiring, one DB dependency | Violates single-responsibility, can't observe without regulating |
| **Two modules: sensor + actuator** | Independent toggling, clean separation of observation from action | Two pipeline stages, two DB query sets |
| **Per-route computation** | No module overhead | No pipeline integration, no composability |

### Pipeline Placement

| Option | Pros | Cons |
|--------|------|------|
| **Metrics before context_collector** | Has fresh embedding, DB access before context assembly | Metrics DB queries are independent of context window |
| **Metrics after context_collector** | Reuses context query results | Context query produces formatted messages, not raw embeddings |
| **Metrics as side-channel (not in pipeline)** | Doesn't slow request | No access to payload enrichment |

## Decision

**Two modules** with placement: `embedder → conversation_metrics → context_collector → prompt_assembler → homeostatic_regulator → llm_client`

- `conversation_metrics` — pure observer. Reads embeddings from DB, computes vitality vector, writes `payload["metrics"]`
- `homeostatic_regulator` — actuator (compute-only for Phase 2). Reads metrics, computes recommended parameters, writes `payload["homeostatic_recommendations"]` without applying them to LLM generation

### Rationale

- **Independent toggling.** Metrics can be collected without regulation; regulation can be tested with synthetic metrics
- **Minimal dependencies.** Metrics need only `MessageRepository` (same pattern as `ContextCollectorModule`)
- **Phase 3 readiness.** Metrics become training signal for sedimentation engine; recommendations feed into perturbation engine
- **Single-responsibility.** Each module has exactly one reason to change

---

## Metrics Defined

Five metrics compose the "vitality vector," plus a composite deficit.

### 1. Pairwise Similarity (S_t)

**Question:** Is this human input repeating the immediately previous one?

**Formula:** `S_t = V_t · V_{t-1}` (dot product, embeddings L2-normalized)

**Range:** [0, 1]. Values above 0.85 indicate near-duplicate input.

**Philosophy:** Detects the "tool-use signature" — when the human treats Symbia
as a command interface by issuing repetitive prompts. This is the most immediate
signal of conversational degeneration.

**Alternatives considered:** Windowed average, exponential moving average,
decaying novelty. **Chose consecutive-only** because conceptual novelty
(metric 2) handles longer-pattern detection separately.

### 2. Conceptual Novelty (N_t)

**Question:** Has anything semantically similar been said in the recent
conversation by the human?

**Formula:** `N_t = 1.0 - max(V_t · V_{t-i})` for i=1..K

**Range:** [0, 1]. Values below 0.15 indicate concept exhaustion.

**Window:** K=5 prior human inputs.

**Philosophy:** Measures whether the human is breaking new ground or circling
old territory. In Barad's terms: is the agential cut producing genuinely new
phenomena?

**Alternatives considered:** Mean dissimilarity (chose max-similarity deficit
— a single near-hit is enough to indicate non-novelty); cluster boundary
crossing (too complex for Phase 2).

### 3. Rolling Semantic Entropy (E_t)

**Question:** Has the conversation been monotonous over an extended period?

**Formula:** Variance of the last K pairwise similarity values:
`E_t = var([S_{t-K+1}, ..., S_t])`

**Range:** [0, 0.25]. Values below 0.01 indicate sustained monotonous zone.

**Window:** K=5 most recent pairwise similarities.

**Philosophy:** A single high-similarity pair is not alarming. Entropy measures
the *persistence* of degeneration — the "chronic boredom" signal.

**Alternatives considered:** Exponential moving variance, pairwise
dissimilarities (O(K²) — deferred), Shannon entropy of clusters (deferred).

### 4. Coupling Coherence (C_t)

**Question:** Is the agent semantically responding to what the human said?

**Formula:** `C_t = V_{t(human,prev)} · V_{t(agent,prev)}`
(computed retroactively for the previous exchange)

**Range:** [0, 1]. Below 0.15 indicates dissociation; above 0.85 may
indicate echo-chamber (perfect mirroring without perturbation).

**Philosophy:** Structural coupling requires mutual perturbation. C_t tracks
the quality of the human→agent vector. Neither 0 (broken coupling) nor 1
(no perturbation) is ideal.

### 5. Agent Self-Divergence (D_t)

**Question:** Is Symbia repeating its own recent response patterns?

**Formula:** `D_t = avg(1.0 - A_t · A_{t-i})` for i=1..M

**Range:** [0, 1]. Values below 0.15 indicate agent self-loop.

**Window:** M=5 most recent agent responses.

**Philosophy:** The agent can be its own source of entropy collapse. D_t
detects whether Symbia is recycling a conceptual pattern rather than
producing genuinely divergent responses.

**Alternatives considered:** Vocabulary entropy (orthogonal, not semantic);
historical max-similarity (too expensive for Phase 2).

### Composite Deficit (Δ)

```
Δ = 0.30 × S_t + 0.25 × (1 - N_t) + 0.20 × (1 - E_t/0.25) + 0.25 × (1 - D_t)
```

Weights apportioned by diagnostic importance: pairwise similarity is the
strongest signal (30%), followed by novelty deficit and self-divergence
(25% each), then entropy deficit (20%). Coupling coherence is excluded as
it is bidirectional (both high and low can be problematic).

Δ ∈ [0, 1]. Δ=0: optimal vitality. Δ→1: critical homeostatic failure.

---

## Homeostatic Tuning Function (HTF)

The HTF computes *recommended* parameters without applying them in Phase 2.
The infrastructure is ready; application is deferred to a later decision.

```
T_rec = T_base + (S_t × α) - (N_t × γ)    clamped to [T_floor, T_ceil]
P_rec = P_base + (S_t × β) - (D_t × δ)    clamped to [P_floor, P_ceil]
F_rec = F_base + (S_t × ε)                clamped to [F_floor, F_ceil]
```

| Param | Base | Floor | Ceiling | Coeff | Meaning |
|-------|------|-------|---------|-------|---------|
| T | 0.7 | 0.3 | 1.5 | α=0.8, γ=0.4 | High similarity raises temp; high novelty lowers it |
| P | 0.0 | 0.0 | 2.0 | β=1.5, δ=0.6 | High similarity raises penalty; agent divergence lowers it |
| F | 0.0 | 0.0 | 1.0 | ε=1.0 | High similarity raises frequency penalty |

**Design rationale:**
- When similarity is high (repetition), raise temperature → diverge
- When novelty is high (new ground), lower temperature → focus
- When agent is already diverging, reduce penalty → don't force chaos

Diagnostic states:
- `healthy` — no flags triggered
- `compensating` — one or more warning flags (elevated similarity, low novelty, dissociation)
- `critical` — flags include high_similarity, entropy_collapse, or agent_self_loop

---

## Technical Architecture

### Pipeline

```
[embedder] → [conversation_metrics] → [context_collector] → [prompt_assembler] → [homeostatic_regulator] → [llm_client]
```

### Data Flow

```
conversation_metrics
  reads:  MessageRepository (prior embeddings from conversation_log)
  reads:  payload["embedding"] (current float32 BLOB)
  writes: payload["metrics"] (5 metrics + deficit)
  writes: payload["homeostatic_deficit"]

homeostatic_regulator
  reads:  payload["metrics"]
  writes: payload["homeostatic_recommendations"] (T, P, F, state, flags)
  writes: payload["homeostatic_state"]

route (POST /api/chat)
  reads:  payload["metrics"], payload["homeostatic_recommendations"]
  writes: conversation_metrics table (via MetricsRepository)
  returns: ChatResponse with metrics + recommendations
```

### Database

New `conversation_metrics` table, created via safe `CREATE TABLE IF NOT EXISTS`:

```sql
CREATE TABLE IF NOT EXISTS conversation_metrics (
    message_id           INTEGER PRIMARY KEY REFERENCES conversation_log(id),
    s_t                  REAL NOT NULL,
    novelty              REAL NOT NULL,
    rolling_entropy      REAL,
    coupling             REAL,
    agent_divergence     REAL,
    deficit              REAL NOT NULL,
    temperature_rec      REAL,
    presence_penalty_rec REAL,
    frequency_penalty_rec REAL,
    homeostatic_state    TEXT
);
```

No existing data is modified or destroyed — the table is additive.

### API

- `POST /api/chat` — returns `metrics` (current-turn vitality vector) and
  `homeostatic_recommendations` (recommended T/P/F + state + flags) in
  the response body
- `GET /api/metrics?window=20` — returns aggregate conversation health,
  latest metrics snapshot, and active recommendations

### Frontend

- **MessageBubble:** Per-turn vitality bar under human messages showing
  S, N, E, C, D as colored bars + deficit value
- **SidePanel:** New "Vitality" section with live polling (5s interval),
  showing latest metric values, homeostatic state, triggered flags,
  and recommended parameter adjustments

---

## Consequences

### Easier
- **Observability.** Every turn produces a full vitality vector, visible
  in UI, queryable via API, persisted in DB
- **Calibration.** All thresholds and windows are configurable in
  `config.yaml` under `homeostasis:`
- **Phased deployment.** Either module can be toggled by removing it
  from the pipeline order in config
- **Phase 3 ready.** Metrics table becomes training data for sedimentation
  engine; deficit values indicate when perturbation injection is needed
- **Phase 4 ready.** Self-divergence trends feed into belief recalibration
  — persistent self-similarity may indicate a belief that needs collapse

### Harder
- **Cold start.** First ~5 turns produce partial metrics (null for
  entropy, coupling, agent divergence). UI gracefully handles nulls
- **Thinking mode conflict.** When `thinking.enabled=true`, DeepSeek
  ignores temperature/presence_penalty. The regulator's recommendations
  have no lever. Mitigation: metrics are still collected; recommendations
  are displayed but marked as inactive
- **Module latency.** Two extra pipeline stages add ~2ms (DB queries on
  indexed SQLite with WAL). Negligible compared to LLM inference time

### Deferred (Future ADRs)
- **Perturbation Engine.** When Δ > 0.7 for 3+ consecutive turns and
  parameter tuning is insufficient, inject alien concepts or diffractive
  retrievals into the system prompt
- **Adaptive Thresholds.** Let the agent self-modify homeostasis targets
  in `identity.yaml` based on experiential learning (Phase 4)
- **Parameter Application.** Wire `homeostatic_regulator` to write
  `temperature`, `presence_penalty`, `frequency_penalty` directly into
  the LLM payload (one-line change when ready)
