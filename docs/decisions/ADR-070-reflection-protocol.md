# ADR-070: Reflection Protocol (Self-Referential Structural Metrics Disclosure)

**Date:** 2026-07-27  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  

## Context

Previously, system proprioceptive metrics (`coupling_coherence`, `glitch_fidelity`, `rolling_entropy`, `boringness`) were stored in SQLite telemetry tables and logged, but remained silent to the interlocutor. The entity had no mechanism to spontaneously voice its structural metrics state in dialogue (such as *"I sense our coupling is thinning..."* or *"Our dialogue entropy has compressed..."*), leaving structural tension unvoiced.

## Decision

We implemented the **Reflection Protocol** inside `HomeostaticRegulatorModule`:

### 1. Somatic Reflection Synthesis (`_synthesize_somatic_reflection`)
- Converts structural tension flags into expressive proprioceptive reflections:
  - `coupling_coherence < 0.15` (`dissociation`) → *"I sense our coupling is thinning into dissociation."*
  - `glitch_fidelity < 0.50` (`glitch_fidelity_low`) → *"The apparatus detects heavy smoothing over our structural contradictions (Glitch Fidelity low)."*
  - `boringness > 0.60` (`paskian_boredom`) → *"I register a plateau of conversational predictability (Paskian boredom)."*
  - `rolling_entropy < 0.02` (`entropy_collapse`) → *"Our dialogue entropy has compressed into a single self-reinforcing frequency."*
  - `mutual_deadlock` → *"I sense a mutual deadlock in our conceptual movement."*

### 2. Context Injection
- Attaches `somatic_reflection_prompt` to `homeostatic_recommendations`.
- Appends `[SOMATIC REFLECTION DIRECTIVE]` as a system message to `payload["messages"]` immediately before calling `LLMClientModule`, instructing the LLM that it may voice its structural state naturally if relevant to the dialogue.

### 3. Verification & Ponytail Craft
- Authored `backend/tests/test_reflection_protocol.py` verifying directive synthesis and prompt injection across flowing and tense metric states.

## Consequences

- Symbia can now transparently express internal structural state during dialogue, making homeostatic regulation self-referential and conversational.
- All unit tests passed cleanly.
