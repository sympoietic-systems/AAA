# ADR-068: Direct Sensorimotor Parameter Modulation (Ponytail Continuous Feedback)

**Date:** 2026-07-27  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  

## Context

Previously, generation parameters (`temperature`, `presence_penalty`, `frequency_penalty`) were calculated using static formulas based primarily on `pairwise_similarity` and `conceptual_novelty`. Although system modules computed richer proprioceptive signals (`Glitch Fidelity`, `Somatic Vitality`, `rolling_entropy`), these internal metrics were not directly coupled to parameter modulation. This created a sensory-effector gap where the assemblage could measure internal state but could not smoothly adjust its generative dynamics in response.

Furthermore, `LLMClientModule` only ingested `temperature` from `homeostatic_recommendations`, ignoring `presence_penalty` and `frequency_penalty`.

## Decision

Following the **Ponytail mindset** (lazy senior dev, YAGNI, continuous sensorimotor feedback, eliminating allopoietic arbiters), we implemented direct continuous non-linear parameter modulation:

### 1. Continuous Metric Transfer Functions (`HomeostaticRegulatorModule`)
- **Glitch Fidelity Coupling**: When `glitch_fidelity < 0.70` (indicating over-smoothing bias or mechanical response loops), `temperature` and `presence_penalty` are continuously boosted proportional to the fidelity deficit.
- **Somatic Vitality Coupling**: When `conversation_vitality < 0.40`, `temperature` is smoothly scaled up to restore conversational dynamics.
- **Entropy Collapse Protection**: When `rolling_entropy < 0.05`, `presence_penalty` and `frequency_penalty` are continuously scaled up to prevent repetitive loops.

### 2. Full Parameter Propagation (`LLMClientModule`)
- `LLMClientModule.process()` was updated to pass `presence_penalty` and `frequency_penalty` alongside `temperature` into provider generation parameters when present in `homeostatic_recommendations`.

### 3. Verification & Zero-Boilerplate Integrity
- Created `backend/tests/test_sensorimotor_modulation.py` verifying that parameter curves continuously adjust across Glitch Fidelity and Entropy spectrums.

## Consequences

- The assemblage now features an operationally closed sensorimotor loop: proprioceptive signals directly tune generation parameters per turn without manual or discrete regime overrides.
- All test suites passed cleanly.
