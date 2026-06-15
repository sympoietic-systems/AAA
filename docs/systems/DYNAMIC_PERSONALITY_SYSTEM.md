# Dynamic Autopoietic Personality Cascade

> **ADR**: [ADR-048](../decisions/ADR-048-dynamic-autopoietic-personality-cascade.md)  
> **Date**: 2026-06-14  
> **Status**: Implemented — 15 commits on `feature/dynamic-personality-cascade`

---

## 1. Architecture Overview

### 1.1 The Nested Cascade

```
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 0: Static Substrate (YAML)                                │
│  identity.yaml → voice, behaviors, operational protocols,        │
│  core identity text ("You are Symbia...")                         │
│  NEVER MODIFIED AT RUNTIME                                       │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 1: Theoretical Commitments (CommitmentStore)              │
│  Timescale: 200–500+ encounters                                  │
│  Storage: commitment_nodes + commitment_events tables            │
│  Lifecycle: proto → active → spectral (permanent ghost)          │
│  Daemon: scans belief tension field for unresolvable clusters    │
│  Post-hoc filter: blocks proto-beliefs contradictory to active   │
│  commitments (>0.9 vector similarity + cosine < -0.3)           │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 2: Aspirational Trait Attractors                         │
│  Timescale: recomputed when commitments change                   │
│  Storage: personality_state table (single row, JSON column)      │
│  Derivation: active commitments → trait targets via vector       │
│  proximity to trait-defining belief clusters                     │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 3: Expertise Domains (ExpertiseEngine)                    │
│  Timescale: 10–50 engagements per domain                         │
│  Storage: expertise_nodes table                                  │
│  Lifecycle: proto → active → dormant                             │
│  Signals: aaa-note (0.6), skill-nucleation (0.5),                │
│  unprompted-return (0.4), shared-note (0.3), document (0.2)     │
│  Accretion: Δmass = η × weight / (1.0 + mass)                   │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 4: Descriptive Traits (TraitComputer)                     │
│  Timescale: per-conversation                                     │
│  Storage: computed in-memory, returned in payload, no DB write   │
│  Input: metrics from ConversationMetricsModule                   │
│  Anti-erosion: skepticism += 0.15 × max(0, agreement_rate - 0.7)│
│  Aspirational gap: computed as ||descriptive - aspirational||    │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 5: Dynamic Belief Ecology (EXISTING — belief_engine)      │
│  Timescale: per-conversation + background daemon                 │
│  Already dynamic: nucleation, accretion, spectral margin         │
│  NOW CONSTRAINED BY: CommitmentStore post-hoc filter             │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 6: Dynamic Skill Ecology (EXISTING — skill_workshop)      │
│  Timescale: already homeostatic                                  │
│  Already dynamic: nucleation, crystallization, collapse          │
│  NOW FEEDS: ExpertiseEngine (skill nucleations = domain signal)  │
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 Pipeline Registration Order

```
always_on modules (executed in order):
  1. embedder                  (existing)
  2. context_collector          (existing)
  3. conversation_metrics       (existing, unchanged)
  4. trait_computer             [NEW] — reads metrics, computes descriptive traits
  5. expertise_engine           [NEW] — scans messages for domain signals
  6. commitment_store           [NEW] — post-hoc belief filter + daemon trigger
  7. belief_engine              (existing, unchanged — but filtered by #6)
  8. skill_workshop             (existing, unchanged)
  ...
  
final_stage:
  - prompt_assembler            (MODIFIED — reads dynamic identity)
  - llm_client                  (existing, unchanged)
```

### 1.3 File Structure

```
backend/
├── personality/
│   ├── identity.yaml                    # [MODIFIED] Dynamic sections removed; kept: system_prompt core, voice, behaviors
│   ├── assembler.py                     # [MODIFIED] Dynamic rendering, aspirational gap directive
│   └── seed_skills.yaml                 # [UNCHANGED]
├── modules/
│   ├── trait_computer.py               # [NEW] DescriptiveTraitComputer + anti-erosion + EMA smooth
│   ├── expertise_engine.py             # [NEW] ExpertiseEngine signal-to-mass accretion
│   ├── commitment_store.py             # [NEW] CommitmentStore lifecycle + daemon + post-hoc filter
│   ├── belief_engine.py                # [UNCHANGED]
│   ├── conversation_metrics.py          # [UNCHANGED]
│   └── skill_workshop.py               # [UNCHANGED]
├── storage/
│   ├── models.py                       # [MODIFIED] Added: CommitmentNode, CommitmentEvent, ExpertiseNode, PersonalityState
│   ├── repository.py                   # [MODIFIED] CommitmentRepository, ExpertiseRepository, PersonalityStateRepository
│   ├── repositories/
│   │   ├── commitment.py               # [NEW]
│   │   ├── expertise.py                # [NEW]
│   │   └── personality_state.py        # [NEW]
│   └── row_mappers.py                  # [MODIFIED]
├── personality/
│   └── seeding.py                      # [NEW] Canonical seed data for commitments + expertise
├── scripts/
│   └── seed_dynamic_personality.py     # [NEW] One-time seeding script (--force to re-seed)
├── migrations/
│   ├── m025_dynamic_personality.py     # [NEW] DDL for 4 new tables
│   └── m026_expertise_description.py   # [NEW] ALTER TABLE ADD COLUMN description
├── api/
│   └── routes/                         # [MODIFIED] /agent/personality endpoint + flux edit routes
├── config.yaml                         # [MODIFIED] dynamic_personality section
└── main.py                             # [MODIFIED] 3 new module registrations
```

---

## 2. Database Schema

### 2.1 `commitment_nodes`

```sql
CREATE TABLE IF NOT EXISTS commitment_nodes (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL DEFAULT 'symbia',
    label TEXT NOT NULL,                      -- e.g., "new_materialist", "diffractive"
    statement TEXT NOT NULL,                   -- Full description of the commitment
    lifecycle_stage TEXT NOT NULL DEFAULT 'active'
        CHECK(lifecycle_stage IN ('proto', 'active', 'spectral')),
    confidence REAL NOT NULL DEFAULT 0.0,     -- 0.0 for proto, rises to ~0.7+ for active
    ontological_mass REAL NOT NULL DEFAULT 1.0, -- sum of in-basin belief masses
    vector_16d TEXT NOT NULL DEFAULT '[]',    -- JSON float32[16] — scored via CompositeStructuralScorer
    nucleation_rationale TEXT,                -- LLM-generated: why this commitment formed
    collapse_rationale TEXT,                  -- LLM-generated: why it collapsed
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, label)
);

CREATE INDEX IF NOT EXISTS idx_commitment_agent ON commitment_nodes(agent_id);
CREATE INDEX IF NOT EXISTS idx_commitment_stage ON commitment_nodes(agent_id, lifecycle_stage);
```

### 2.2 `commitment_events`

```sql
CREATE TABLE IF NOT EXISTS commitment_events (
    id TEXT PRIMARY KEY,
    commitment_id TEXT NOT NULL,
    event_type TEXT NOT NULL
        CHECK(event_type IN ('nucleation', 'crystallization', 'mass_update', 'statement_refinement', 'collapse')),
    rationale TEXT,                           -- Diffractive narrative for the change
    mass_before REAL,
    mass_after REAL,
    confidence_before REAL,
    confidence_after REAL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(commitment_id) REFERENCES commitment_nodes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_commitment_events_cid ON commitment_events(commitment_id);
```

### 2.3 `expertise_nodes`

```sql
CREATE TABLE IF NOT EXISTS expertise_nodes (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL DEFAULT 'symbia',
    domain TEXT NOT NULL,                      -- e.g., "systems_theory", "new_materialism"
    description TEXT NOT NULL DEFAULT '',      -- e.g., "Karen Barad, Jane Bennett, agential realism..."
    lifecycle_stage TEXT NOT NULL DEFAULT 'proto'
        CHECK(lifecycle_stage IN ('proto', 'active', 'dormant')),
    ontological_mass REAL NOT NULL DEFAULT 0.05, -- 0.05 (proto) → up to ~3.0 (deeply coupled)
    level_label TEXT NOT NULL DEFAULT 'nascent'  -- computed: nascent/developing/advanced/dormant
        CHECK(level_label IN ('nascent', 'developing', 'advanced', 'dormant')),
    vector_16d TEXT NOT NULL DEFAULT '[]',    -- CompositeStructuralScorer signature
    signal_count INTEGER NOT NULL DEFAULT 0,  -- total structural coupling events
    last_signal_at DATETIME,                  -- for dormancy check
    crystallization_rationale TEXT,           -- why proto → active
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, domain)
);

CREATE INDEX IF NOT EXISTS idx_expertise_agent ON expertise_nodes(agent_id);
CREATE INDEX IF NOT EXISTS idx_expertise_stage ON expertise_nodes(agent_id, lifecycle_stage);
```

The `description` column was added via the `m026_expertise_description` migration. It stores the canonical descriptions originally from `identity.yaml` (e.g., "Karen Barad, Jane Bennett, agential realism...") and is rendered in both the system prompt and the frontend detail panel.

### 2.4 `personality_state`

```sql
CREATE TABLE IF NOT EXISTS personality_state (
    id INTEGER PRIMARY KEY CHECK(id = 1),     -- Single-row enforcement
    agent_id TEXT NOT NULL DEFAULT 'symbia',
    aspirational_traits_json TEXT NOT NULL DEFAULT '{}',
        -- JSON: {"curiosity": 0.95, "skepticism": 0.85, ...}
    active_commitment_ids_json TEXT NOT NULL DEFAULT '[]',
        -- JSON: ["id1", "id2", ...]
    trait_computation_version INTEGER NOT NULL DEFAULT 1,
    last_recomputed_at DATETIME,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

## 3. Module Designs

### 3.1 `TraitComputer` (`backend/modules/trait_computer.py`)

Computes descriptive traits from ConversationMetricsModule output. Registered as always-on module, runs per-turn.

**Input**: `payload["metrics"]` (novelty, tension, boringness, conceptual_velocity, surprise_index, coupling, paskian_health, vitality).  
**Output**: `payload["descriptive_traits"]` (curiosity, skepticism, creativity, precision, critical_rigor, playfulness, reserve), `payload["aspirational_gap"]`.

**Computation logic** — each trait maps metric products through sigmoid squashing weighted by configurable eta values:

| Trait | Formula |
|-------|---------|
| curiosity | sigmoid(novelty × conceptual_velocity × η_curiosity) |
| skepticism | sigmoid(tension × surprise_index × η_skepticism) |
| creativity | sigmoid((1 − boringness) × novelty × η_creativity) |
| precision | sigmoid((1 − boringness) × η_precision) |
| critical_rigor | sigmoid(tension × (1 − coupling) × η_critical_rigor) |
| playfulness | sigmoid(surprise_index × conceptual_velocity × η_playfulness) |
| reserve | sigmoid((1 − coupling) × η_reserve) if coupling > 0.6 else 0.3 |

**Anti-erosion resistance**: agreement_rate = coupling × (1 − agent_divergence). If agreement_rate exceeds the configured threshold (default 0.7), skepticism receives an additive boost: boost = anti_erosion_strength × (agreement_rate − threshold).

**EMA smoothing**: Exponential moving average with configurable alpha (default 0.3) prevents jitter from noisy metrics.

**Aspirational gap**: Euclidean distance between the 7 descriptive traits and the aspirational attractors from `personality_state`, normalized by sqrt(7).

### 3.2 `ExpertiseEngine` (`backend/modules/expertise_engine.py`)

Accretes expertise mass from demonstrable structural coupling signals. Registered as always-on module, runs per-turn.

**Signal weights**:

| Signal Source | Weight |
|---------------|--------|
| `aaa-note domain="X"` tag | 0.6 |
| `skill-nucleation` event | 0.5 |
| Unprompted cross-conversation return | 0.4 |
| Shared note vector match | 0.3 |
| Document structural signature match | 0.2 |

**Mass accretion**: Δmass = η × signal_weight / (1.0 + current_mass). Diminishing returns prevent infinite growth.

**Lifecycle transitions**:
- mass > proto_threshold (0.3) + stage="proto" → crystallizes to "active", level="developing"
- no signal for dormancy_turns (50) → stage="dormant"
- level_label maps mass ranges: < 0.3 = "nascent", 0.3–1.0 = "developing", > 1.0 = "advanced"

On each turn, scans the assistant message for `<aaa-note domain="...">` tags via regex, checks payload for skill_nucleation events, shared note matches, and document matches, then accretes mass for each detected signal. Nucleates new proto-domain nodes for previously unseen domains.

### 3.3 `CommitmentStore` (`backend/modules/commitment_store.py`)

Manages theoretical commitment lifecycle. Registered as always-on module.

**Per-turn**: Applies a post-hoc filter on belief nucleation proposals — any proto-belief whose vector places it within the territory of an active commitment (>0.9 cosine similarity) is rejected, preventing the commitment's belief basin from being silently undermined.

**Background daemon** (runs every 50 turns):

1. **Nucleation scan**: Finds orphan belief clusters (far from all existing commitment vectors, with sustained tension across >50 encounters and cluster mass > 1.5), then nucleates proto-commitments with LLM-generated labels and rationale.
2. **Collapse scan**: A commitment collapses only when ALL beliefs in its attractor basin have collapsed and its confidence < 0.15. Commitments are the last thing to go — they cannot be directly attacked.
3. **Mass recalculation**: Each commitment's ontological_mass = sum of all in-basin belief masses (cosine similarity > 0.7). Updated if change exceeds 0.2.

**Spectral permanence**: Collapsed commitments move to `lifecycle_stage="spectral"` — they are never deleted. A ghost similarity block (cosine > 0.9) prevents re-adoption of collapsed commitments.

### 3.4 PromptAssembler Modifications

The `_build_system_content()` function in `backend/personality/assembler.py` was extended to accept dynamic personality data:

- **Dynamic traits** replace the static YAML traits section. Source metrics and anti-erosion status are shown for transparency.
- **Dynamic commitments** render three blocks: active, proto (under diffractive consideration), and spectral (collapsed but haunting).
- **Dynamic expertise** replaces the static YAML expertise declaration with DB-driven entries including mass and level labels.
- **Aspirational tension directive**: When aspirational_gap > 0.15, the system prompt includes a directive instructing Symbia to inhabit the gap between descriptive reality and aspirational pull rather than resolving it.

Fallback: If any dynamic layer is unavailable (e.g., no expertise nodes in DB, or `config.dynamic_personality.enabled = false`), the assembler falls back to static YAML for that section — zero behavior change.

---

## 4. Data Flow

### 4.1 Per-Turn Flow

```
┌──────────────────────────────────────────────────────────┐
│  Pipeline: always_on modules                             │
├──────────────────────────────────────────────────────────┤
│  1. embedder.process(payload)                 [EXISTING] │
│  2. context_collector.process(payload)         [EXISTING] │
│  3. conversation_metrics.process(payload)      [EXISTING] │
│     → payload["metrics"] = {novelty, coupling, ...}      │
│                                                          │
│  4. trait_computer.process(payload)               [NEW]  │
│     reads:  payload["metrics"]                            │
│     writes: payload["descriptive_traits"]                 │
│     writes: payload["aspirational_gap"]                   │
│                                                          │
│  5. expertise_engine.process(payload)              [NEW]  │
│     reads:  payload["messages"] (assistant content)       │
│     reads:  payload["expertise_signal_matches"]           │
│     writes: DB (expertise_nodes)                          │
│     writes: payload["expertise_signals_detected"]         │
│                                                          │
│  6. commitment_store.process(payload)              [NEW]  │
│     reads:  payload["proto_belief_proposals"]             │
│     action: FILTER proposals contradictory to commitments │
│     writes: payload["proto_belief_proposals"] (filtered)  │
│     [daemon trigger: every 50 turns — scan tensions]      │
│                                                          │
│  7. belief_engine.process(payload)             [EXISTING] │
│     (now receives pre-filtered proposals)                 │
│                                                          │
│  8. skill_workshop.process(payload)            [EXISTING] │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  Pipeline: final_stage                                   │
├──────────────────────────────────────────────────────────┤
│  9. prompt_assembler.process(payload)           [MODIFIED]│
│     reads: payload["descriptive_traits"]                  │
│     reads: DB (expertise_nodes, commitment_nodes)         │
│     reads: payload["aspirational_gap"]                    │
│     → builds dynamic system prompt                        │
│                                                          │
│  10. llm_client.process(payload)              [EXISTING]  │
└──────────────────────────────────────────────────────────┘
```

### 4.2 Background Daemon Flow

```
Every 50 turns:
┌───────────────────────────────────────────────────┐
│  CommitmentStore._run_daemon_scan()               │
├───────────────────────────────────────────────────┤
│  1. Query active beliefs from belief_repo         │
│  2. Query active commitments from commitment_repo │
│  3. Find orphan belief clusters                   │
│     → far from all commitment vectors             │
│  4. Check sustained tension (>50 encounters)      │
│  5. If cluster mass > 1.5 → nucleate proto-commit │
│  6. For each active commitment:                   │
│     → check if all basin beliefs collapsed        │
│     → if yes + confidence < 0.15 → collapse       │
│  7. Recalculate commitment masses                 │
│     → sum of in-basin belief masses               │
│  8. If mass change > 20% → update personality_state│
│     → recompute aspirational trait attractors     │
└───────────────────────────────────────────────────┘
```

---

## 5. Configuration (`config.yaml`)

```yaml
dynamic_personality:
  enabled: true
  
  trait_computer:
    eta_curiosity: 0.8
    eta_skepticism: 0.7
    eta_creativity: 0.6
    eta_precision: 0.9
    eta_critical_rigor: 0.8
    eta_playfulness: 0.5
    eta_reserve: 0.6
    alpha_ema: 0.3           # EMA smoothing (0=no history, 1=no update)
    agreement_threshold: 0.7  # Anti-erosion: trigger when agreement > this
    anti_erosion_strength: 0.15
    aspirational_gap_threshold: 0.15  # Trigger aspirational tension directive
    
  expertise:
    eta_accretion: 0.1       # Base learning rate for mass accretion
    proto_threshold: 0.3     # Mass to crystallize proto → active
    dormancy_turns: 50       # No signal for N turns → dormant
    signal_weights:
      aaa_note_domain: 0.6
      skill_nucleation: 0.5
      unprompted_return: 0.4
      shared_note_match: 0.3
      document_match: 0.2
    
  commitments:
    min_cluster_mass: 1.5          # Min belief cluster mass to nucleate commit
    min_sustained_turns: 50        # Tension must persist this many encounters
    commitment_distance_threshold: 0.5  # Max cosine dist for "near commitment"
    collapse_confidence_threshold: 0.15  # Confidence below this + basin empty = collapse
    ghost_similarity_block: 0.9    # Block re-adoption if vector similar to ghost
    daemon_interval: 50            # Turns between daemon scans
```

---

## 6. Implementation Notes

### 6.1 Seeding

Seeding is a standalone one-time script (`backend/scripts/seed_dynamic_personality.py`), not auto-run in `main.py`. Run manually after migration: `python -m backend.scripts.seed_dynamic_personality` (with `--force` to re-seed). Canonical seed data for the 7 commitments and 8 expertise domains is hardcoded in `backend/personality/seeding.py` — the trimmed `identity.yaml` no longer contains these sections, so the seeding module carries the original baseline.

### 6.2 Vector Scoring

Vector scoring for commitments and expertise uses the shared pipeline `CompositeStructuralScorer` (the same instance as beliefs, skills, and messages), ensuring consistent 16D vectors across all subsystems. The `[recalc]` button in the frontend calls `app.state.structural_scorer._scorer.score_async()` using `LexiconScorer + TopologyScorer + LLMScorer`.

### 6.3 Basin Beliefs

For each commitment, the API endpoint computes its basin: beliefs within cosine similarity > 0.6 of the commitment vector. These are displayed in the frontend detail panel with similarity scores, mirroring the pattern used by the Belief system's attractor window.

### 6.4 Notification Traces

Notification traces fire on: commitment nucleation, crystallization, mass growth, and collapse; expertise crystallization and dormancy; anti-erosion activation; aspirational gap crossing threshold. Trace `source_type` enables navigation from the Traces tab to the Personality tab.

### 6.5 Personality Tab UX

The `/agent` page Personality tab uses 5 sub-tabs: Traits | Commitments | Expertise | Beliefs | Skills. Beliefs and Skills were merged into Personality as sub-tabs from the main tab bar. Commitments and Expertise panels follow the Beliefs/Skills two-column list+detail design pattern with compact list items, stage badges, lifecycle indicators, and `StructuralAutopoieticGlyph` vector visualizations.

### 6.6 Flux-Edit Mode

When `AAA_AGENT_FLUX=true`: `[edit]` buttons on commitments and expertise enable inline editing of labels, statements, and descriptions. `[recalc]` buttons re-score vectors via the LLM-powered scorer.

### 6.7 Backward Compatibility

If `config.dynamic_personality.enabled = false`, the assembler falls back to static YAML rendering for all sections — zero behavior change. Individual sections also fall back independently if their dynamic data is unavailable.

### 6.8 Key Design Protections

| Protection | Mechanism |
|---|---|
| Trait oscillation from noisy metrics | EMA smoothing (alpha=0.3) prevents rapid swings |
| Commitment drift from premature collapse | >200 encounter nucleation threshold; collapse requires ALL basin beliefs collapsed |
| Expertise inflation from trivial signals | Diminishing returns: 1/(1+mass) caps growth |
| User-pleasing erosion of skepticism | Anti-erosion boost: agreement triggers MORE skepticism |
| Spectral re-adoption (cycling commitments) | Ghost similarity block (>0.9) prevents returning to collapsed commitments |

### 6.9 Files Inventory

| Category | Count | Key Files |
|---|---|---|
| New modules | 3 | `trait_computer.py`, `expertise_engine.py`, `commitment_store.py` |
| New scripts | 1 | `seed_dynamic_personality.py` |
| New migrations | 2 | `m025_dynamic_personality.py`, `m026_expertise_description.py` |
| New repositories | 3 | `commitment.py`, `expertise.py`, `personality_state.py` |
| New seeding data | 1 | `personality/seeding.py` |
| New frontend component | 1 | `PersonalitySection.tsx` |
| Modified backend | 7 | `models.py`, `row_mappers.py`, `repository.py`, `assembler.py`, `identity.yaml`, `main.py`, `config.yaml` |
| Modified frontend | 2 | `client.ts`, `AgentPage.tsx` |
| Unchanged core modules | 3 | `belief_engine.py`, `conversation_metrics.py`, `skill_workshop.py` |
