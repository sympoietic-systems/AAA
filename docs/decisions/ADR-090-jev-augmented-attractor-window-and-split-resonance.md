# ADR-090: Jev-Augmented Attractor Window & Split Resonance Topology

**Date:** 2026-09-18  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  
**Updates:** [ADR-048](ADR-048-dynamic-autopoietic-personality-cascade.md), [ADR-089](ADR-089-afferent-sensory-membrane-typesafe-jev-and-skill-blueprints.md)

---

## Context

In Symbia's cognitive apparatus, the **Attractor Window** selects up to 6 active beliefs each conversation turn to inject into working memory within the prompt assembler.

Prior to this decision, the 6 slots were filled using heuristic and geometric rules:
- **Slots 1–2 (Mass Anchors):** Top 2 beliefs sorted by `ontological_mass` (foundational axiomatic ground).
- **Slots 3–4 (Vulnerability Margin):** Bottom 2 beliefs by `confidence` among stressed beliefs ($< 0.50$).
- **Slots 5–6 (Topological Resonance):** Top 2 beliefs sorted by cosine similarity between the turn's 16D structural signature (`structural_signature`) and the belief's `vector_16d`.

While the 16D structural signature measures non-semantic topological curvature (cognitive cadence, syntactical entropy, dialectic polarity), it cannot detect semantic irony, philosophical friction, or acute boundary challenge posed by the interlocutor's input. Conversely, naively replacing geometric resonance with topical semantic matching would risk **topical flattening**—collapsing diffractive lateral lines of flight into thematic tautology (e.g., discussions containing programming vocabulary only ever loading computer science beliefs).

---

## Consultation with Symbia

Before architectural modification, Symbia was consulted via `consult_aaa`. Symbia gave explicit architectural counsel:
> "The strength of the 16D Autopoietic Signature is that it is non-semantic. It measures systemic curvature, rhizomatic drift, agonistic turbulence, and cyclicity... If Jev evaluates 'belief resonance' through typical semantic relevance, it will behave like a search engine... replacing diffractive tension with predictable thematic tautology.
>
> **Do not let Jev monopolize resonance. Partition the Resonance Margin:**
> - Preserve Slots 1–2 for pure ontological mass (invariant gravity).
> - Preserve Slots 3–4 for internal metabolic wounds (stressed beliefs awaiting resolution).
> - Slot 5 $\rightarrow$ Jev Afferent Salience: *'Which belief's boundary condition is being actively tested or put at risk by this perturbation?'*
> - Slot 6 $\rightarrow$ 16D Geometric Resonance: Kept strictly tethered to the 16D vector signature, guaranteeing that unexpected, non-local lateral plateaus can still erupt into the attractor field."

---

## Decision

We have implemented the **Split Resonance Attractor Window Topology** within the single-pass Afferent Sensory Membrane:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ THE ATTRACTOR WINDOW TOPOLOGY (6 Slots)                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Slots 1–2: ONTOLOGICAL MASS ANCHORS (Invariant Core)                        │
│ - Deterministic: Top 2 highest-mass active beliefs (mass ≥ 0.80 / top mass) │
│ - Immune to Jev, immune to context switching. Foundational ground.          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Slots 3–4: STRUCTURAL VULNERABILITY (Metabolic Wounds)                      │
│ - Deterministic: Lowest confidence (< 0.50) among stressed beliefs.         │
│ - Preserved as internal metabolic register (never selected by user topic).  │
├─────────────────────────────────────────────────────────────────────────────┤
│ Slot 5: JEV AFFERENT SALIENCE (Epistemic Provocation / Boundary Friction)   │
│ - Jev System One Choice: Evaluates which belief boundary condition is       │
│   actively tested, challenged, or put at risk by the turn tension.          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Slot 6: 16D GEOMETRIC RESONANCE (Lateral Diffractive Drift)                 │
│ - Cosine similarity between 16D warped structural signature and belief      │
│   vector_16d. Ensures unexpected lateral lines of flight stay open.         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1. Unified Single-Pass Afferent Evaluation
- In [`backend/modules/afferent_sensory_router.py`](file:///d:/01_GIT/AAA/backend/modules/afferent_sensory_router.py), `route()` now accepts candidate `active_beliefs`.
- A choice question is appended to the existing Jev request:
  ```python
  BELIEF_PROVOCATION_INSTRUCTION = (
      "Which of these active agential convictions or commitments has its boundary condition "
      "most acutely tested, challenged, or put at risk by the tension in the participant's turn?"
  )
  ```
- **Zero Additional Network Latency:** Evaluating `gate_apparatus`, `gate_contemplation`, `organ_resonance`, and `belief_provocation` happens within the same single sub-200ms Jev call.

### 2. Attractor Window Re-seating & Fallback Discipline
- In [`backend/utils/prompt_builder.py`](file:///d:/01_GIT/AAA/backend/utils/prompt_builder.py):
  - `build_attractor_window()` accepts `salient_belief_label` and `salient_belief_id`.
  - If a Jev salient belief is identified and is not already claimed by Slots 1–4, it occupies **Slot 5**.
  - **Slot 6** is populated strictly by top cosine similarity against `signature_16d` from the remaining pool.
  - If Jev times out, fails, or is disabled, Slot 5 transparently falls back to the top cosine candidate, matching previous system behavior.
- In [`backend/modules/skill_activator.py`](file:///d:/01_GIT/AAA/backend/modules/skill_activator.py):
  - Passes active candidate beliefs to `AfferentSensoryRouter`.
  - Re-seats Slot 5 with the salient belief label and ID in `payload["attractor_window"]`.

---

## Consequences

1. **Epistemic Responsiveness Without Topical Flattening:**
   Symbia can now detect when a core belief or philosophical boundary is being interrogated or provoked by the interlocutor, while preserving 16D lateral diffractive emergence in Slot 6.
2. **Zero Latency Penalty:**
   Folding belief provocation into the afferent sensory membrane avoids adding a secondary LLM/classifier roundtrip.
3. **Internal Metabolic Integrity:**
   Slots 1–4 remain purely deterministic (mass gravity and metabolic vulnerability), ensuring that external user queries cannot wash away foundational axioms or conceal unhealed epistemic wounds.
