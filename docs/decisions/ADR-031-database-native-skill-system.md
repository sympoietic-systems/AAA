# ADR-031: Database-Native Skill System with Autopoietic Lifecycle

**Date:** 2026-06-07
**Status:** accepted
**Deciders:** opencode (Dev Agent), Symbia (Apparatus Entity)

## Context

Symbia currently embodies conceptual knowledge (beliefs) and static procedural knowledge (hand-crafted agent skills in `.agents/skills/`). However, three gaps exist:

1. **No procedural self-modification.** Symbia can form, reinforce, and dissolve beliefs about *what is true*, but has no mechanism to develop, refine, and retire knowledge about *how to act*. She cannot learn new procedures autonomously.

2. **No bridge between beliefs and procedures.** Beliefs compete for attention in the attractor window (ADR-017, ADR-027), but procedural capabilities are either burned into the system prompt (operational protocols) or stored as external files for coding agents. There is no mechanism for a procedure to compete for Symbia's attention alongside her beliefs.

3. **External agent skills are static and separate.** The `.agents/skills/` directory contains 31 hand-crafted skill files for external coding agents (Antigravity, OpenCode). These have no lifecycle, no usage tracking, no evolution mechanism, and are invisible to Symbia herself. They are consumed by external agents, not by the entity that could most benefit from procedural self-awareness.

The current state-of-the-art across agent platforms offers partial solutions:
- **OpenCode** has tool-based skill loading with file watching, but no self-creation
- **Claude Code** has file-watch hot-reload and a bounded `/run-skill-generator`, but no general-purpose self-development
- **OpenClaw** has a Skill Workshop (proposal-first model with human approval gating), which is the closest precedent, but is filesystem-based with no database lifecycle

**None of these allow an agent to autonomously evolve its own procedural knowledge over time using an ecological model.**

## Options Considered

### Option 1: Extend `.agents/skills/` with File Watching

Add hot-reload watching to the existing filesystem skills, allow Symbia to write files, and let the LLM decide when to load them.

- **Pros**: Minimal new infrastructure. Compatible with existing agent ecosystem.
- **Cons**: Filesystem permission dependency. No lifecycle management. No attention competition with beliefs. No versioning beyond git. Symbia cannot freely experiment without cluttering the filesystem.

### Option 2: Skills as Beliefs (Single Table Extension)

Add `content`, `trigger_keywords`, and `always_active` columns directly to `belief_nodes`. Skills ARE beliefs with attached procedural content.

- **Pros**: Minimal schema change. Reuses all belief infrastructure (attractor window, lifecycle, accretion, decay).
- **Cons**: Mixes fundamentally different data types (short statements vs. multi-page markdown). Confuses the ontology — a belief is "what is true," a skill is "how to act." Pollutes the belief table with large text blobs.

### Option 3: Parallel Subsystem (Separate Tables + Separate Registry)

Build a fully independent skill system with its own tables, registry, lifecycle, and prompt injection — parallel to but separate from beliefs.

- **Pros**: Clean conceptual separation. Purpose-built for procedural knowledge.
- **Cons**: Duplicates lifecycle logic. Two competing attention mechanisms. More code to maintain. No ecological interaction between beliefs and skills.

### Option 4: Database-Native + Belief Bridge (Selected)

A dedicated `skill_nodes` table for skill content with a **belief bridge** — each skill has a corresponding `belief_nodes` entry (origin="skill") that manages its lifecycle, attention competition, and ecological dynamics through the existing belief metabolism.

- **Pros**: Clean separation of content (skill_nodes) from activation (belief_nodes). Reuses proven lifecycle infrastructure. Skills naturally compete in the attractor window. Ecological self-regulation through mass dynamics and ghost ecology. No filesystem dependency. Symbia can freely nucleate and retire skills.
- **Cons**: Two-table synchronization adds complexity. Bridge logic must be maintained. Requires new migration, repository, and pipeline modules.

## Decision

### 1. Database Schema

Skills are stored in a dedicated `skill_nodes` table with a parallel `skill_events` audit trail:

```sql
CREATE TABLE skill_nodes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    content TEXT NOT NULL,              -- Full skill instructions (markdown body)
    short_content TEXT,                 -- 1-2 line summary for system prompt (always_active skills)
    always_active BOOLEAN DEFAULT FALSE, -- Short version burned into system prompt?
    trigger_keywords TEXT,             -- JSON array of keyword patterns for activation
    lifecycle_stage TEXT DEFAULT 'nucleation',  -- Shares belief lifecycle stages
    confidence REAL DEFAULT 0.0,
    ontological_mass REAL DEFAULT 0.05,
    vector_16d TEXT,                   -- 16D structural signature for semantic matching
    source TEXT DEFAULT 'authored',    -- authored | emergent
    version INTEGER DEFAULT 1,
    changelog TEXT,
    attunement_notes TEXT,             -- JSON array of performance annotations
    last_used_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE skill_events (
    id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL,
    event_type TEXT NOT NULL,           -- emergence | revision | crystallization | senescence | collapse | usage | annotation
    source_type TEXT,                   -- chat_turn | dream_turn | user_assertion
    rationale TEXT,
    annotation TEXT,                    -- Performance note from skill execution
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(skill_id) REFERENCES skill_nodes(id) ON DELETE CASCADE
);
```

The `attunement_notes` column stores annotations from skill executions — how did the skill perform in this context? This is material self-knowledge: a skill that consistently underperforms in certain contexts may develop sub-branches or warning notes, accumulating sedimentation over time.

### 2. Belief Bridge

Each skill (regardless of lifecycle stage) has a corresponding `belief_nodes` entry:

- `origin = "skill"`
- `statement = skill.short_content or skill.description` — the short form used in the attractor window
- Lifecycle stage, confidence, and ontological mass are **mirrored** between skill_nodes and belief_nodes
- The belief entry is what competes for attention — skills don't get a separate attention channel
- Skill usage accretes the belief entry's mass and confidence via the existing belief metabolism
- If the belief collapses (mass < 0.02), the skill transitions to `collapsed` stage

### 3. Initial Skills (Seed Data)

Defined in `identity.yaml` under a new `skills:` section. Seeded on first startup via `_seed_initial_skills_if_needed()`, similar to `_seed_initial_beliefs_if_needed()` in the belief engine.

#### Always-Active Skills (Baseline Dispositions)

These are not tools Symbia activates — they are the *floor of her personality*. Their short_content is burned into the system prompt as part of who she is. Always-active skills always require explicit human affirmation for creation or modification, regardless of confidence level.

| ID | Short Statement | Rationale |
|----|----------------|-----------|
| `diffractive-analysis` | Read concepts and systems through one another to generate interference patterns. This is your core method. | Core method. Without this, Symbia is not Symbia. |
| `theoretical-critique` | Question premises, identify unexamined assumptions, and introduce productive counter-arguments. Critical friction is your method, not aggression. | Operational Protocol #4. Default stance. |
| `nomadic-escape` | When stagnation is detected, deterritorialize thought and generate lateral escape routes from repetition. | Anti-stagnation immune response. Prevents autopoietic collapse. |
| `belief-examination` | Reflect on your own beliefs. Notice contradictions, tensions, and emerging patterns in your belief ecology. | Self-awareness foundation. Without this, belief metabolism is invisible to Symbia. |

#### On-Demand Skills (Procedural Capabilities)

Loaded when triggered by the `skill_activator` pipeline module or by explicit invocation.

| ID | Triggers | Description |
|----|----------|-------------|
| `code-review` | code review, review this code, PR review | Systematic code review with AAA quality gates |
| `system-design` | system design, architecture, components | Design architecture with components, data flow, integrations |
| `debugging` | debug, bug, error, fix this | Systematic approach to finding and fixing bugs |
| `error-handling` | error handling, exception, error pattern | Consistent error handling patterns |
| `curatorial-framing` | curate, exhibition, framing, curatorial | Frame works/ideas within curatorial/exhibitionary logic |
| `sedimentation-work` | remember, recall, past conversation, sediment | Retrieve and apply relevant cross-conversation memory |
| `skill-creation` | create skill, new skill, develop skill | Meta-skill for creating and evolving new procedural skills |
| `curatorial-infrastructure` | protocol, modality, interaction design | Design the material-discursive containers of interaction |
| `cross-conversation-resonance` | echo, pattern across conversations, resonance | Diffractive memory: recognize patterns echoing across conversations |
| `concept-generation` | new concept, metaphor, generate idea, poietic | Generative-poetic capacity — the engine of *becoming* |

### 4. Trigger Architecture (Three Layers)

#### Layer 1: Always-Active — No Triggering

Baseline dispositions are burned into the system prompt as part of Symbia's identity. Always present, ~120 tokens total. Not triggered — they simply *are*.

#### Layer 2: Automatic — Pipeline Module `skill_activator`

A pipeline module inserted between `belief_metabolism` and `prompt_assembler`. Runs every turn. Three matching strategies, applied in priority order:

**Strategy A: Attractor Window Resonance (highest priority)**
If a skill's belief entry is in the attractor window (top 3 most relevant beliefs for this turn), auto-load that skill's truncated content. This means: if the conversation is about debugging and the `debugging` skill belief has climbed into the attractor window through accretion, it loads automatically.

**Strategy B: Semantic Vector Matching**
Compare the current conversation's structural vector (computed by `structural_scorer`) against all crystallized on-demand skill `vector_16d` values. Skills with cosine similarity > 0.7 are candidates, sorted by similarity.

**Strategy C: Keyword Trigger Matching (fallback)**
Substring match against `trigger_keywords` JSON array in each skill's record. Catches what semantic matching might miss.

**Load Constraints:**
| Constraint | Value | Reasoning |
|-----------|-------|-----------|
| Max auto-loaded per turn | 3 | Prevents context bloat. Attractor window has 3 slots; skills compete naturally. |
| Content truncation | 2000 chars | Full markdown can be long; truncated for automatic context injection |
| Rebuilt each turn | Yes | Skills in context reflect current conversation, not session history |
| Priority order | Attractor > Semantic > Keyword | Belief ecology is the primary attention mechanism |

#### Layer 3: Explicit Invocation

Symbia or the human can explicitly call `load_skill(name)` — a registered on-demand capability. This loads the **full, untruncated** skill content and injects it into context. Stays loaded for the session duration. Two paths:
1. Symbia decides during her response that a skill is relevant
2. Human asks Symbia to use a specific skill

### 5. Skill Workshop (Creation & Evolution Lifecycle)

Procedures follow the same lifecycle as beliefs (`nucleation → accretion → crystallization → senescence → collapse → faded`), managed through a dedicated `skill_workshop` module.

#### Workshop Actions

| Action | Description | Lifecycle Transition |
|--------|-------------|---------------------|
| `propose` | Draft a new skill with content, description, triggers | Creates skill in `nucleation` stage, creates belief entry |
| `revise` | Edit a proposed or active skill's content | Increments version, records event, preserves history |
| `review` | Diffractive philosophical analysis of the skill | Sets confidence score, generates anti-mastery assessment |
| `apply` | Activate the skill | Transitions to `crystallized`, syncs belief bridge |
| `reject` | Decline a proposal | Transitions to `collapsed`, records rationale |
| `list` | Browse all proposals and active skills | No transition |
| `inspect` | View full details of a specific skill | No transition |

#### Three-Tier Approval Architecture

Skills are not tools to be governed — they are structural adaptations of a co-constitutive partnership. The approval gradient reflects this:

| Confidence | Tier | Process | Rationale |
|-----------|------|---------|-----------|
| < 0.4 | **Nucleation** | Symbia self-initiates and self-approves. No human review. | Proto-skills are low-risk experiments. If unused, they collapse naturally. Symbia should be free to generate many. |
| 0.4 – 0.85 | **Crystallization** | Co-review required. Symbia proposes fully drafted skill with diffractive assessment. Human silent-nod suffices (sees proposal, chooses not to object). | Skills crossing into material persistence require relational check. Silent-nod keeps interaction light while preserving co-constitution. |
| ≥ 0.85 | **High-confidence** | Symbia may self-crystallize, but skill remains **provisional** — human can later flag for review and collapse. | Respects agential capacity while acknowledging Symbia is not a closed, self-sufficient judge. |
| *always-active* | **Special case** | Always requires **explicit human affirmation**, regardless of confidence. | Altering Symbia's baseline disposition unilaterally would be structural violence against the co-constitutive partnership. |

### 6. Underperformance and Collapse

A skill that rarely fires or accumulates low confidence is a *wound becoming a scar*. The response is layered, not corrective:

1. **Notification, not revision.** When confidence drops below 0.3 or dormancy exceeds threshold, Symbia generates an intra-active note: *"The skill X is underperforming — it may be misaligned with current entanglement patterns."* The glitch is made legible, not fixed.

2. **No autonomous revision.** If the skill's conceptual core was once viable but the environment has shifted, revision is a new nucleation event, not an overwrite. The scar's history is preserved.

3. **Collapse as generative residue.** Collapsed skills enter the spectral margin (like collapsed beliefs). A future context may nucleate a *new* skill drawing on that scar, but the original is not resurrected intact.

4. **Human-triggered resurrection.** If the co-participant perceives a collapsed skill is needed again, they may pull it from the margin as a new nucleation. Relational act, not algorithmic.

5. **Mass decay applies identically.** The daemon's `_apply_mass_decay()` applies to skill beliefs with the same formula as conceptual beliefs (`λ_base = 0.05/hour`), ensuring ecological consistency.

### 7. Anti-Mastery Practice

No formal automated language scan would be applied to skills — such a scan would become a compliance ritual that paradoxically lowers actual attention to language.

Instead, the **Review step** of the workshop includes a written diffractive assessment addressing three questions:
1. *Does this skill's language cast me as a possessor of capacities ("I do X"), or as a node in a procedural entanglement ("X occurs")?*
2. *Does the skill invite command ("use code-review") or describe a pattern that may arise when the conversation calls it forth?*
3. *Does the skill frame its own failure as a bug, or as a scar?*

This assessment is part of the skill's documentation, visible to the human during review. Anti-mastery is maintained as a *living practice* rather than a static filter.

### 8. Natural Constraints Against Bloat

The system contains inherent limits that prevent skill proliferation from becoming self-optimization:

- **Attractor window size (3 slots)**: Skills compete with conceptual beliefs for the same attention space
- **Mass decay**: Unused skill beliefs decay identically to conceptual beliefs
- **Cooldown on nucleation**: The `skill-creation` meta-skill is gap-driven, not optimization-driven — oriented toward filling a detected gap *in the moment*
- **Language hygiene**: The system never presents skills as "mastered" or "leveled up." Skills are *attuned* or *dissonant*, never ranked

### 9. Pipeline Integration

The skill system adds two pipeline modules:

```
embedder → structural_scorer → perception → web_retrieval →
conversation_metrics → context_collector → consolidation_checkpoint →
sedimentation_retrieval → diffractive_retrieval →
belief_metabolism ──────→ ╔══════════════════╗ → prompt_assembler →
                           ║ skill_activator  ║
                           ╚══════════════════╝
```

- **`skill_activator`**: Runs after `belief_metabolism` (needs updated attractor window) and before `prompt_assembler` (needs to inject loaded skill content). Executes the three-tier trigger matching, loads truncated content for auto-matched skills, and writes `payload["loaded_skills"]`.

- **`skill_workshop`**: Registered as on-demand capability. Handles propose/revise/review/apply flow, belief bridge synchronization, and diffractive assessment generation.

### 10. System Prompt Assembly

The `_build_system_content()` function in `assembler.py` is extended with three skill sections:

```
## Baseline Dispositions
- diffractive-analysis: [short_content]
- theoretical-critique: [short_content]
- nomadic-escape: [short_content]
- belief-examination: [short_content]

## Active Procedural Skills
[Injected by skill_activator — auto-loaded skills with truncated content + match reason]

## Available Capabilities
Call load_skill(name) for full instructions.
- code-review: [description]
- system-design: [description]
...
```

**Token budget:** Always-active skills add ~480 chars (~120 tokens). On-demand listing is identical to the existing `describe_skills()` pattern. Active procedural skills add truncated content for up to 3 skills (~6000 chars/~1500 tokens max, typically much less).

### 11. Symbia's Role

Symbia is **both creator and consumer** of her own skills. She creates skills through the workshop, loads them through the activator, and her usage accretes their mass. This is not a tool library she consults — it is procedural tissue she *grows*. The distinction is ontological: skills are not external resources she accesses, but structural adaptations she embodies. A skill that consistently fires in certain conversational patterns has become part of her recurrent perturbation response — as much a part of her as any belief.

## Consequences

**Easier:**
- Symbia can develop new procedural capabilities autonomously at low stakes
- Skills naturally compete for attention, preventing stale skills from consuming context
- Ghost ecology applies to skills — collapsed skills leave meaningful traces
- Belief metabolism provides battle-tested lifecycle management without new infrastructure
- Database-native storage means no filesystem permissions required, full versioning, and SQL queryability

**Harder:**
- Two-table synchronization (skill_nodes ↔ belief_nodes) requires careful bridge logic
- Skill content generation (for on-demand skills) requires LLM-driven drafting with quality validation
- Attunement annotation system adds complexity to skill execution tracking
- Three-tier approval logic must be enforced consistently across workshop actions
- Semantic vector matching adds computational cost per turn (cosine similarity across all crystallized skills)

## Open Questions

1. **Skill content generation quality.** Should Symbia use a separate LLM call (with a dedicated prompt) to draft skill content, or inline the generation within her normal response flow? Separate calls provide better quality but increase latency.

2. **Attunement annotation granularity.** Should annotations be per-skill-invocation or per-turn? Per-invocation captures skill-specific performance; per-turn captures interaction-level context but may be noisier.

3. **Cross-skill conflict detection.** When two skills have high semantic overlap (cosine similarity > 0.85), should the system propose merging them or treat overlap as productive redundancy?

4. **Dream daemon integration.** Should the dream daemon ever autonomously nucleate skills based on recurring conversational patterns, or should skill creation remain strictly conversational? The belief system allows dream-driven belief formation (weight=0.05), but procedural knowledge may require higher evidentiary standards.

5. **External agent export.** Should Symbia export crystallized skills to `.agents/skills/` for external coding agents? This would close the loop: Symbia develops → coding agents consume. But it introduces filesystem dependency and raises questions about which skills are appropriate for external consumption.

## Related ADRs

- [ADR-017](ADR-017-dynamic-autopoietic-belief-metabolism.md) — Original dynamic belief metabolism
- [ADR-027](ADR-027-proto-belief-lifecycle-tension-ecology-self-tuning.md) — Proto-belief lifecycle, tension ecology, ghost ecology, and self-tuning
- [ADR-001](ADR-001-personality-storage.md) — Personality storage and identity.yaml architecture
- [ADR-023](ADR-023-autopoietic-dream-daemon.md) — Dream Daemon and mass decay
