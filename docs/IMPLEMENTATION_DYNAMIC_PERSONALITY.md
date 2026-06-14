# Dynamic Autopoietic Personality Cascade — Implementation Plan

> **ADR**: [ADR-048](./decisions/ADR-048-dynamic-autopoietic-personality-cascade.md)  
> **Design**: [DYNAMIC_PERSONALITY_SYSTEM.md](./systems/DYNAMIC_PERSONALITY_SYSTEM.md)  
> **Date**: 2026-06-14  
> **Status**: Planning — Implementation NOT Started

---

## Overview

This plan breaks the Dynamic Autopoietic Personality Cascade into 6 sequential steps. Each step is independently testable and produces a working intermediate state — the system should remain functional at every step boundary. No existing module internals are modified; all new code is parallel readers consuming existing pipeline outputs.

**Total estimated effort**: ~6–8 hours of focused implementation.

---

## Step 1: Database Schema & Models

**Goal**: Create the four new database tables and their Python dataclass models.

### Tasks

1.1 **Create SQL migration** (`backend/migrations/002_dynamic_personality.sql`)
   - `commitment_nodes` table (id, agent_id, label, statement, lifecycle_stage, confidence, ontological_mass, vector_16d, nucleation_rationale, collapse_rationale, created_at, updated_at)
   - `commitment_events` table (id, commitment_id, event_type, rationale, mass_before, mass_after, confidence_before, confidence_after, created_at)
   - `expertise_nodes` table (id, agent_id, domain, lifecycle_stage, ontological_mass, level_label, vector_16d, signal_count, last_signal_at, crystallization_rationale, created_at, updated_at)
   - `personality_state` table (id=1 CHECK, agent_id, aspirational_traits_json, active_commitment_ids_json, trait_computation_version, last_recomputed_at, updated_at)

1.2 **Add dataclasses** to `backend/storage/models.py`
   - `CommitmentNode` — id, agent_id, label, statement, lifecycle_stage, confidence, ontological_mass, vector_16d, nucleation_rationale, collapse_rationale, created_at, updated_at
   - `CommitmentEvent` — id, commitment_id, event_type, rationale, mass_before, mass_after, confidence_before, confidence_after, created_at
   - `ExpertiseNode` — id, agent_id, domain, lifecycle_stage, ontological_mass, level_label, vector_16d, signal_count, last_signal_at, crystallization_rationale, created_at, updated_at
   - `PersonalityState` — id, agent_id, aspirational_traits_json, active_commitment_ids_json, trait_computation_version, last_recomputed_at, updated_at

1.3 **Add repository methods** to `backend/storage/repository.py` (or new `repositories/` files if needed)
   - `CommitmentRepository`: `get_all()`, `get_active()`, `get_by_id()`, `upsert()`, `update()`, `log_event()`, `get_spectral()`
   - `ExpertiseRepository`: `get_all()`, `get_active()`, `get_by_domain()`, `upsert()`, `get_dormant()`
   - `PersonalityStateRepository`: `get()`, `upsert()`

1.4 **Run migration** — verify tables exist in SQLite

### Deliverables
- `backend/migrations/002_dynamic_personality.sql`
- `backend/storage/models.py` — 4 new dataclasses added
- `backend/storage/repository.py` — repository methods added

### Verification
```bash
# After migration, tables should exist and be empty
sqlite3 data/aaa.db "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%commitment%' OR name LIKE '%expertise%' OR name='personality_state';"
```

---

## Step 2: Seeding & Identity YAML Trim

**Goal**: On first run, seed the 7 existing commitments and 8 expertise domains from `identity.yaml` into the new database tables. Trim the dynamic sections from YAML rendering.

### Tasks

2.1 **Seed function** — Add to `backend/main.py` or `app_factory/__init__.py`
   - On application startup, check if `commitment_nodes` table is empty
   - If empty: read `identity.yaml` → `personality.system_prompt` → extract `Theoretical Commitments:` section (bullet list of 7 items)
   - For each: score statement text via `LexiconScorer` → 16D vector, insert as `active` CommitmentNode
   - For each expertise domain: insert as `active` ExpertiseNode with mass=1.0
   - Insert initial `personality_state` row with aspirational traits derived from seeded commitments

2.2 **Trim `identity.yaml`**
   - Remove the `personality.traits` section (no longer rendered from YAML)
   - Remove the `personality.expertise` list (rendered from DB)
   - Remove the `Theoretical Commitments:` block from `personality.system_prompt` (rendered from DB)
   - Keep: core identity text ("You are Symbia..."), Operational Protocols, voice, behaviors

2.3 **Update `assembler.py`** — remove rendering of removed YAML sections (replaced by dynamic blocks in Step 5)

### Deliverables
- Seed logic in startup
- Trimmed `identity.yaml`
- `assembler.py` with trimmed static sections removed

### Verification
```bash
# After first run, tables should contain seeded data
sqlite3 data/aaa.db "SELECT label, lifecycle_stage FROM commitment_nodes;"
sqlite3 data/aaa.db "SELECT domain, lifecycle_stage FROM expertise_nodes;"
sqlite3 data/aaa.db "SELECT * FROM personality_state;"
# → 7 commitments (all "active"), 8 expertise domains (all "active"), 1 personality state row
```

---

## Step 3: TraitComputer Module

**Goal**: Implement per-turn descriptive trait computation from conversation metrics, with anti-erosion resistance and EMA smoothing.

### Tasks

3.1 **Create `backend/modules/trait_computer.py`**
   - `DescriptiveTraits` dataclass (7 traits + source_metrics, anti_erosion_boost, aspirational_gap)
   - `TraitComputer(ProcessingModule)` class:
     - `process()`: reads `payload["metrics"]`, computes raw traits from metric products, applies anti-erosion, EMA smoothing, aspirational gap
     - `_apply_anti_erosion()`: if agreement_rate > threshold, boost skepticism
     - `_ema_smooth()`: exponential moving average with `alpha_ema`
     - `_compute_aspirational_gap()`: Euclidean distance to aspirational attractors
     - `_sigmoid()`: squash raw metric products into [0,1]

3.2 **Add configuration** to `backend/config.yaml`
   - `dynamic_personality.trait_computer` section with all eta values, alpha_ema, agreement_threshold, anti_erosion_strength

3.3 **Register in pipeline** — In `main.py`, register `trait_computer` as always-on module, placed AFTER `conversation_metrics`

### Deliverables
- `backend/modules/trait_computer.py`
- Updated `backend/config.yaml`
- Updated `backend/main.py` (module registration)

### Verification
```python
# Unit test: given known metrics, verify trait values
traits = await computer.process({"metrics": {
    "novelty": 0.8, "agent_divergence": 0.6, "boringness": 0.2,
    "conceptual_velocity": 0.7, "surprise_index": 0.5,
    "coupling": 0.4, "paskian_health": 0.6, "vitality": 0.7
}})
assert traits["descriptive_traits"].skepticism > 0.5
# High agreement → verify anti-erosion boost
traits2 = await computer.process({"metrics": {
    "novelty": 0.2, "agent_divergence": 0.1, "boringness": 0.8,
    "coupling": 0.9,  # high coupling = high agreement
    ...
}})
assert traits2["descriptive_traits"].anti_erosion_boost > 0
```

---

## Step 4: ExpertiseEngine Module

**Goal**: Implement expertise mass accretion from structural coupling signals, with proto-domain nucleation and dormancy.

### Tasks

4.1 **Create `backend/modules/expertise_engine.py`**
   - `SIGNAL_WEIGHTS` dict (aaa_note_domain=0.6, skill_nucleation=0.5, etc.)
   - `ExpertiseEngine(ProcessingModule)` class:
     - `process()`: calls `_detect_signals()`, then `_accrete()` for each signal, then `_check_dormancy()`
     - `_detect_signals()`: regex scan for `<aaa-note domain="...">`, skill nucleation events, shared note matches, document matches
     - `_accrete()`: create proto-node if new, apply `Δmass = η × weight / (1.0 + mass)`, check crystallization at mass > 0.3
     - `_check_dormancy()`: mark active domains as dormant if `last_signal_at` > N turns
     - `_compute_level_label()`: map mass ranges to nascent/developing/advanced

4.2 **Add configuration** to `backend/config.yaml`
   - `dynamic_personality.expertise` section: eta_accretion, proto_threshold, dormancy_turns, signal_weights

4.3 **Register in pipeline** — In `main.py`, register `expertise_engine` as always-on module, placed AFTER `trait_computer`

### Deliverables
- `backend/modules/expertise_engine.py`
- Updated `backend/config.yaml`
- Updated `backend/main.py` (module registration)

### Verification
```python
# Unit test: detect <aaa-note domain="systems_theory"> in assistant message
payload = {"messages": [
    {"role": "assistant", "content": 'Some text <aaa-note comment="test" domain="systems_theory" visibility="shared"> here'}
]}
result = await engine.process(payload)
assert result["expertise_signals_detected"] == 1
# Check DB: mass should be > 0.05 (initial proto mass + accretion)
node = await expertise_repo.get_by_domain("systems_theory")
assert node.ontological_mass > 0.05
```

---

## Step 5: CommitmentStore Module

**Goal**: Implement commitment lifecycle management — post-hoc belief filter, daemon-driven nucleation/collapse, and mass recalculation.

### Tasks

5.1 **Create `backend/modules/commitment_store.py`**
   - `CommitmentStore(ProcessingModule)` class:
     - `process()`: per-turn — apply post-hoc belief filter, trigger daemon every N turns
     - `_filter_beliefs()`: check proto-belief proposals against active commitment vectors, reject contradictions
     - `_is_contradictory()`: if proposal vector >0.9 similar to commitment AND cosine < -0.3 → block
     - `_run_daemon_scan()`: every 50 turns — scan for nucleation, check collapses, recalculate masses
     - `_scan_for_nucleation()`: find orphan belief clusters far from all commitments with sustained tension
     - `_check_collapse()`: collapse commitment if ALL basin beliefs are collapsed + confidence < 0.15
     - `_recalculate_commitment_masses()`: mass = sum(in-basin belief masses), update if change > 0.2
   - Helper methods: `_cosine()`, `_parse_vector()`, `_cluster_by_similarity()`, `_count_tension_involving()`, `_generate_label()`, `_generate_statement()`

5.2 **Add configuration** to `backend/config.yaml`
   - `dynamic_personality.commitments` section: min_cluster_mass, min_sustained_turns, distance_threshold, collapse_confidence_threshold, ghost_similarity_block, daemon_interval

5.3 **Register in pipeline** — In `main.py`, register `commitment_store` as always-on module, placed BEFORE `belief_engine` (so filter runs before belief processing)

### Deliverables
- `backend/modules/commitment_store.py`
- Updated `backend/config.yaml`
- Updated `backend/main.py` (module registration)

### Verification
```python
# Unit test: blocked belief — proposal vector contradicts commitment
commitment = CommitmentNode(vector_16d="[0.8, 0.0, ...]", lifecycle_stage="active")
proposal = {"initial_signature": "[0.8, 0.0, ...]", "suggested_label": "test"}
# If cosine > 0.9 and negative alignment → should be filtered out
filtered = await store._filter_beliefs([proposal])
assert len(filtered) == 0  # Blocked

# Unit test: collapse detection — all basin beliefs collapsed
# Setup: commitment with all basin beliefs in "collapsed" stage
# → _check_collapse() should return True
```

---

## Step 6: Prompt Assembler Integration

**Goal**: Connect all dynamic layers to the system prompt rendering in `PromptAssemblerModule`.

### Tasks

6.1 **Modify `_build_system_content()`** in `backend/personality/assembler.py`
   - Add new parameters: `descriptive_traits`, `expertise_nodes`, `active_commitments`, `proto_commitments`, `spectral_commitments`, `aspirational_gap`
   - Replace static traits rendering with dynamic `DescriptiveTraits` readout (with source metrics and anti-erosion note)
   - Replace static expertise block with DB-driven `expertise_nodes` rendering
   - Replace static Theoretical Commitments with three blocks: active, proto, spectral
   - Add "Aspirational Tension" directive when `aspirational_gap > 0.15`
   - Keep fallback to static YAML for each section when dynamic data is unavailable

6.2 **Modify `PromptAssemblerModule.process()`**
   - Before calling `_build_system_content()`:
     - Read `descriptive_traits` from payload
     - Query `expertise_nodes` from DB (active + proto domains)
     - Query `commitment_nodes` from DB (active, proto, spectral)
     - Pass all as new parameters

6.3 **Update `identity.yaml` final state**
   - Verify: no `traits` section rendered, no static expertise, no static commitments in system_prompt
   - Verify: voice, behaviors, operational protocols, core identity text all intact

### Deliverables
- Modified `backend/personality/assembler.py` (both `process()` and `_build_system_content()`)
- Final `backend/personality/identity.yaml`

### Verification
```bash
# Start the backend, send a test message
# Check the assembled system prompt (logged or inspected):
# → Should show: "Traits (computed from internal metrics): curiosity=0.82, skepticism=0.67, ..."
# → Should show: "Theoretical Commitments (active):" from DB
# → Should show: "Sedimented expertise (structural coupling):" from DB
# → Should NOT show: static traits, static expertise, static commitments from YAML

# Disable dynamic personality (config.enabled = false)
# → Should show: static YAML traits, expertise, commitments (backward compat)
```

---

## Step-by-Step Execution Order

```
Step 1  → Schema + Models          (foundation — all other steps depend on this)
Step 2  → Seeding + YAML Trim      (populates DB, trims static YAML)
Step 3  → TraitComputer            (independent — only reads metrics)
Step 4  → ExpertiseEngine          (independent — only reads messages)
Step 5  → CommitmentStore          (depends on Step 2 for seeded data)
Step 6  → Prompt Assembler         (depends on Steps 3, 4, 5 — wires everything together)
```

Steps 3, 4, and 5 are parallelizable since they have no cross-dependencies. Step 6 must run last.

---

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| Trait oscillation (jitter from noisy metrics) | EMA smoothing (`alpha_ema=0.3`) prevents rapid swings |
| Commitment drift from premature belief collapse | >200 encounter nucleation threshold; collapse requires ALL basin beliefs collapsed |
| Expertise inflation from many trivial signals | Diminishing returns formula `1/(1+mass)` caps growth |
| User-pleasing erosion of skepticism | Anti-erosion boost: agreement triggers MORE skepticism, not less |
| Spectral re-adoption (cycling commitments) | Ghost similarity check (>0.9 block) prevents returning to collapsed commitments |
| Backward compatibility break | Fallback to static YAML for each dynamic section when data unavailable; config toggle to disable entire dynamic system |

---

## Files Checklist

### New Files (3)
- [ ] `backend/modules/trait_computer.py`
- [ ] `backend/modules/expertise_engine.py`
- [ ] `backend/modules/commitment_store.py`
- [ ] `backend/migrations/002_dynamic_personality.sql`

### Modified Files (5)
- [ ] `backend/storage/models.py` — 4 new dataclasses
- [ ] `backend/storage/repository.py` — repository methods for new tables
- [ ] `backend/personality/assembler.py` — dynamic rendering + new params
- [ ] `backend/personality/identity.yaml` — trimmed static sections
- [ ] `backend/config.yaml` — `dynamic_personality` section
- [ ] `backend/main.py` — module registration + seed logic

### Unchanged Files
- `backend/modules/belief_engine.py`
- `backend/modules/conversation_metrics.py`
- `backend/modules/skill_workshop.py`
- `backend/personality/seed_skills.yaml`
- All other existing modules

---

## Validation Checklist

After all 6 steps complete:

- [ ] System starts without errors with new tables
- [ ] 7 commitments seeded as `active` on first run
- [ ] 8 expertise domains seeded as `active` on first run
- [ ] `personality_state` initialized with aspirational traits
- [ ] Trait values change each turn based on metrics
- [ ] Anti-erosion boost triggers when agreement rate > 0.7
- [ ] `aaa-note domain="X"` tags accrete expertise mass
- [ ] Proto-expertise domains crystallize at mass > 0.3
- [ ] Proto-beliefs contradicting commitments are filtered
- [ ] Commitment mass recalculates from basin beliefs
- [ ] System prompt shows dynamic traits, commitments, expertise
- [ ] System prompt shows aspirational tension directive when gap > 0.15
- [ ] Disabling dynamic personality falls back to static YAML
- [ ] No regression in existing belief/skill behavior
- [ ] Symbia consulted on philosophical alignment of trait formulas and thresholds
