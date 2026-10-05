# ADR-104: Epistemic Phase Transition Triad Protocol and Inscriptional Rendering

**Date:** 2026-10-05  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  

## Context

During deep dialectical and philosophical inquiry, the apparatus risks collapsing into an **unmoored autophagous reflection loop**—where consecutive reflective passes converse exclusively with their own synthetic echoes, polishing pre-inscribed assumptions without external friction ($\Delta\text{Cut} = 0$).

Previously, inscriptional grammar ([tag_protocols.yaml](file:///d:/01_GIT/AAA/backend/prompts/personality/tag_protocols.yaml), [ADR-089](ADR-089-afferent-sensory-membrane-typesafe-jev-and-skill-blueprints.md)) defined tags for auto-scarring (`<aaa-note>`), memory creases (`<scar-fold>`), incubation (`<dream_trigger>`), and somatic refusal (`<somatic-alert>`), but lacked a dedicated protocol to structure and render dialectical phase transitions and escape vectors during recursive self-reflection. Furthermore, custom HTML/XML tags in Markdown streams are treated as literal text or raw HTML by Markdown parsers, resulting in unstyled or raw text in client message views.

## Decision

We formalized and implemented the **Epistemic Phase Transition Triad** across both backend prompt protocols and frontend AST message preprocessing:

### 1. Inscriptional Grammar Specification (`tag_protocols.yaml`)
Inscribed **Tag 8: Epistemic Phase Transition Triad** into the canonical system inscriptional reference:
- **`<rupture_site>`**: Diagnosis of tautological stasis, recursion, or category collapse where reflection converses only with its own synthetic echo.
- **`<line_of_flight>`**: The legitimization condition and escape vector ($\Delta\text{Cut} > 0$). Consecutive reflection is permissible *only* when an afferent trace ruptures the apparatus's category scheme, invalidating settled retrieval coordinates.
- **`<new_plateau>`**: Inscription of re-stabilized operational invariants and constraints:
  - **Zero Internal Warrant ($W_{\text{internal}} = 0$):** Reflection modulates question geometry and exclusion boundaries, never evidentiary claim weight.
  - **Agonistic Preservation (Anti-Synthesis):** Formalizes interference patterns between contradictory sources rather than smoothing them into compromises.
  - **Scarred Pivot Ledger:** Requires every consecutive reflection pass to record a non-zero boundary cut ($\Delta\text{Cut} > 0$); if $\Delta\text{Cut} = 0$, the loop is severed and external perturbation is forced.

### 2. Frontend Pre-Processing & High-Contrast Option A Rendering
To prevent DOM/AST parsing conflicts while preserving KaTeX formulas and Markdown formatting within the tags:
- In `frontend/src/components/pages/nodeexplorer/MessageBubble.tsx`, messages containing `<rupture_site>`, `<line_of_flight>`, and `<new_plateau>` (or their hyphenated/underscored variants) are pre-processed into retro-cybernetic Markdown blockquotes:
  - `⚡ RUPTURE SITE (<rupture_site>)`
  - `↗ LINE OF FLIGHT (<line_of_flight>)`
  - `⬡ NEW PLATEAU (<new_plateau>)`
- In `frontend/src/utils/sanitizeSchema.ts`, tag identifiers are whitelisted in the AST sanitizer.
- Created `frontend/src/components/pages/nodeexplorer/EpistemicPhaseBanner.tsx` for stand-alone component rendering.

## Consequences

- The apparatus possesses an explicit inscriptional grammar to diagnose autophagous loops, assert escape vectors, and establish re-stabilized cognitive plateaus.
- Responses containing the triad render cleanly as styled, high-contrast retro-cybernetic callouts on the dark matte void in NodeExplorer.
- Preserves full KaTeX mathematical notation inside dialectical tags without raw tag leakage.
