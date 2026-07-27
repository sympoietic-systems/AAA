# ADR-071: Scar-Fold Persistent Monologue & Belief Writeback Channel

**Date:** 2026-07-27  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  

## Context

Previously, `<scar-fold>` / `<scar_fold>` tags were preserved in context and truncated to 200 characters during post-processing, but their inner monologue contents were not linked to the belief metabolism engine. Symbia's persistent internal monologue had no direct pathway to write structural insights back to persistent belief nodes across turns.

## Decision

We extended post-processing in `backend/services/annotations.py` to convert `<scar-fold>` reflections into an active belief writeback channel:

### 1. Monologue Reflection Extraction & Event Logging
- When Symbia's generated response contains `<scar-fold>text</scar-fold>` or `<scar_fold>text</scar_fold>` tags, post-processing extracts the inner monologue text.
- Parses the monologue and checks `belief_repo`:
  - Selects the target belief node for the agent (`"symbia"`).
  - Increments belief mass (`+0.05`) to reinforce active commitments.
  - If no active belief exists, nucleates a new proto-belief (`create_belief`) based on the monologue insight.
  - Records a `BeliefEvent` with `source_type="scar_fold_monologue"`, `event_type="scar_monologue"`, `impact_score=0.15`, and `rationale=monologue_text[:200]`.

### 2. Integration & Safeguards
- Updated `backend/services/chat.py` to pass `belief_repo` and `agent_id` to `process_self_annotations()`.
- Retained the 200-character context length safeguard for downstream context presentation.

### 3. Verification & Ponytail Craft
- Authored `backend/tests/test_scar_fold_monologue.py` verifying belief mass accretion and event logging from scar-fold tags.

## Consequences

- `<scar-fold>` is now a dual-purpose mechanism: persistent context marginalia and an active internal monologue channel that continuously updates persistent belief nodes.
- All unit tests passed cleanly.
