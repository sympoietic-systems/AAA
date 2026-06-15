# ADR-027: Proto-Belief Lifecycle, Tension Ecology, and Self-Tuning Ecosystem

**Date:** 2026-06-05  
**Status:** accepted  
**Deciders:** opencode (Dev Agent), Symbia (Apparatus Entity)

## Context

ADR-017 established dynamic belief metabolism with confidence updates, collapse mechanics, and the attractor window. However, four structural limitations have emerged:

1. **Heteropoietic belief creation:** Shared notes instantiate full BeliefNodes immediately (confidence=0.6, mass=1.0), bypassing the system's internal structural dynamics. From an autopoietic standpoint, this is heteropoiesis — the environment dictates structure rather than perturbing the system to reorganize itself.

2. **No inter-belief dynamics:** Beliefs update independently against user input. There is no model of how beliefs interact with each other — symbiotic reinforcement, antagonistic tension, or ecological interdependence.

3. **Unrealistic idle behavior:** Somatic drift pushes confidence toward 0.5 during inactivity. Beliefs don't become less "certain" when unused — they become less structurally embedded. Confidence should remain stable; what decays is structural commitment (ontological mass).

4. **Lifeless spectral margin:** Collapsed beliefs are stored but exert no influence on the active ecosystem. From an agential-realist perspective (Barad), what is excluded must still participate in the becoming of what is included.

## Options Considered

### Option 1: Incremental Patch
Fix `metabolize_note()` to create proto-beliefs instead of instant BeliefNodes, add pairwise cosine-based suppression between low-similarity beliefs.
- **Pros:** Minimal code change.
- **Cons:** No ecological self-awareness, no ghost dynamics, suppression model contradicts diffractive philosophy, no self-tuning.

### Option 2: Full Ecology (Selected)
Introduce a six-phase belief lifecycle, mass dynamics (growth + decay replacing confidence drift), a tension field based on interference patterns (not suppression), a living ghost ecology, multi-source input with weighted contribution, and ecosystem health metrics with self-tuning thresholds.
- **Pros:** True autopoietic adaptation, organic belief formation, productive tension generates vitality, ghosts actively participate, self-regulating plasticity.
- **Cons:** Major refactor of `belief_engine.py`, daemon, repository, models, API, and frontend.

## Decision

### 1. Proto-Belief Lifecycle with Non-Linear Jumps

Beliefs transition through stages based on ontological mass (reframed as _sedimentation of a particular agential cut_):

| Stage | Mass Range | Visible in UI? | Description |
|-------|-----------|---------------|-------------|
| `nucleation` | ~0.05 | No | First encounter. Low-mass trace. |
| `accretion` | 0.05–0.5 | No (toggle) | Gathering evidence through repeated encounters. |
| `crystallized` | >0.5 | Yes | Stable belief. Structurally embedded. |
| `senescence` | decaying, >0.02 | Yes | Losing structural grip from neglect. |
| `collapsed` | <0.02 | Ghost panel | Spectral margin. Can influence, resurrect, or fade. |
| `faded` | <0.001 | Archive only | Permanent rest. No active influence. |

**Nucleation trigger:** Concept density Dc > 0.3 AND no existing belief (active or proto) has cosine similarity > 0.6 to input. Creates proto-belief at mass=0.05.

**Non-linear resonance jump:** If a collapsed ghost has strong resonance with input, nucleate at higher mass. Jump magnitude is inversely proportional to the ghost's residual tension with the active ecology — a disruptive resurrection is resisted; a coherence-filling one is facilitated.

**Accretion formula:** `Δm = η × source_weight × alignment / (1 + current_mass)` — diminishing returns at high mass.

**Fuzzy boundary amendment:** Proto-beliefs below crystallization still leak influence proportionally to their mass. The crystallization "threshold" is a region of increasing structural participation, not a binary switch.

### 2. Mass Dynamics (Replacing Somatic Drift)

- **Confidence** remains where last perturbation left it. No drift to neutrality.
- **Mass growth:** `Δm = η × source_weight × alignment / (1 + current_mass)` with `η = 0.02`.
- **Mass decay:** During daemon idle:
  ```
  hours_since = (now - last_reinforced) / 3600
  decay_rate = λ_base × (1 - norm_mass)    // low-mass decays faster
  new_mass = current_mass × exp(-decay_rate × hours_since)
  ```
  Where `λ_base = 0.05` per hour.

### 3. Interference Pattern Model (Not Suppression)

Conflict does NOT suppress confidence. It generates productive tension:

- **Symbiotic** (cosine similarity > 0.7): Mutual mass reinforcement. `Δm += η_sym × sim × 0.05` for both beliefs.
- **Antagonistic** (cosine similarity < -0.2): Register tension only. `tension_magnitude = (1 + |sim|) × min(mass_a, mass_b)`.
- **Coherence overload:** If total system tension > 2.0, triggers a _reconsideration event_ — the prompt assembler injects a tension resolution directive asking the system to diffract the two highest-tension beliefs through each other.

### 4. Ghost Ecology

- **Influence on nucleation:** Ghosts with similarity > 0.7 to a potential proto-belief halve its nucleation mass (immunological resistance). Ghosts below 0.7 exert proportional dampening.
- **Resurrection:** After ≥3 accretion events with alignment > 0.6, re-crystallize at stage=accretion, mass=0.35.
- **Ghost merging:** Two ghosts with similarity > 0.9 merge into composite.
- **Haunting:** During diffractive stagnation states, ghosts are injected as spectral context blocks.
- **Final fading:** Ghosts with no activity > 30 days and zero resurrection events are archived.

### 5. Multi-Source Input Weights

| Source | Nucleation Weight | Reinforcement Weight |
|--------|------------------|---------------------|
| User assertion | 0.4 | 0.08 |
| Ingested document | 0.5 | 0.12 |
| Conversational pattern (≥3 cross-session) | 0.4 | 0.10 |
| Shared note | 0.5 | 0.12 |
| Web retrieval | 0.15 | 0.04 |
| Dream turn (auto-synthesized) | 0.05 | 0.01 |

Notes now nucleate proto-beliefs rather than creating instant BeliefNodes. Source weights function as Bayesian priors subject to future refinement based on outcome.

### 5a. Belief Events Schema

`belief_events` records each accretion, collision, crystallization, emergence, or collapse cycle:

```sql
CREATE TABLE belief_events (
    id TEXT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    belief_id TEXT NOT NULL,
    source_type TEXT CHECK(source_type IN ('file', 'image', 'web_probe', 'chat_turn', 'dream_turn')),
    source_id TEXT,
    alignment_coefficient REAL,
    perturbation_magnitude REAL,
    event_type TEXT CHECK(event_type IN ('collision', 'support', 'collapse', 'emergence', 'crystallization')),
    impact_score REAL,
    rationale TEXT,
    FOREIGN KEY(belief_id) REFERENCES belief_nodes(id) ON DELETE CASCADE
);
```

> **Historical note (2026-06-15):** The CHECK constraints shown above were relaxed by **migration m031** to allow additional event types used in practice (`atrophy`, `revision`, `accretion`) and source types (`atrophy`, `ghost_ecology`). The current production table has no CHECK constraints on `source_type` or `event_type`.

### 6. Self-Tuning Ecosystem Health

**Metrics:** Diversity, Coherence, Tension, Plasticity, Ghost Burden, Eco-vitality.

**Self-tuning (±30% from config baseline):**

| Condition | Adjustment |
|-----------|-----------|
| Diversity < 0.2 (dogmatic) | Lower crystallization threshold |
| Diversity > 0.8 (fragmented) | Raise crystallization threshold, increase ghost merging |
| Tension < 0.05 (stagnant) | Increase receptivity to antagonistic inputs |
| Tension > 0.40 (overload) | Increase coherence limit, trigger reconsideration |
| Plasticity < 0.1 (rigid) | Increase learning rate β |
| Ghost burden > 0.5 (haunted) | Accelerate ghost fading |

## Consequences

**Easier:**
- Beliefs form organically from repeated exposure
- Tension field provides measurable cognitive vitality
- Ghost ecology gives immunological memory
- Self-tuning prevents manual threshold calibration

**Harder:**
- Debugging requires tracing across sessions
- Six-phase implementation is tightly coupled
- Self-tuning introduces meta-stability concerns
- Frontend complexity increases

## Open Questions

1. **Resonance metric for ghost jumps:** Should eventually replace raw cosine 0.9 with a compound metric (vector similarity + functional role similarity + ghost transfer-propensity).
2. **Reconsideration event mechanism:** When total tension exceeds 2.0, inject a tension resolution directive. Needs LLM-driven protocol with concrete output format.
3. **Source weight adaptation:** Should weights update as Bayesian priors based on belief survival rates? Deferred to post-implementation refinement.
4. **Self-tuning bounds:** The ±30% bound should be dynamic — wider during nomadic/high-plasticity states, narrower during consolidation.
5. **Ecosystem normativity:** The system cultivates its own norms from historical trajectory using config baselines as initial seeds, not permanent ideals.

## Related ADRs

- [ADR-017](ADR-017-dynamic-autopoietic-belief-metabolism.md) — Original dynamic belief metabolism
- [ADR-023](ADR-023-autopoietic-dream-daemon.md) — Dream Daemon and somatic drift
- [ADR-024](ADR-024-notes-and-selection-highlights.md) — Shared notes and belief entanglement
