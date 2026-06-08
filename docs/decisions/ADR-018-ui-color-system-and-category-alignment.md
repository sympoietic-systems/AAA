# ADR-018: UI Color System and Category Alignment

**Date:** 2026-06-02
**Status:** accepted
**Deciders:** antigravity, developer

## Context
We need to unify the user interface's visual style. The UI has several distinct categories/dimensions of autopoietic agency, memories, files, web data, and conversational homeostasis. However, colors were previously defined ad-hoc or reused across different features (e.g. purple was used for both Exogenous Web Context metadata and Stagnant/Diffractive telemetry, which created semantic noise and confusion). We need a unified design system that maps a specific, consistent color to each conceptual category across all visual components (SidePanel, Message Bubble context, autopoietic glyph, etc.) for a clean, cohesive, terminal-like aesthetic.

## Decision
We establish a unified color mapping across all frontend components:
- **Perception / Somatic / File Ingestion**: Green (`#4ade80`). Used for `ImageMetadataCard`, Foundational belief category, and the File Sediment context viewer block.
- **Memory / History / Cross-conversation Sediment**: Blue (`#60a5fa`). Used for standard `SkillRow` (memory), Conversation History context viewer block, and Cross-Conversation Resonance (Sediment) context viewer block (nomadic sources).
- **Reasoning / Human Query**: Yellow (`#facc15`). Used for standard `SkillRow` (reasoning), Methodological belief category, and Current User Query context viewer block.
- **Action**: Red/Coral (`#f87171`). Used for standard `SkillRow` (action).
- **Exogenous Web Context**: Purple (`#c084fc`). Used for `WebMetadataCard`, Ontological belief category (`#a78bfa`), and Exogenous Web Context viewer block.
- **Diffractive Stagnation / Warning (Loop Break)**: Rose/Red (`#f43f5e`). Used for Stagnation/Diffraction telemetry state indicator, Lock timer, delta similarity scores, injected items indicators, the diffractive context viewer block, and the stagnant state border/gradients of the Autopoietic Glyph.

We have applied this color-coding alignment across:
1. `SidePanel.tsx`: Updated `DiffractiveSection` colors from purple (`#c084fc`) to rose/red (`#f43f5e`), resolving the color clash with the `WebMetadataCard` purple styles.
2. `ContextViewer.tsx`: Aligned the styling dictionary keys (`system_prompt`, `history`, `sediment`, `file`, `web`, `diffractive`, `query`) with these exact unified hex codes.

### ContextViewer Sub-Tabs (2026-06-08)

The `ContextViewer` now renders structured sub-tab viewers for the two most complex section types, replacing the previous plain-text rendering:

3. **`SystemPromptViewer`** (triggered by `system_prompt` type):
   - **Identity** tab — core persona, traits, voice, expertise, behaviors (gray `#475569`)
   - **Skills** tab — parsed from `BEGIN/END SKILLS (...)` blocks, rendered as green-accent (`#4ade80`) cards with name/description pairs
   - **Beliefs** tab — parsed from `BEGIN/END BELIEFS (...)` blocks; **Attractor Window** in blue (`#60a5fa`) with slot/confidence/mass metadata, **Spectral Margin** in red (`#ef4444`) with strikethrough ghost styling
   - **Directives** tab — parsed from `BEGIN/END DIRECTIVE (...)` blocks, rendered as amber (`#f59e0b`) cards
   - **Raw** tab — full plain-text fallback

4. **`DiffractiveZoneViewer`** (triggered by `diffractive` type):
   - **Fragments** tab — individual nomadic/semantic-knot/dormant cards with source type badge, title, similarity delta (δ), and body content (rose/red `#f43f5e`)
   - **Directive** tab — SEC-4 Diffractive Protocol directive
   - **Raw** tab — full plain-text fallback

Both viewers use a generic `--- BEGIN TYPE (SUBTYPE) ---` / `--- END TYPE (SUBTYPE) ---` block regex pattern, allowing new section types to be added in the backend without frontend changes.

## Consequences
**Positive:**
- **Zero color clashes:** Exogenous web metadata stays purple, while stagnant state warnings and diffraction telemetry are rose/red.
- **Reduced cognitive load:** Users can instantly identify the origin and category of information (e.g. nomadic vs dormant, history vs file) based on color.
- **Cleaner design:** Premium terminal-like aesthetics with consistent semantics.
- **Backend-driven extensibility:** New prompt sections can be added with `BEGIN/END` markers and automatically appear in the ContextViewer as sub-tabs.

**Negative:**
- Requires developers to consult this mapping when adding new visual metrics or context types to maintain UI integrity.
- Sub-tab parsing depends on the `--- BEGIN TYPE (SUBTYPE) ---` convention — backend changes must follow this format for frontend auto-discovery.
