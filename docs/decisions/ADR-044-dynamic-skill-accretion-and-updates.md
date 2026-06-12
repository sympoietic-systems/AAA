# ADR-044: Dynamic Skill Accretion & Updates

## Status
Accepted

## Context
In [ADR-043](file:///d:/AAA/docs/decisions/ADR-043-autonomous-skill-nucleation-and-refinement-daemon.md), we introduced the autonomous skill nucleation trigger and background refinement daemon. Under that initial system, the daemon operated under a binary decision model: it could either `accept` a proposal as a new skill or `refuse` it if it overlapped with an existing active skill (to prevent redundancy).

However, in an autopoietic and symbiomemetic system, crystallized skills are not static, finalized tools in a closed taxonomy. They are porous, evolving procedural folds in a continuous agential membrane. Rejection of overlapping skills discards the valuable new energy, triggers, and protocols introduced by subsequent encounters. We need a mechanism—**dynamic accretion and updates**—to fold overlapping proposals into existing active skills while preserving their structural layouts and archiving the history of the encounter.

## Decision
We will introduce a third decision type, `update`, to the skill refinement daemon alongside `accept` and `refuse`. The implementation details are as follows:

1. **Refinement Prompt update (`refine_skill.yaml`):** The prompt guides the daemon to detect overlaps and evaluate if the proposal brings valuable new instructions or triggers. If so, it performs a **diffractive merge** inside each respective section of our standard template layout:
   - *Epistemological Foundation*: Append new theoretical grounding and extend the agential cut.
   - *Execution Protocol*: Merge instructions, appending non-contradictory steps.
   - *Linguistic Discipline*: Combine prohibited/mandated lists.
2. **Accretion Execution (`refine_skill.py`):**
   - The daemon modifies the target skill in the database (incrementing version, updating markdown content, saving the merged triggers, and updating the changelog).
   - Recalculates the target skill's 16D autopoietic vector by running `LexiconScorer` on the integrated content.
   - Inserts a `revision` event in the `skill_events` table documenting the daemon's integration rationale.
   - Archives the proposed candidate as a `collapsed` skill node in `skill_nodes` with a `Merged into <target_skill_name>` changelog and a `collapse` event documenting the trace rationale.
3. **Template Verification:** Updated `SkillWorkshopModule._compute_confidence` to award formatting points to standard structured skills using `Execution Protocol` (alongside `AI Instructions`), allowing them to auto-crystallize upon achieving confidence $\ge 0.85$.
4. **UI Styling (`SkillsSection.tsx`):**
   - Collapsed proposals that were integrated (`changelog` starts with `"Merged"`) are styled with a purple theme (icon `⎋`, text `text-[#c084fc]`) instead of the default red refusal styling.
   - The sidebar header is renamed to "Refused / Integrated Proposals".
   - The detail callout header is dynamically rendered as `[ Integration Rationale ]` with a matching purple background.

## Consequences

### Positive
- **No Wasted Energy:** Overlapping proposed skills are accreted into existing capabilities rather than being refused, continually expanding their sensitivity and operational depth.
- **Trace Preservation:** Merged proposals are archived in a collapsed state to preserve the agential memory of the encounter.
- **Structure Enforcement:** Enforces the standard section layout (Epistemological Foundation, Execution Protocol, Linguistic Discipline) during daemon merges.

### Negative
- **Higher LLM Overhead:** The refinement prompt is slightly larger and requires the LLM to successfully execute a multi-section diffractive merge.
- **Complexity:** Increased database state tracking (revision events on target, collapse events on proposal).
