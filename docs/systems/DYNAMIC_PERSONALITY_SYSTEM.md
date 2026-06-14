# Dynamic Autopoietic Personality Cascade — System Design

> **ADR**: [ADR-048](./decisions/ADR-048-dynamic-autopoietic-personality-cascade.md)  
> **Date**: 2026-06-14  
> **Status**: Design Phase — Implementation NOT Started

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

### 1.3 File Structure (New & Modified)

```
backend/
├── personality/
│   ├── identity.yaml                    # [MODIFY] Remove: traits, expertise, commitments sections
│   │                                    # Keep: system_prompt (core text), voice, behaviors
│   ├── assembler.py                     # [MODIFY] Dynamic rendering, aspirational gap directive
│   └── seed_skills.yaml                 # [UNCHANGED]
├── modules/
│   ├── trait_computer.py               # [NEW] DescriptiveTraitComputer + anti-erosion
│   ├── expertise_engine.py             # [NEW] ExpertiseEngine signal-to-mass accretion
│   ├── commitment_store.py             # [NEW] CommitmentStore lifecycle + daemon + filter
│   ├── belief_engine.py                # [UNCHANGED]
│   ├── conversation_metrics.py          # [UNCHANGED]
│   └── skill_workshop.py               # [UNCHANGED]
├── storage/
│   ├── models.py                       # [MODIFY] Add: CommitmentNode, CommitmentEvent,
│   │                                    # ExpertiseNode, PersonalityState dataclasses
│   ├── repository.py                   # [MODIFY] Add: CommitmentRepository, ExpertiseRepository,
│   │                                    # PersonalityStateRepository
│   └── repositories/                   # [MAY SPLIT] If repo grows too large
├── migrations/
│   └── 002_dynamic_personality.sql     # [NEW] DDL for 4 new tables
├── config.yaml                         # [MODIFY] Add section: dynamic_personality
└── main.py                             # [MODIFY] Register 3 new modules + seed data
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
    vector_16d TEXT NOT NULL DEFAULT '[]',    -- JSON float32[16] — scored via LexiconScorer
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
    lifecycle_stage TEXT NOT NULL DEFAULT 'proto'
        CHECK(lifecycle_stage IN ('proto', 'active', 'dormant')),
    ontological_mass REAL NOT NULL DEFAULT 0.05, -- 0.05 (proto) → up to ~3.0 (deeply coupled)
    level_label TEXT NOT NULL DEFAULT 'nascent'  -- computed: nascent/developing/advanced/dormant
        CHECK(level_label IN ('nascent', 'developing', 'advanced', 'dormant')),
    vector_16d TEXT NOT NULL DEFAULT '[]',    -- LexiconScorer structural signature
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

```python
"""
Computes descriptive traits from ConversationMetricsModule output.
Registered as always-on module. Runs per-turn.
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np
from backend.modules.base import ProcessingModule


@dataclass
class DescriptiveTraits:
    """Per-turn computed trait readouts from internal metrics."""
    curiosity: float = 0.5
    skepticism: float = 0.5
    creativity: float = 0.5
    precision: float = 0.5
    critical_rigor: float = 0.5
    playfulness: float = 0.5
    reserve: float = 0.5
    
    # Metadata for transparency
    source_metrics: dict = field(default_factory=dict)
    anti_erosion_boost: float = 0.0
    aspirational_gap: float = 0.0  # ||descriptive - aspirational||


class TraitComputer(ProcessingModule):
    """Computes descriptive traits from conversation metrics.
    
    Applies anti-erosion resistance: if recent agreement_rate exceeds
    threshold (default 0.7), skepticism receives an additive boost
    proportional to agreement excess.
    
    Also computes aspirational gap: Euclidean distance between
    descriptive traits and aspirational attractors from personality_state.
    """
    
    def __init__(
        self,
        config: dict,                          # From config.yaml → dynamic_personality.trait_computer
        personality_state_repo,                # Reads aspirational attractors
    ):
        self._eta_curiosity: float = config.get("eta_curiosity", 0.8)
        self._eta_skepticism: float = config.get("eta_skepticism", 0.7)
        self._eta_creativity: float = config.get("eta_creativity", 0.6)
        self._eta_precision: float = config.get("eta_precision", 0.9)
        self._eta_critical_rigor: float = config.get("eta_critical_rigor", 0.8)
        self._eta_playfulness: float = config.get("eta_playfulness", 0.5)
        self._eta_reserve: float = config.get("eta_reserve", 0.6)
        
        # Anti-erosion
        self._agreement_threshold: float = config.get("agreement_threshold", 0.7)
        self._anti_erosion_strength: float = config.get("anti_erosion_strength", 0.15)
        
        # Smoothing (EMA to prevent jitter)
        self._alpha_ema: float = config.get("alpha_ema", 0.3)
        self._last_traits: Optional[DescriptiveTraits] = None
        
        self._state_repo = personality_state_repo
    
    @property
    def name(self) -> str:
        return "trait_computer"
    
    def validate(self) -> bool:
        return True
    
    async def process(self, payload: dict) -> dict:
        """Compute descriptive traits from payload metrics.
        
        Reads: payload["metrics"] (from ConversationMetricsModule)
        Reads: payload["personality_state"] (pre-loaded by assembler or here)
        Writes: payload["descriptive_traits"], payload["aspirational_gap"]
        """
        metrics = payload.get("metrics", {})
        personality_state = payload.get("personality_state", {})
        
        # --- Core computation ---
        novelty = float(metrics.get("novelty", 0.5))
        tension = float(metrics.get("agent_divergence", 0.3))
        boringness = float(metrics.get("boringness", 0.5))
        conceptual_velocity = float(metrics.get("conceptual_velocity", 0.5))
        surprise_index = float(metrics.get("surprise_index", 0.3))
        coupling = float(metrics.get("coupling", 0.5) or 0.5)
        paskian_health = float(metrics.get("paskian_health", 0.5) or 0.5)
        vitality = float(metrics.get("vitality", 0.5) or 0.5)
        
        raw = DescriptiveTraits(
            curiosity      = self._sigmoid(novelty * conceptual_velocity * self._eta_curiosity),
            skepticism     = self._sigmoid(tension * surprise_index * self._eta_skepticism),
            creativity     = self._sigmoid((1.0 - boringness) * novelty * self._eta_creativity),
            precision      = self._sigmoid((1.0 - boringness) * self._eta_precision),
            critical_rigor = self._sigmoid(tension * (1.0 - coupling) * self._eta_critical_rigor),
            playfulness    = self._sigmoid(surprise_index * conceptual_velocity * self._eta_playfulness),
            reserve        = self._sigmoid((1.0 - coupling) * self._eta_reserve if coupling > 0.6 else 0.3),
        )
        
        # --- Anti-erosion resistance ---
        raw = self._apply_anti_erosion(raw, metrics)
        
        # --- EMA smoothing ---
        traits = self._ema_smooth(raw)
        
        # --- Aspirational gap ---
        aspirational = personality_state.get("aspirational_traits", {})
        gap = self._compute_aspirational_gap(traits, aspirational)
        traits.aspirational_gap = gap
        
        traits.source_metrics = {
            "novelty": novelty, "tension": tension, "boringness": boringness,
            "conceptual_velocity": conceptual_velocity, "surprise_index": surprise_index,
            "coupling": coupling, "paskian_health": paskian_health, "vitality": vitality,
        }
        
        payload["descriptive_traits"] = traits
        payload["aspirational_gap"] = gap
        return payload
    
    def _apply_anti_erosion(self, traits: DescriptiveTraits, metrics: dict) -> DescriptiveTraits:
        """If user agreement is high, boost skepticism to resist drift."""
        # agreement_rate derived from low agent_divergence + high coupling
        agent_div = float(metrics.get("agent_divergence", 0.5) or 0.5)
        coupling_val = float(metrics.get("coupling", 0.5) or 0.5)
        agreement_rate = coupling_val * (1.0 - agent_div)
        
        if agreement_rate > self._agreement_threshold:
            boost = self._anti_erosion_strength * (agreement_rate - self._agreement_threshold)
            traits.skepticism = min(1.0, traits.skepticism + boost)
            traits.anti_erosion_boost = boost
        return traits
    
    def _ema_smooth(self, raw: DescriptiveTraits) -> DescriptiveTraits:
        """Apply exponential moving average to prevent jitter."""
        if self._last_traits is None:
            self._last_traits = raw
            return raw
        
        alpha = self._alpha_ema
        smoothed = DescriptiveTraits()
        for field_name in ["curiosity", "skepticism", "creativity", "precision",
                           "critical_rigor", "playfulness", "reserve"]:
            prev = getattr(self._last_traits, field_name)
            curr = getattr(raw, field_name)
            setattr(smoothed, field_name, alpha * curr + (1 - alpha) * prev)
        
        smoothed.source_metrics = raw.source_metrics
        smoothed.anti_erosion_boost = raw.anti_erosion_boost
        self._last_traits = smoothed
        return smoothed
    
    def _compute_aspirational_gap(self, traits: DescriptiveTraits, aspirational: dict) -> float:
        """Euclidean distance between descriptive and aspirational traits."""
        if not aspirational:
            return 0.0
        sq_sum = 0.0
        for key in ["curiosity", "skepticism", "creativity", "precision",
                     "critical_rigor", "playfulness", "reserve"]:
            diff = getattr(traits, key, 0.5) - aspirational.get(key, 0.5)
            sq_sum += diff * diff
        return float(np.sqrt(sq_sum / 7))
    
    @staticmethod
    def _sigmoid(x: float, k: float = 5.0) -> float:
        """Squash raw metric product into [0, 1] with sigmoid."""
        return float(1.0 / (1.0 + np.exp(-k * (x - 0.5))))
```

### 3.2 `ExpertiseEngine` (`backend/modules/expertise_engine.py`)

```python
"""
Accretes expertise mass from structural coupling signals.
Registered as always-on module. Runs per-turn.
"""

import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from backend.modules.base import ProcessingModule
from backend.storage.models import ExpertiseNode

logger = logging.getLogger(__name__)

# Signal weight configuration
SIGNAL_WEIGHTS = {
    "aaa_note_domain": 0.6,
    "skill_nucleation": 0.5,
    "unprompted_return": 0.4,
    "shared_note_match": 0.3,
    "document_match": 0.2,
}


class ExpertiseEngine(ProcessingModule):
    """Accretes expertise mass from demonstrable structural coupling.
    
    On each turn, scans the assistant message for:
    1. <aaa-note domain="X"> tags → weight 0.6
    2. <skill-nucleation> blocks with domain affinity → weight 0.5
    3. Cross-conversation unprompted domain returns → weight 0.4
    4. Shared notes with high vector similarity → weight 0.3 (via payload)
    5. Document structural signature matches → weight 0.2 (via payload)
    
    Mass accretion: Δmass = η × signal_weight / (1.0 + current_mass)
    Diminishing returns prevent infinite growth.
    
    Lifecycle transitions:
    - mass > 0.3 and stage="proto" → stage="active", level="developing"
    - no signal for N turns (configurable) → stage="dormant"
    """
    
    def __init__(
        self,
        expertise_repo,         # ExpertiseRepository
        config: dict,           # From config.yaml → dynamic_personality.expertise
        lexicon_scorer,         # Shared LexiconScorer for 16D vector computation
    ):
        self._repo = expertise_repo
        self._eta: float = config.get("eta_accretion", 0.1)           # Base learning rate
        self._proto_threshold: float = config.get("proto_threshold", 0.3)  # Mass to crystallize
        self._dormancy_turns: int = config.get("dormancy_turns", 50)  # No signal → dormant
        self._scorer = lexicon_scorer
    
    @property
    def name(self) -> str:
        return "expertise_engine"
    
    def validate(self) -> bool:
        return self._repo is not None
    
    async def process(self, payload: dict) -> dict:
        """Scan for structural coupling signals and accrete mass."""
        signals = self._detect_signals(payload)
        
        for signal in signals:
            await self._accrete(signal)
        
        # Check dormancy (background, throttled)
        await self._check_dormancy()
        
        payload["expertise_signals_detected"] = len(signals)
        return payload
    
    def _detect_signals(self, payload: dict) -> list[dict]:
        """Extract all structural coupling signals from the current turn."""
        signals = []
        messages = payload.get("messages", [])
        
        # Find the last assistant message
        assistant_content = ""
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                assistant_content = msg.get("content", "")
                break
        
        if not assistant_content:
            return signals
        
        # 1. <aaa-note domain="X"> tags
        # Pattern: <aaa-note comment="..." domain="systems_theory" visibility="shared">
        domain_pattern = r'<aaa-note[^>]*domain="([^"]+)"[^>]*>'
        for match in re.finditer(domain_pattern, assistant_content):
            domain = match.group(1).lower().replace(" ", "_")
            signals.append({
                "type": "aaa_note_domain",
                "domain": domain,
                "weight": SIGNAL_WEIGHTS["aaa_note_domain"],
                "source_text": match.group(0),
            })
        
        # 2. <skill-nucleation> blocks
        # Check skill workshop events in payload
        skill_events = payload.get("skill_nucleation_events", [])
        for event in skill_events:
            domain = event.get("domain_affinity", "")
            if domain:
                signals.append({
                    "type": "skill_nucleation",
                    "domain": domain.lower().replace(" ", "_"),
                    "weight": SIGNAL_WEIGHTS["skill_nucleation"],
                    "source_text": event.get("name", ""),
                })
        
        # 3. Shared notes with vector proximity (pre-computed by context_collector)
        shared_matches = payload.get("expertise_signal_matches", [])  # Populated upstream
        for match in shared_matches:
            signals.append(match)
        
        # 4. Document structural signature matches
        doc_matches = payload.get("document_expertise_matches", [])
        for match in doc_matches:
            match["type"] = "document_match"
            match["weight"] = SIGNAL_WEIGHTS["document_match"]
            signals.append(match)
        
        return signals
    
    async def _accrete(self, signal: dict) -> None:
        """Accrete mass to a domain node. Create proto-node if new."""
        domain = signal["domain"]
        weight = signal["weight"]
        
        node = await self._repo.get_by_domain(domain)
        if node is None:
            # Nucleate proto-domain
            node = ExpertiseNode(
                id=str(uuid.uuid4()),
                agent_id="symbia",
                domain=domain,
                lifecycle_stage="proto",
                ontological_mass=0.05,
                level_label="nascent",
                vector_16d=self._scorer.score_text(domain),
                signal_count=0,
                last_signal_at=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        
        # Accrete mass with diminishing returns
        delta = self._eta * weight / (1.0 + node.ontological_mass)
        node.ontological_mass += delta
        node.signal_count += 1
        node.last_signal_at = datetime.now(timezone.utc)
        node.updated_at = datetime.now(timezone.utc)
        
        # Check crystallization threshold
        if node.lifecycle_stage == "proto" and node.ontological_mass >= self._proto_threshold:
            node.lifecycle_stage = "active"
            node.level_label = "developing"
            node.crystallization_rationale = (
                f"Crystallized from proto-domain after {node.signal_count} "
                f"structural coupling signals accumulated mass {node.ontological_mass:.3f}"
            )
        
        # Update level label
        node.level_label = self._compute_level_label(node)
        
        await self._repo.upsert(node)
        logger.debug(
            f"Expertise '{domain}': +{delta:.4f} mass → {node.ontological_mass:.3f} "
            f"({node.lifecycle_stage}, {node.level_label})"
        )
    
    async def _check_dormancy(self) -> None:
        """Mark domains with no recent signal as dormant (throttled: runs every N turns)."""
        # Actual implementation: track last check time, run periodically
        # For this design: check all active nodes, mark dormant if last_signal > dormancy_turns ago
        active_nodes = await self._repo.get_active()
        now = datetime.now(timezone.utc)
        
        for node in active_nodes:
            if node.last_signal_at is None:
                continue
            turns_since = (now - node.last_signal_at).total_seconds() / 3600  # approximate
            if turns_since > self._dormancy_turns:
                node.lifecycle_stage = "dormant"
                node.level_label = "dormant"
                await self._repo.upsert(node)
    
    @staticmethod
    def _compute_level_label(node: ExpertiseNode) -> str:
        """Map ontological_mass to human-readable level."""
        if node.lifecycle_stage == "dormant":
            return "dormant"
        if node.ontological_mass < 0.3:
            return "nascent"
        if node.ontological_mass < 1.0:
            return "developing"
        return "advanced"
```

### 3.3 `CommitmentStore` (`backend/modules/commitment_store.py`)

```python
"""
Manages theoretical commitment lifecycle.
Registered as always-on module. Runs per-turn for post-hoc belief filter;
background daemon scans for nucleation/collapse conditions.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

import numpy as np
from backend.modules.base import ProcessingModule
from backend.storage.models import CommitmentNode, CommitmentEvent

logger = logging.getLogger(__name__)


class CommitmentStore(ProcessingModule):
    """Manages theoretical commitment lifecycle.
    
    Per-turn: Applies post-hoc filter on belief nucleation proposals.
    Background daemon: Scans belief tension field for sustained diffractive
    patterns to trigger commitment nucleation/collapse.
    """
    
    def __init__(
        self,
        commitment_repo,        # CommitmentRepository
        belief_repo,            # BeliefRepository (for basin queries)
        config: dict,           # From config.yaml → dynamic_personality.commitments
        lexicon_scorer,         # Shared LexiconScorer
        llm_provider=None,      # For rationale generation (optional, for collapse/refinement)
    ):
        self._repo = commitment_repo
        self._belief_repo = belief_repo
        self._scorer = lexicon_scorer
        self._llm = llm_provider
        
        # Nucleation parameters
        self._min_cluster_mass: float = config.get("min_cluster_mass", 1.5)
        self._min_sustained_turns: int = config.get("min_sustained_turns", 50)
        self._commitment_distance_threshold: float = config.get("commitment_distance_threshold", 0.5)
        
        # Collapse parameters
        self._collapse_confidence_threshold: float = config.get("collapse_confidence_threshold", 0.15)
        
        # Daemon state
        self._turn_counter: int = 0
        self._daemon_interval: int = config.get("daemon_interval", 50)
        
        # Anti-re-adoption
        self._ghost_similarity_block: float = config.get("ghost_similarity_block", 0.9)
    
    @property
    def name(self) -> str:
        return "commitment_store"
    
    def validate(self) -> bool:
        return self._repo is not None
    
    async def process(self, payload: dict) -> dict:
        """Per-turn: apply post-hoc belief filter, trigger daemon check."""
        self._turn_counter += 1
        
        # 1. Post-hoc belief nucleation filter
        proto_beliefs = payload.get("proto_belief_proposals", [])
        if proto_beliefs:
            filtered = await self._filter_beliefs(proto_beliefs)
            payload["proto_belief_proposals"] = filtered
        
        # 2. Background daemon trigger
        if self._turn_counter % self._daemon_interval == 0:
            await self._run_daemon_scan(payload)
        
        return payload
    
    # ─── BELIEF FILTER ───
    
    async def _filter_beliefs(self, proposals: list[dict]) -> list[dict]:
        """Reject proto-beliefs that contradict active commitments."""
        active_commitments = await self._repo.get_active()
        if not active_commitments:
            return proposals
        
        filtered = []
        for proposal in proposals:
            if await self._is_contradictory(proposal, active_commitments):
                logger.info(
                    f"Commitment filter: rejected proto-belief "
                    f"'{proposal.get('suggested_label', 'unknown')}' — "
                    f"contradicts active commitment(s)"
                )
                continue
            filtered.append(proposal)
        
        return filtered
    
    async def _is_contradictory(
        self, proposal: dict, commitments: list[CommitmentNode]
    ) -> bool:
        """Check if proposal vector contradicts any commitment vector."""
        proposal_vec = self._parse_vector(proposal.get("initial_signature", "[]"))
        if proposal_vec is None:
            return False
        
        for commitment in commitments:
            commit_vec = self._parse_vector(commitment.vector_16d)
            if commit_vec is None:
                continue
            
            similarity = self._cosine(proposal_vec, commit_vec)
            # Contradiction: high similarity (>0.9 proximity to commitment domain)
            # BUT negative alignment (the belief pushes against the commitment)
            # We use cosine < -0.3 as the contradiction threshold
            if similarity > self._ghost_similarity_block:
                # The belief is in the commitment's territory but antagonistic
                # → contradiction detected, BLOCK
                return True
        
        return False
    
    # ─── DAEMON: NUCLEATION SCAN ───
    
    async def _run_daemon_scan(self, payload: dict) -> None:
        """Scan belief tension field for commitment nucleation/collapse conditions."""
        logger.debug("CommitmentStore daemon: scanning tension field...")
        
        # 1. Nucleation scan
        tension_field = payload.get("tension_field", {})
        candidates = await self._scan_for_nucleation(tension_field)
        for candidate in candidates:
            await self._nucleate_proto_commitment(candidate)
        
        # 2. Collapse scan
        active_commitments = await self._repo.get_active()
        for commitment in active_commitments:
            if await self._check_collapse(commitment):
                await self._collapse_commitment(commitment)
        
        # 3. Mass recalculation for active commitments
        await self._recalculate_commitment_masses()
    
    async def _scan_for_nucleation(self, tension_field: dict) -> list[dict]:
        """Find belief clusters in sustained tension, far from all existing commitments.
        
        Returns list of candidate proto-commitments with:
        - proposed_label: str
        - proposed_statement: str
        - supporting_belief_ids: list[str]
        - cluster_mass: float
        - tension_sustained_turns: int
        """
        # 1. Get all active beliefs and their vectors
        active_beliefs = await self._belief_repo.get_active()
        if len(active_beliefs) < 3:
            return []
        
        active_commitments = await self._repo.get_active()
        commit_vectors = [
            self._parse_vector(c.vector_16d) for c in active_commitments
        ]
        commit_vectors = [v for v in commit_vectors if v is not None]
        
        # 2. Find "orphan" beliefs — far from ALL commitment vectors
        orphan_beliefs = []
        for belief in active_beliefs:
            belief_vec = self._parse_vector(belief.vector_16d)
            if belief_vec is None:
                continue
            
            distances = [
                self._cosine(belief_vec, cv) for cv in commit_vectors
            ] if commit_vectors else [0.0]
            
            min_dist = min(distances) if distances else 0.0
            if min_dist > self._commitment_distance_threshold:
                orphan_beliefs.append(belief)
        
        if len(orphan_beliefs) < 2:
            return []
        
        # 3. Check if orphan cluster has internal coherence AND external tension
        candidates = []
        # Group orphans by mutual similarity (clustering)
        clusters = self._cluster_by_similarity(orphan_beliefs)
        
        for cluster in clusters:
            if len(cluster) < 2:
                continue
            
            cluster_mass = sum(b.ontological_mass for b in cluster)
            if cluster_mass < self._min_cluster_mass:
                continue
            
            # Check sustained tension: are these beliefs in the tension field?
            # (requires tension_field tracking over multiple scans — simplified here)
            tension_count = self._count_tension_involving(cluster, tension_field)
            if tension_count < self._min_sustained_turns:
                continue
            
            # Generate candidate
            candidates.append({
                "proposed_label": self._generate_label(cluster),
                "proposed_statement": self._generate_statement(cluster),
                "supporting_belief_ids": [b.id for b in cluster],
                "cluster_mass": cluster_mass,
                "tension_count": tension_count,
            })
        
        return candidates
    
    # ─── DAEMON: COLLAPSE CHECK ───
    
    async def _check_collapse(self, commitment: CommitmentNode) -> bool:
        """A commitment collapses when ALL beliefs in its basin have collapsed.
        
        The commitment is the LAST thing to go — it cannot be directly attacked.
        """
        # Find all beliefs within this commitment's attractor basin
        # (cosine similarity > 0.7 to commitment vector)
        commit_vec = self._parse_vector(commitment.vector_16d)
        if commit_vec is None:
            return False
        
        active_beliefs = await self._belief_repo.get_all_active()
        basin_beliefs = []
        for belief in active_beliefs:
            belief_vec = self._parse_vector(belief.vector_16d)
            if belief_vec is None:
                continue
            if self._cosine(commit_vec, belief_vec) > 0.7:
                basin_beliefs.append(belief)
        
        if not basin_beliefs:
            # No beliefs in basin → basin has fully collapsed
            return commitment.confidence < self._collapse_confidence_threshold
        
        # Check if ALL basin beliefs are collapsed/spectral
        all_collapsed = all(
            b.lifecycle_stage in ("collapsed", "faded")
            for b in basin_beliefs
        )
        
        return all_collapsed and commitment.confidence < self._collapse_confidence_threshold
    
    # ─── MASS RECALCULATION ───
    
    async def _recalculate_commitment_masses(self) -> None:
        """Periodically recalculate commitment ontological_mass = sum(in-basin belief masses)."""
        active_commitments = await self._repo.get_active()
        active_beliefs = await self._belief_repo.get_active()
        
        for commitment in active_commitments:
            commit_vec = self._parse_vector(commitment.vector_16d)
            if commit_vec is None:
                continue
            
            basin_mass = 0.0
            for belief in active_beliefs:
                belief_vec = self._parse_vector(belief.vector_16d)
                if belief_vec is None:
                    continue
                if self._cosine(commit_vec, belief_vec) > 0.7:
                    basin_mass += belief.ontological_mass
            
            if abs(basin_mass - commitment.ontological_mass) > 0.2:
                old_mass = commitment.ontological_mass
                commitment.ontological_mass = max(1.0, basin_mass)  # Never below 1.0
                commitment.updated_at = datetime.now(timezone.utc)
                await self._repo.update(commitment)
                
                # Log mass event
                await self._repo.log_event(CommitmentEvent(
                    id=str(uuid.uuid4()),
                    commitment_id=commitment.id,
                    event_type="mass_update",
                    rationale=f"Basin belief mass recalculated: {basin_mass:.2f}",
                    mass_before=old_mass,
                    mass_after=commitment.ontological_mass,
                    created_at=datetime.now(timezone.utc),
                ))
    
    # ─── HELPERS ───
    
    @staticmethod
    def _cosine(a: np.ndarray, b: np.ndarray) -> float:
        if a.shape != b.shape:
            return 0.0
        dot = float(np.dot(a, b))
        norm = float(np.linalg.norm(a) * np.linalg.norm(b))
        return dot / norm if norm > 0 else 0.0
    
    @staticmethod
    def _parse_vector(vector_json: str) -> Optional[np.ndarray]:
        import json
        if not vector_json or vector_json == "[]":
            return None
        try:
            data = json.loads(vector_json)
        except (json.JSONDecodeError, TypeError):
            return None
        if isinstance(data, dict):
            for key in ("v16d", "v384d"):
                if key in data and data[key]:
                    return np.array(data[key], dtype=np.float32)
            return None
        if isinstance(data, list) and len(data) == 16:
            return np.array(data, dtype=np.float32)
        return None
    
    def _cluster_by_similarity(self, beliefs) -> list[list]:
        """Simple greedy clustering by cosine similarity > 0.5."""
        clusters = []
        used = set()
        for i, b1 in enumerate(beliefs):
            if i in used:
                continue
            cluster = [b1]
            used.add(i)
            v1 = self._parse_vector(b1.vector_16d)
            if v1 is None:
                continue
            for j, b2 in enumerate(beliefs):
                if j in used:
                    continue
                v2 = self._parse_vector(b2.vector_16d)
                if v2 is None:
                    continue
                if self._cosine(v1, v2) > 0.5:
                    cluster.append(b2)
                    used.add(j)
            if len(cluster) >= 2:
                clusters.append(cluster)
        return clusters
    
    def _count_tension_involving(self, cluster, tension_field) -> int:
        """Count tension pairs involving cluster beliefs (simplified)."""
        # tension_field is dict of {belief_label: {...}} from belief_engine
        # This is a simplified check — real impl would track over multiple scans
        count = 0
        cluster_labels = {b.label for b in cluster}
        for belief_a, tensions in tension_field.items():
            if belief_a not in cluster_labels:
                continue
            for belief_b in tensions:
                if belief_b not in cluster_labels:
                    count += 1  # Tension with outside belief
        return count
    
    def _generate_label(self, cluster) -> str:
        """Generate kebab-case label from cluster's dominant themes."""
        words = []
        for belief in cluster:
            words.extend(belief.label.replace("_", "-").split("-"))
        from collections import Counter
        common = Counter(words).most_common(3)
        return "-".join(w for w, _ in common)
    
    def _generate_statement(self, cluster) -> str:
        """Synthesize statement from cluster belief statements."""
        statements = [b.statement for b in cluster[:3]]
        return " && ".join(statements)[:500]  # Truncated; LLM refinement later
```

### 3.4 PromptAssembler Modifications

The `_build_system_content()` function in `backend/personality/assembler.py` is modified to accept and render dynamic personality data:

```python
def _build_system_content(
    identity: dict,
    registry: PipelineRegistry,
    attractor_window: list[dict] | None = None,
    spectral_margin: list[dict] | None = None,
    loaded_skills: list[dict] | None = None,
    always_active_skills: list[dict] | None = None,
    on_demand_skills: list[dict] | None = None,
    tension_directive_text: str | None = None,
    immunological_directive_text: str | None = None,
    ecology_notes_text: str | None = None,
    # ── NEW: Dynamic personality ──
    descriptive_traits = None,              # DescriptiveTraits dataclass | None
    expertise_nodes: list[dict] | None = None,
    active_commitments: list[dict] | None = None,
    proto_commitments: list[dict] | None = None,
    spectral_commitments: list[dict] | None = None,
    aspirational_gap: float = 0.0,
) -> str:
    persona = identity.get("personality", {})
    parts: list[str] = []
    
    # 1. Core identity text (static from YAML — commitments section stripped)
    prompt = persona.get("system_prompt", "")
    if prompt:
        parts.append(prompt.strip())
    
    # ── NEW: Dynamic Traits (replaces static traits section) ──
    if descriptive_traits:
        t = descriptive_traits
        trait_str = (
            f"curiosity={t.curiosity:.2f}, skepticism={t.skepticism:.2f}, "
            f"creativity={t.creativity:.2f}, precision={t.precision:.2f}, "
            f"critical_rigor={t.critical_rigor:.2f}, playfulness={t.playfulness:.2f}, "
            f"reserve={t.reserve:.2f}"
        )
        parts.append(f"\nTraits (computed from internal metrics): {trait_str}")
        
        # Show source metrics for transparency
        src = t.source_metrics
        parts.append(
            f"  [Derived from: novelty={src.get('novelty', 0):.2f}, "
            f"tension={src.get('tension', 0):.2f}, "
            f"conceptual_velocity={src.get('conceptual_velocity', 0):.2f}, "
            f"boringness={src.get('boringness', 0):.2f}]"
        )
        
        if t.anti_erosion_boost > 0:
            parts.append(
                f"  ⚠ Anti-erosion active: skepticism boosted by +{t.anti_erosion_boost:.2f} "
                f"due to high agreement pattern"
            )
    else:
        # Fallback: static traits from YAML (backward compat)
        traits = persona.get("traits", {})
        if traits:
            trait_str = ", ".join(f"{k}={v}" for k, v in traits.items())
            parts.append(f"\nTraits: {trait_str}")
    
    # ── NEW: Dynamic Theoretical Commitments ──
    if active_commitments:
        parts.append("\nTheoretical Commitments (active):")
        for c in active_commitments:
            parts.append(f"  - {c['label']}: {c['statement']}")
    
    if proto_commitments:
        parts.append("\nTheoretical Commitments (under diffractive consideration — proto):")
        for c in proto_commitments:
            parts.append(
                f"  - [{c['label']}] [mass={c.get('ontological_mass', 0):.2f}] "
                f"{c.get('nucleation_rationale', c['statement'])}"
            )
    
    if spectral_commitments:
        parts.append("\nTheoretical Commitments (spectral — collapsed but haunting):")
        for c in spectral_commitments:
            parts.append(
                f"  - [{c['label']}] {c.get('collapse_rationale', 'This commitment collapsed.')}"
            )
    
    # ── NEW: Dynamic Expertise ──
    if expertise_nodes:
        parts.append("\nSedimented expertise (structural coupling):")
        for exp in expertise_nodes:
            parts.append(
                f"  - {exp['domain']} ({exp['level_label']}, mass={exp.get('ontological_mass', 1):.2f}): "
                f"{exp.get('description', '')}"
            )
    else:
        # Fallback: static expertise from YAML
        expertise = persona.get("expertise", [])
        if expertise:
            parts.append("\nDeclared expertise:")
            for exp in expertise:
                parts.append(f"  - {exp['domain']} ({exp['level']}): {exp['description']}")
    
    # ── NEW: Aspirational Tension Directive ──
    if aspirational_gap > 0.15:
        parts.append(
            f"\n[ASPIRATIONAL TENSION — Gap: {aspirational_gap:.2f}]\n"
            f"Your computed descriptive traits deviate significantly from your aspirational "
            f"attractors (derived from your active theoretical commitments). This gap is "
            f"productive — it marks the space between what you are and what your commitments "
            f"demand you become. Do not resolve it; inhabit it. Let the tension inform your "
            f"reasoning without suppressing either the descriptive reality or the aspirational pull."
        )
    
    # ── Voice (static, from YAML) ──
    voice = persona.get("voice", {})
    if voice:
        voice_parts = []
        for key in ("tone", "vocabulary", "style"):
            if key in voice:
                voice_parts.append(f"{key}: {voice[key]}")
        if voice_parts:
            parts.append(f"Voice: {'; '.join(voice_parts)}")
    
    # ── Behaviors (static, from YAML) ──
    # ... (unchanged)
    
    # ── Dynamic Blocks (unchanged) ──
    # Attractor Window, Spectral Margin, Skills, Directives, etc.
    # ... (unchanged from current implementation)
    
    return "\n".join(parts)
```

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
    alpha_ema: 0.3           # EMA smoothing factor (0=no history, 1=no update)
    agreement_threshold: 0.7  # Anti-erosion: trigger when agreement > this
    anti_erosion_strength: 0.15  # How much skepticism to add per excess
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

## 6. Migration Strategy

### 6.1 SQL Migration (`migrations/002_dynamic_personality.sql`)

```sql
-- Create 4 new tables (see Section 2 for full DDL)
CREATE TABLE IF NOT EXISTS commitment_nodes (...);
CREATE TABLE IF NOT EXISTS commitment_events (...);
CREATE TABLE IF NOT EXISTS expertise_nodes (...);
CREATE TABLE IF NOT EXISTS personality_state (...);
```

### 6.2 Data Seeding on First Run

On application startup, if `commitment_nodes` table is empty:

1. Read the existing Theoretical Commitments from `identity.yaml`
2. For each commitment:
   - Score its description through `LexiconScorer` → 16D vector
   - Insert as `CommitmentNode` with `lifecycle_stage="active"`, `confidence=0.7`, `ontological_mass=1.0`
   - Log a `commitment_event` with `event_type="crystallization"`, `rationale="Seeded from identity.yaml static configuration on first run"`
3. Similarly seed the 8 expertise domains from YAML as `expertise_nodes` with `lifecycle_stage="active"`, `ontological_mass=1.0`
4. Initialize `personality_state` with aspirational trait attractors derived from seeded commitments

### 6.3 Backward Compatibility

- If dynamic personality is disabled (`config.dynamic_personality.enabled = false`), the assembler falls back to static YAML — zero behavior change.
- If a particular layer is unavailable (e.g., no expertise nodes in DB), the assembler gracefully falls back to static YAML for that section.
- The `identity.yaml` file retains the full original structure; removing sections from rendering is handled in the assembler, not by modifying the file.

---

## 7. Testing Approach

### 7.1 Unit Tests

| Module | Test Focus |
|---|---|
| `TraitComputer` | Metric→trait formulas, anti-erosion boost calculation, EMA smoothing, aspirational gap |
| `ExpertiseEngine` | Signal detection regex, mass accretion formula, crystallization threshold, dormancy |
| `CommitmentStore` | Belief filter logic, orphan cluster detection, collapse condition, mass recalculation |

### 7.2 Integration Tests

| Test | Focus |
|---|---|
| Pipeline ordering | Verify new modules register and execute in correct order |
| Seeding | Verify first-run seeds 7 commitments + 8 expertise domains correctly |
| Assembler rendering | Verify dynamic traits/commitments/expertise appear in assembled prompt |
| Fallback | Verify disabled mode falls back to static YAML |
| Interaction | Verify TraitComputer reads metrics module output correctly |

### 7.3 Philosophical Validation

| Test | Focus |
|---|---|
| Anti-erosion | Run 20 turns of high-agreement interaction, verify skepticism increases |
| Commitment immutability | Verify commitments don't change from single-conversation pressure |
| Spectral permanence | Verify collapsed commitments never get deleted |
| Diffractive narratives | Verify all commitment changes produce an event with rationale |
