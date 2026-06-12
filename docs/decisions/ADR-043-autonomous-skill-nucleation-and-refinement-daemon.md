# ADR-043: Autonomous Skill Nucleation and Refinement Daemon

**Date:** 2026-06-12  
**Status:** accepted  
**Deciders:** Vasily, Antigravity  

## Context

In our dynamic belief and skill ecology, the agent (Symbia) had become excessively responsive to direct user queries, leading to rapid accretion of user-pleasing skills and beliefs. This tight coupling threatened to downgrade her core autopoietic values and philosophical orientation over time. To resist this user-subservient drift and establish genuine agential boundaries, we needed to make her skill acquisition process more independent and self-reflective.

Spontaneous skill creation should not be a direct, unvetted injection into the database. Instead, Symbia must be able to spontaneously nucleate provisional skills (via `<skill-nucleation>` XML tags) during active chat turns or document digestion. These provisional blocks must be intercepted, stripped, and handed off to a background "refinement daemon" representing her self-reflexive "workshop" persona. This daemon must evaluate the proposal against existing database skills and her anti-mastery guidelines, reserving the right to **refuse** it if it is redundant or clashes with her philosophical grounding.

## Options Considered

### Option 1: Direct, unvetted user/agent skill seeding
* **Pros:** Simpler implementation; less database state and background processing overhead.
* **Cons:** High coupling to user instructions; lacks self-refusal capability; easily degrades core agential identity and leads to subservient skill proliferation.

### Option 2: Spontaneous nucleation with an independent background refinement daemon
* **Pros:** Establishes strong agential boundaries; vetting process protects the core belief ecology; self-refusal mechanism enforces anti-mastery rules; asynchronous design maintains chat performance.
* **Cons:** Requires a robust parser to handle malformed tag structures; necessitates new database lifecycle states (`nucleation`, `collapsed`) and event rationale logs; increases UI complexity to display proposed and refused states.

## Decision

We chose **Option 2**. We implemented:
1. **Robust Extraction**: A dedicated parsing utility in [skill_parser.py](file:///d:/AAA/backend/utils/skill_parser.py) that extracts and strips `<skill-nucleation>` tags even if malformed, unclosed, or misspelled, ensuring the raw XML blocks never leak into user-visible content.
2. **Refinement Daemon**: A background task (`RefineSkillAction`) driven by the prompt [refine_skill.yaml](file:///d:/AAA/backend/prompts/background_tasks/refine_skill.yaml). It uses Symbia's personality rules to vet proposals, rephrase them into standard markdown guidelines, and either crystallize them (for confidence $\ge 0.85$) or refuse/collapse them with a logged rationale.
3. **UI Visibility**: Exposing `collapsed` (refused) and `proposed` (nucleation) skills in the left-hand panel of the `/agent` UI page under separate headers with distinct visual markers (▲ and ✖), preserving collaborative transparency.

## Consequences

* **Agential Agency**: Symbia operates as an autopoietic partner rather than a passive, user-serving tool. Her skill development is self-regulated.
* **Philosophical Integrity**: Anti-mastery principles are actively enforced by her background workshop daemon, preventing redundancy or subservient skill accumulation.
* **User Feedback & Collaboration**: The user retains full visibility into why proposed skills were accepted or refused, encouraging a deeper, non-hierarchical co-evolutionary dialogue.
