# ADR-050: Frontend Codebase Optimization — Extraction, Deduplication & Code Splitting

**Status:** Accepted (Implemented)  
**Date:** 2026-06-24

## Context

Over several months of rapid feature development, the AAA frontend accumulated structural debt in its largest files. Four critical files exceeded 700 lines each, with `ConnectionCloud.tsx` reaching 1,131 lines and `useChat.ts` at 802 lines. Several patterns had been duplicated across components:

1. **Inline component definitions inside render functions** (e.g., `renderResearchProposalComponent` in `MessageBubble.tsx`) violated React's rules of hooks by calling `useState`/`useEffect` from within a non-component function.
2. **Duplicate polling infrastructure** — five identical pub-sub patterns (metrics, beliefs, tokens, daemon, scheduler) in `telemetryStore.ts` (429 lines).
3. **Duplicate API calls** — `ConnectionCloud.tsx` independently fetched `getConversationTree()` despite `useChat` already loading the same data.
4. **Duplicate resize logic** — left and right panel resizers in `App.tsx` were near-identical ~57-line implementations.
5. **Duplicate title editing UI** — desktop header and mobile bar rendered the same title form twice.
6. **No code splitting** — the entire application loaded as a single 964 KB bundle regardless of which page the user visited.
7. **No frontend tests** — zero test infrastructure or test files.

## Decision

We performed a systematic refactoring in four batches, each ending with full verification (tests, lint, type-check, build).

### Batch 1 — Pure Extractions

- **`usePanelResizer` hook** (`hooks/usePanelResizer.ts`): Extracted duplicated resize logic from `App.tsx` into a reusable hook with `storageKey`, `minWidth`, `computeMaxWidth` options. Both left and right panels use it via destructuring.
- **`ConversationTitleBar` component** (`components/shared/ConversationTitleBar.tsx`): Encapsulated title display, inline editing, and generate/export buttons. Accepts `variant: "desktop" | "mobile"` for responsive styling. Removed `editingTitle`, `titleVal`, `handleTitleSubmit` state from `App.tsx`.
- **`buildNotesMap` utility** (`utils/noteHelpers.ts`): Centralized the `Map<messageId, NoteInfo[]>` construction that was duplicated in `NodeExplorer.tsx` and `ConnectionCloud.tsx`. Exported `EMPTY_NOTE_ARRAY` constant for stable reference equality.

### Batch 2 — Component Splits (Fixing React Rules Violations)

- **`ResearchProposalCard`** (`nodeexplorer/ResearchProposalCard.tsx`): Extracted the 150-line inline component from `MessageBubble.tsx`. Now a proper standalone component with its own `useState`/`useEffect` hooks, imported via react-markdown's `components` config. Fixes React rules violation.
- **`SelectionToolbar`** (`nodeexplorer/SelectionToolbar.tsx`): Extracted the Copy/Note popup that appears on text selection. Uses shared `copyToClipboard` utility.
- **`NoteEditorPopover`** (`nodeexplorer/NoteEditorPopover.tsx`): Extracted the note add/edit popup with visibility selector and save/cancel/delete actions.

### Batch 3 — Infrastructure Consolidation

- **`telemetryStore.ts` generic factory**: Created `createPollingChannel<T>(name, fetcher, interval)` and `createKeyedPollingChannel<T>(...)` factory functions. Replaced five identical pub-sub implementations. Exports remain identical — zero consumer changes. 429 → 279 lines.
- **ConnectionCloud tree deduplication**: Removed independent `getConversationTree()` fetch from `ConnectionCloud.tsx`. Tree data now flows from `useChat` via `App.tsx` props (`treeNodes`, `treeLinks`). Eliminates duplicate API call.

### Batch 4 — Architecture & Performance

- **React Router integration**: Added `react-router-dom`, wrapped `main.tsx` in `<BrowserRouter>`. Replaced manual `window.location.pathname` if/else chains with `<Routes>`/`<Route>` in `App.tsx`. Replaced all `window.location.href`/`window.location.replace` with `useNavigate()`.
- **Code splitting via `React.lazy()`**: Six page components (`TeaserPreview`, `LoginPage`, `AgentPage`, `ResearchPage`, `ResearchTaskPage`, `ConversationLandingPage`) are now lazy-loaded. Initial bundle reduced from 964 KB to 790 KB (18% reduction). Non-workspace pages load on demand.
- **ConnectionCloud pan/zoom to refs**: Moved `pan` and `zoom` from React state to `useRef` values with a `redrawTick` counter trigger. Eliminates per-frame re-renders during canvas drag interaction. `onWheel` handler attached directly via `addEventListener` with `{ passive: false }` for React 19 compatibility.
- **`dimensionsRef`**: Canvas wheel handler reads dimensions from ref instead of stale state closure.

### Test Infrastructure

- **Vitest + Testing Library**: Installed `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `jsdom`.
- **`vitest.config.ts`**: JavaScript DOM environment, auto-setup with `@testing-library/jest-dom/vitest` matchers.
- **`src/tests/setup.ts`**: Global `localStorage` mock for all tests.
- **93 tests across 10 files**: Pure function tests (`estimateTokens`, `getAncestorPathIds`, `areNumberArraysEqual`, `areStringArraysEqual`, `areNotesEqual`, `computeLineDiff`, `formatTime`, `formatDateTime`, `formatTimestamp`, `formatRelativeTime`, `copyToClipboard`, `buildNotesMap`), hook tests (`usePanelResizer`, `telemetryStore`), and component tests (`ConversationTitleBar`, `ResearchProposalCard`).

## Consequences

### Line Count Reductions

| File | Before | After | Reduction |
|------|--------|-------|-----------|
| `App.tsx` | 788 | 588 | -200 (25%) |
| `MessageBubble.tsx` | 871 | 578 | -293 (34%) |
| `ConnectionCloud.tsx` | 1,131 | 981 | -150 (13%) |
| `telemetryStore.ts` | 429 | 279 | -150 (35%) |
| `useChat.ts` | 802 | 734 | -68 (8%) |

**Total**: 4,021 → 3,160 across major files (**861 lines removed, 21% reduction**).

### New Files (14 source + 10 test)
- `hooks/usePanelResizer.ts`
- `components/shared/ConversationTitleBar.tsx`
- `utils/noteHelpers.ts`
- `components/pages/nodeexplorer/ResearchProposalCard.tsx`
- `components/pages/nodeexplorer/SelectionToolbar.tsx`
- `components/pages/nodeexplorer/NoteEditorPopover.tsx`
- 7 test files + `vitest.config.ts` + `src/tests/setup.ts`

### Performance
- **Initial bundle**: 964 KB → 790 KB (18% smaller main chunk)
- **Lazy chunks**: AgentPage (112 KB), ResearchTaskPage (79 KB), ConversationLandingPage (11 KB), ResearchPage (8 KB), TeaserPreview (4 KB), LoginPage (2 KB)
- **Canvas interaction**: Pan/zoom no longer triggers React re-renders
- **Tree fetching**: One less API call per tree update

### Maintainability
- All components that were defined inside render functions are now proper standalone modules
- Duplicate state management patterns consolidated into reusable hooks/utilities
- Test coverage for all pure utility functions and key components
- Clear dependency flow: ConnectionCloud receives tree data via props instead of independent fetch

### Verification Gates (all green)
- `npm test`: 93 tests pass
- `npm run build`: Succeeds with code-split chunks
- `npm run lint`: No new errors
- `npx tsc -b`: No new type errors
