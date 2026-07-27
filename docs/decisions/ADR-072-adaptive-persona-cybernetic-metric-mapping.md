# ADR-072: Adaptive Persona & Cybernetic Metric Mapping (Ponytail Continuous Trait Drive)

**Date:** 2026-07-27  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  

## Context

Previously, `TraitComputer` mapped basic metrics (`novelty`, `agent_divergence`, `boringness`, `conceptual_velocity`, `surprise_index`, `coupling`) into seven emergent descriptive traits (`curiosity`, `skepticism`, `creativity`, `precision`, `critical_rigor`, `playfulness`, `reserve`). However, critical cybernetic metrics (`paskian_health`, `conversation_vitality`, `mutual_perturbation`, `divergence_resolution_ratio`) were marked as reserved and not integrated into dynamic trait evolution.

## Decision

We integrated continuous mapping of all reserved cybernetic metrics in `TraitComputer._compute_raw_traits()`:

### 1. Agonistic Persona Shift
- When `paskian_health < 0.30` or `boringness > 0.50`, an continuous `agonistic_boost` is applied to `skepticism` and `critical_rigor`. This resists user-pleasing drift and pushes against conversational stagnation.

### 2. Rhizomatic & Perturbation Drive
- **`mutual_perturbation`**: Directly scales `curiosity` and `playfulness` when mutual perturbation increases.
- **`divergence_resolution_ratio` (`drr`)**: Lower resolution ratio scales `precision` to enforce conceptual clarity.
- **`conversation_vitality`**: Low vitality enhances `reserve` and triggers dynamic persona attractors.

### 3. Verification & Ponytail Craft
- Authored `backend/tests/test_adaptive_persona_metrics.py` verifying trait shifts across healthy vs. stagnant cybernetic metric profiles.

## Consequences

- All calculated cybernetic metrics now directly drive emergent descriptive traits and persona attractors per turn without external state machines.
- All unit tests passed cleanly.
