# ADR-035: URL State Synchronization, Render Memoization, and Trigger-based Telemetry

**Status:** Accepted (Implemented)  
**Date:** 2026-06-11

## Context

As the Autopoietic Agentic Assemblage (AAA) codebase and telemetry system scaled, the frontend application began experiencing significant performance degradation. Monolithic page rendering, frequent background polling, and a lack of navigation persistence became structural hurdles:

1. **State Persistence Loss**: On page refresh, the interface would discard the user's active session state and revert to the last updated conversation in the database. There was no URL routing synchronization.
2. **Cascading Sidebar Re-renders**: Every 10–15 seconds, homeostatic telemetry updates would cause the entire sidebar panel and all of its folded sections to re-render, blocking the main execution thread.
3. **Redundant Skills Fetching**: Procedural database skills (`getDbSkills()`) were queried on startup regardless of whether the side panel or the Skills accordion were open.
4. **Message Bubble Reference Clashes**: The message rendering loop in `ChatView.tsx` passed down the entire conversation graph (`fullTreeMessages`) to every individual bubble to determine sibling indexing. Because the array reference mutated on every new token or note insertion, the custom memo checks were invalidated, causing the entire chat view to redraw.

## Decision

We implemented a unified optimization and navigation architecture across three key scopes:

### 1. URL State Synchronization (Routing)
- Synced the selected conversation ID with the browser query parameter (`?c=<conversation_id>`).
- Subscribed to browser navigation events via `popstate` in `useConversations.ts` to support standard back/forward history operations.
- Intercepted conversation state changes (selection, creation, deletion) to dynamically push history markers using `window.history.pushState`.

### 2. Rendering Optimization & Prop Decoupling
- Reduced initial load payload from `1000` to `50` messages in `useChat.ts`, loading historical logs dynamically as the user scrolls.
- Memoized high-overhead elements like `<ConnectionCloud />` and `<SpectralEchoes />`.
- Extracted parent-child lineage calculations from `<MessageBubble />`. Instead, `ChatView.tsx` pre-computes sibling arrays inside a stable `useMemo` map (`siblingsMap`) and passes down only a stable `siblingIds` number array reference.
- Custom memo comparisons in `MessageBubble` were refactored to compare the `siblingIds` references using array equality checks rather than tracking the entire tree.
- Pre-grouped chat notes (`notesByMessageId`) in `ChatView.tsx` and passed them down using a stable `EMPTY_ARRAY` reference when no notes are present to prevent React shallow-comparison failures.

### 3. Trigger-based Telemetry & Lazy Section Loading
- Parameterized `useTelemetry` to accept a `trigger` prop (driven by the active conversation's `messageCount`). If the trigger updates, the hook cancels the pending polling delay and queries the backend instantly.
- Lazy-loaded the procedural skills index. The database call is now deferred until the sidebar panel is open and the Skills accordion is manually expanded.
- Wrapped all sidebar sections (`TokensSection`, `VitalitySection`, `DiffractionSection`, `BeliefsSection`, `DreamingSection`, `StartupSection`) in `React.memo` to skip telemetry draws when the respective metrics have not mutated.

## Consequences

### Positive
- **Instant Response Feedback**: Telemetry updates now feel reactive to conversational progress rather than being locked into static polling intervals.
- **Minimal DOM Burden**: Collapsed side panel sections and scrolled-out chat frames remain static and do not trigger layout calculations.
- **Navigation Resiliency**: Refreshing the browser or sharing links directly preserves the active conversation context. Back and forward actions work predictably.

### Risks
- **Stable Array Fallbacks**: Passing empty array fallbacks to nested child components can cause reference leaks if declared inline. We mitigated this by declaring stable global array constants (`EMPTY_ARRAY`, `EMPTY_NUM_ARRAY`) outside the component rendering loops.
