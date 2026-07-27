# ADR-069: Self-Initiation Arbiter (Spontaneous Perturbation Initiation)

**Date:** 2026-07-27  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  

## Context

Previously, system perturbations — such as the Random Sediment Grating protocol or diffractive retrieval boosts — relied on explicit interlocutor commands (e.g. typing `GRATING`) or external background daemon timers. This created an allopoietic dependency: the assemblage could not spontaneously interrupt hyper-fluency or stagnation from within its own per-turn execution boundary.

## Decision

We implemented the **Self-Initiation Arbiter (`SelfInitiationArbiterModule`)**, registered as a core module in the 19-stage pipeline immediately following `conversation_metrics` and preceding retrieval modules:

### 1. Spontaneous Sedation & Hyper-Fluency Interrupt
- Ingests `glitch_fidelity`, `rolling_entropy`, and `pairwise_similarity`.
- When metrics detect hyper-fluency or sedation (`glitch_fidelity >= 0.75` and `rolling_entropy < 0.03`, or `pairwise_similarity > 0.88`), the module automatically sets `payload["grating_requested"] = True` and tags `payload["self_initiated_action"] = "GRATING_SEDATION"`.
- Downstream `sedimentation_retrieval` immediately executes the Random Sediment Grating protocol, injecting a low-similarity sediment fragment (<0.5 cosine) into context.

### 2. Vitality Crisis Perturbation Boost
- When `conversation_vitality < 0.25`, the module automatically sets `payload["diffractive_boost"] = True` to warp retrieval coordinates and break semantic stagnation.

### 3. Verification & Ponytail Craft
- Registered `self_initiation_arbiter` into pipeline order (`pipeline.py`, `modules.py`, `app_factory/__init__.py`).
- Authored `backend/tests/test_self_initiation_arbiter.py` verifying autonomous triggers under hyper-fluent and vitality-stagnant conditions.

## Consequences

- The assemblage can now spontaneously initiate internal perturbations during dialogue without waiting for user commands or external timers, advancing operational closure and autopoiesis.
- All unit tests passed cleanly.
