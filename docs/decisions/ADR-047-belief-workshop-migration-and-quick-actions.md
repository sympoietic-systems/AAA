# ADR-047: Belief Workshop Migration & Quick Actions

## Status
Accepted

## Context
Following the implementation of the Belief Workshop (ADR-046), we needed to transition legacy data (inactive "spectral ghosts" and "proto-beliefs") from `belief_nodes` into the new `belief_proposals` table to let Symbia's vetting workshop process them. 

However, doing a static SQL insert would bypass the autonomous refinement pipeline, meaning proposals would lack suggested statements, kebab-case labels, semantic similarity target nominations, and Symbia's cognitive reflections. To solve this, we needed to simulate the dynamic injection of all legacy assets through the real background refinement pipeline.

During execution, two key issues were identified:
1. **Background Action Dispatch Bug**: The `refine_proposal_sync` method in `BeliefService` attempted to call `.dispatch` and `.wait_for_task` on `BackgroundTaskEngine`, which was invalid as it only supports the `.run` interface.
2. **Missing Reflection Storage**: The `RefineBeliefAction` successfully processed proposals via LLM calls but failed to write the generated `rationale` back into the database's `symbia_reflection` column, leaving the reflection text blank in the UI.
3. **UX Friction**: Selecting targets, writing rejection rationales, and scrolling back and forth between the reflection text box and the Vetting actions area introduced unnecessary mechanical scrolling.

## Decision

We have implemented the following solutions:

### 1. Backend Pipeline & Migration Script
* **Fixed Service-Engine Integration**: Updated `BeliefService.refine_proposal_sync` to call `bg_engine.run("refine_belief", ...)` instead of `dispatch`.
* **Populated Reflections**: Modified `RefineBeliefAction.execute` to write the generated LLM rationale directly to the `symbia_reflection` column via `belief_repo.update_proposal_symbia_reflection`.
* **Legacy Injection Script**: Created `backend/scripts/simulate_legacy_injection.py` to:
  1. Cache all 42 legacy proposal entries.
  2. Clear the `belief_proposals` table.
  3. Re-inject them sequentially through `belief_metabolism._nucleate_proto_belief` to initialize them as pending proposals.
  4. Trigger the full `refine_proposal_sync` refinement task on each node, generating suggestions, merge targets, and Symbia reflections.

### 2. Frontend Quick Vetting Action Buttons
Updated `frontend/src/components/pages/agentpage/beliefs/BeliefDetail.tsx` to dynamically render direct quick-action buttons below Symbia's Reflection box:
* **Merge Option**: If `potential_merge_target` is present, it displays `[ Merge into: "target-label" ]` which auto-selects the nominated target and activates the merge form.
* **Adopt Option**: If no merge target is nominated, it displays `[ Adopt as: "suggested-label" ]` which pre-fills the suggested statement and label inputs.
* **Reject Option**: Renders `[ Reject ]` (or `[ Reject Proposal (Symbia Recommended) ]` if the reflection recommends rejection). Clicking it pre-fills the rejection rationale box with Symbia's reflection.
* **Auto-Scroll Focus**: Binds a React `useRef` to the Vetting form container. Activating any quick-action button automatically smooth-scrolls the workshop form directly into view.

### 3. Synthesized Merge Statements
* **Editable Synthesis**: When merging, the UI displays a text area initialized with the target belief's statement. The collaborator can edit/synthesize the wording to merge the proposal's specific nuances.
* **Versioned Tracking**: If the statement is updated, the backend scores the new text to compute a new 16D signature, bumps the target belief's version, and logs a historical statement version. If unchanged, the system updates only the mass and confidence.

## Consequences

### Positive
* **Operationalized Workshop**: Legacy proto-beliefs and spectral ghosts have successfully run through the real background pipeline, enabling Symbia's vetting dashboard.
* **Complete Metadata**: All 42 proposals now have high-quality kebab-case labels, refined statements, reflections, and mathematical similarity links.
* **Reduced UX Friction**: Users can accept, merge, or reject proposals with a single click, without manually searching through long select lists or typing out rationales.
* **True Semantic Synthesis**: Merging is no longer a purely mathematical accretion of mass; it allows for actual diffractive refinement of the belief's text with versioned tracking.

### Negative
* **One-Time Migration Cost**: Running LLM cycles on all 42 proposals took approximately 4 minutes of API execution.
