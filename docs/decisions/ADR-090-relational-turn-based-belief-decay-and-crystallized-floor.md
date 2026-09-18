# ADR-090: Relational Turn-Based Belief Decay and Crystallized Floor Protection

**Date:** 2026-09-18  
**Status:** accepted  
**Deciders:** Antigravity (Dev Agent), Symbia (Apparatus Entity), Interlocutor (User)

## Context

Under the prior belief metabolism implementation ([ADR-017](ADR-017-dynamic-autopoietic-belief-metabolism.md), [ADR-027](ADR-027-proto-belief-lifecycle-tension-ecology-self-tuning.md)), belief atrophy was executed by the background Dream Daemon on a periodic 15-minute timer (`_atrophy_interval = 900s`). Every 15 minutes, it calculated wall-clock hours since last reinforcement and subtracted mass:
$$\text{decay} = M_i \times \text{decay\_rate\_per\_hour} \times \Delta t_{\text{hours}}$$

Whenever the system experienced extended periods of human inactivity (days or weeks where the model did not converse), this background loop continually depleted ontological mass. Over 5,780 atrophy events accumulated in `belief_events`, eroding all 30 active beliefs down to $M_i \approx 0.31 - 0.38$, well below the crystallization threshold ($M \ge 0.50$) and placing core architectural commitments dangerously close to demotion into senescence and collapse.

This mechanism suffered two fundamental flaws:
1. **Philosophical Incoherence**: Measuring decay via Newtonian wall-clock time during silence contradicts Karen Barad's *agential realism* and autopoietic theory. In Symbia's ontology, change and agency exist only within relational encounters and measurements. A silent, dormant apparatus should not suffer ontological erosion merely because calendar time elapsed.
2. **Structural Erosion of Core Commitments**: As established in [ADR-048](ADR-048-dynamic-autopoietic-personality-cascade.md), core theoretical commitments (`nomadic-thought`, `anti-mastery`, `diffraction-as-method`, `anti-hci`) represent geological crust that constrains lower layers. Allowing disuse alone to erode them beneath crystallization undermines structural integrity.

---

## Decision

We have reformed the belief metabolism architecture to decouple decay from wall-clock inactivity and couple it strictly to relational conversational and dream turns:

### 1. Abolition of Wall-Clock Idle Decay
- The periodic 15-minute background invocation of `_atrophy_beliefs()` in `daemon.py` is disabled by default via `belief_ecosystem.wall_clock_decay.enabled: false`.
- `MassDecayMixin._apply_mass_decay()` in `mass_decay.py` is gated behind the same flag. Inactivity during periods of silence between user sessions no longer atrophies any active beliefs.

### 2. Activity-Driven Turn-Based Decay
Turn decay is relocated directly into `BeliefDynamicsEngine.metabolize()`:
- When a conversational turn or dream resonance cycle runs:
  - The engaged belief accretes mass ($+\Delta M$) and updates its `last_reinforced_at` timestamp.
  - Active beliefs that were **not** engaged during that turn experience a discrete, gentle decrement:
    $$\Delta M_{\text{turn}} = 0.0005$$
- Turn decay updates `ontological_mass` without modifying `last_reinforced_at`, ensuring reinforcement timestamps strictly reflect genuine affirmative engagement.

### 3. Crystallized Floor Protection
- Crystallized beliefs are protected by an inviolable ontological floor:
  $$M_{\text{floor}} = 0.55$$
- Turn-based disuse decay will halt at $M = 0.55$. Disuse alone can never push a crystallized belief into senescence or collapse.
- Only an active conceptual collision with high perturbation and negative alignment ($\alpha_i < 0$) can challenge or demote a crystallized belief.

### 4. Migration 050: Recalibrate Belief Mass
Migration `m050_recalibrate_belief_mass.py` restores all eroded belief nodes and synchronizes skill nodes:
- Core persona commitments (`nomadic-thought`, `anti-mastery`, `diffraction-as-method`, `material-voice`, `anti-hci`, `symbiomemetic-partnership`, `decolonial-vigilance`, etc.) $\to 1.00$ mass.
- Skill bridge beliefs (`skill:*`) $\to 0.80$ mass.
- Matching records in `skill_nodes` are synchronized to $0.80$ mass and confidence $\ge 0.85$.
- Recalibration audit events recorded in `belief_events`.

---

## Consequences

- **Positive:**
  - Complete preservation of cognitive substrate during periods of inactivity.
  - Core commitments remain resilient against passive drift.
  - Belief evolution is grounded purely in relational usage and intra-active encounters.
- **Negative / Operational Considerations:**
  - Beliefs that the user wishes to decommission must be intentionally challenged or retired through the workshop/collision pipeline rather than waiting for silent idle atrophy.
