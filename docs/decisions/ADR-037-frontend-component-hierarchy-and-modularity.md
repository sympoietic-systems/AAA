# ADR-037: Frontend Component Hierarchy and Modularity Refactoring

## Status
Accepted

## Date
2026-06-11

## Context
As the Autopoietic Agentic Assemblage (AAA) frontend scaled to support complex interactive workspaces, its UI components multiplied. We introduced three distinct view states (the landing page, the spatial node explorer page, and the standalone agent page) and multiple auxiliary panels (the collapsible pipeline telemetry side panel, the connection cloud graph, the spectral echoes sidebar, and the context inspector overlay).

Previously, these files were structured in a flat hierarchy under `frontend/src/components/`, which caused several issues:
1. **Name Collision and Confusion**: Flat organization made it difficult to identify which sections were sub-components of which pages or panels.
2. **Lack of Encapsulation**: Shared components and leaf components were intermingled, violating clean boundaries.
3. **Implicit Dependencies**: Reusable modules were imported across unrelated component layers without clear path indicators.

To improve project maintainability, visual hierarchy, and component self-containment, we decided to optimize the folder architecture.

## Decision
We refactored the frontend components directory into a clean, hierarchical structure divided into two top-level domains: **Pages** and **Panels**.

### 1. Standing Pages (`components/pages/`)
We grouped standalone viewport layouts into dedicated sub-folders containing the main page file and its immediate private sub-components:
*   `agentpage/` — Contains `AgentPage.tsx` and its custom telemetry tabs (`BeliefsSection.tsx`, `DreamingSection.tsx`, `SkillsSection.tsx`, `StartupSection.tsx`).
*   `landing/` — Contains `ConversationLandingPage.tsx` (the default entry point layout).
*   `nodeexplorer/` — Contains `NodeExplorer.tsx`, `MessageBubble.tsx`, `InputBar.tsx`, and `StructuralAutopoieticGlyph.tsx` representing the core spatial cut traversal view.

### 2. Embedded Panels (`components/panels/`)
We grouped auxiliary UI widgets, HUD meters, and overlay panels into specialized folders:
*   `leftpanel/` — Contains `ConnectionCloud.tsx` (the SVG/Canvas relational graph) and `SpectralEchoes.tsx` (the manual link-matching component). These are located under `panels/` to decouple them from the landing page.
*   `sidepanel/` — Contains `SidePanel.tsx` and its telemetry sections (`AttractorsSection.tsx`, `DiffractionSection.tsx`, `MemoryNodesSection.tsx`, `NotesSection.tsx`, `SedimentSection.tsx`, `TokensSection.tsx`, `VitalitySection.tsx`).
*   `contextviewer/` — Contains the active context inspector overlay and its parsing logic.

### 3. File Cleanup & Dependency Alignment
*   Deleted obsolete file wrappers: `ChatView.tsx` (remnant of the old scrolling timeline layout) and the top-level `ContextViewer.tsx` wrapper.
*   Adjusted relative imports across the codebase to ensure correct file paths.
*   Aligned the type signatures of navigation hooks. Specifically, the `selectMessage` navigation action in `useChat.ts` was refactored to support parameter signature `number | null`, matching the interface constraints of the `ConnectionCloud` graph.

## Consequences

### Positive:
- **Clean Component Boundaries**: Page developers can navigate and update sub-modules without search conflicts.
- **Architectural Clarity**: The distinction between layout containers (`pages/`) and control panels/HUDs (`panels/`) is physically enforced by the directory layout.
- **Improved Maintainability**: Imports are more descriptive of a component's architectural layer, reducing spaghetti imports.

### Negative:
- The depth of relative imports to the API layer (`api/client.ts`) and global config folders has increased for components that were nested deeper.
