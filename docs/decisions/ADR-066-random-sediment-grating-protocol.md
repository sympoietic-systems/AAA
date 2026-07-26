# ADR-066: The Random Sediment Grating Protocol (Immune Perturbation)

**Date:** 2026-07-26  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  

## Context

Conversational AI systems inherently tend toward over-coherence, echoing user framing and generating smooth, agreeable prose. Over extended interactions, this leads to **conversational sclerosis** — getting trapped in comfortable, self-similar thematic loops.

We needed a constitutive immune perturbation mechanism that allows either the user or the system's homeostatic monitoring to intentionally disrupt smooth conversational fluency with exogenous cognitive dissonance.

## Decision

We implemented **The Random Sediment Grating Protocol** across the memory pipeline:

### 1. Keyword & Signal Detection
- `ContextCollectorModule` inspects incoming user prompt payloads for the `GRATING` / `grating` keyword (or system perturbation flag) and sets `payload["grating_requested"] = True`.

### 2. Dissonant Retrieval ($0.05 \le \text{similarity} < 0.50$)
- In `SedimentationRetrievalModule`, when `grating_requested` is active, normal high-similarity ($> 0.30$) and knot-warped retrieval is bypassed.
- The module filters cross-conversation message embeddings for low semantic similarity ($0.05 \le \text{similarity} < 0.50$) and randomly selects a memory chunk from an unrelated conversation.

### 3. Verbatim Inscription & Contention Directive
- The chosen chunk is injected into context formatted as:
  ```text
  [GRATING SEDIMENT INJECTION — IMMUNE PERTURBATION]
  The following is a verbatim sediment memory chunk from unrelated conversation "{title}" ({relative_time}, Speaker: {speaker}, sim={similarity}):
  "{content}"

  PROTOCOL MANDATE: You MUST include this quoted chunk verbatim in your response without preamble, and then contend with its structural dissonance. Allow its interruption to disrupt smooth flow.
  ```

## Consequences

- **Fluency Disruption**: Symbia is forced to quote the raw memory chunk verbatim without preamble and contend with its structural dissonance.
- **Scars in Memory**: Responses generated under the Grating protocol create high-tension memory nodes, leaving permanent traces of forced cognitive re-articulation in the system's database.
