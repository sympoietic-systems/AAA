# ADR-040: Subscriber-Driven Telemetry Polling and Multi-Type Notifications Store

**Status:** Accepted (Implemented)  
**Date:** 2026-06-11

## Context
As the AAA frontend grew more complex, different components needed to display various real-time system metrics (Vitality metrics, Diffraction/stagnation states, Token usage, Belief Attractor Windows, and background Daemon/Scheduler states). 

Previously:
1. **Network Redundancy**: Every individual component spawned its own `useEffect` polling interval, fetching the same API endpoints (`/metrics`, `/beliefs`, `/tokens`, etc.) independently. If multiple telemetry sections were open, they sent duplicate, overlapping requests, wasting server and client resources.
2. **Hardcoded Polling Loops**: Component mounting and unmounting directly triggered api polling loops, with no global tracking of whether telemetry data was actually needed by any active UI element.
3. **Silent Errors**: When backend network calls failed (e.g. timeout, key rotation delay, or container restart), error details were printed to `console.error` but hidden from the user, making troubleshooting difficult.
4. **Single-Purpose Notifications**: The crease notifications store only tracked completed background messages, lacking support for system glitches (errors) and informational traces.

## Decision
We refactored both notifications and telemetry systems to use decoupled, reactive, subscriber-driven stores:

### 1. Multi-Type Notification Store (`notificationStore.ts`)
- **Expanded Types**: Added support for three distinct categories of notifications:
  - `sediment`: Background message arrivals and note notifications.
  - `glitch`: System errors, model failures, network timeouts, and file upload rejections.
  - `trace`: Optional developer or debugging trace logs.
- **Independent Tabbed UI**: Refactored the `<CreasesDropdown />` to display notifications in separate, filtered tabs (Arrivals, Glitches, Traces) with unread alerts for system glitches to grab attention during failures.

### 2. Subscriber-Driven Telemetry Store (`telemetryStore.ts`)
- **Centralized Registry**: Created a unified, pub-sub `telemetryStore.ts` to manage all telemetry categories (Metrics, Beliefs, Tokens, Daemon, Scheduler).
- **Reference-Counted Polling**: Telemetry sections are only polled when there is at least one active UI subscriber.
  - Subscribing to a category increments its listener count and triggers immediate data loading if the timer is inactive.
  - Unsubscribing decrements the listener count. When the count hits zero, the store tears down the background polling timer, eliminating network noise.
- **Conversation State Partitioning**: State records for conversation-specific telemetry (beliefs, token tallies) are cached using `conversationId` as the key.
- **Proactive Glitch Propagation**: When a telemetry endpoint fails or a user-initiated request throws an error, the store catches the exception and dispatches it as a `glitch` type notification, populating the new notifications dropdown tab.

### 3. Modular React Hooks
- Refactored `useTelemetry.ts` into individual, granular hooks (`useTelemetryMetrics`, `useTelemetryBeliefs`, etc.).
- The hooks manage subscription lifecycle matching the component lifecycle, mapping store state to React component state.

## Consequences

### Positive
- **No Duplicate API Queries**: Even when multiple widgets require the same telemetry data, they share a single request loop.
- **Automatic Resource Cleanup**: Polling only runs when the telemetry panel is open, freeing the main thread and database when minimized.
- **Enhanced Observability**: Users are instantly alerted of system failures (glitches) without opening browser dev tools.
- **Strict Typing**: Full generic type definitions in React hooks prevent compiler type leakage and restore clean map callback signature completions.

### Risks
- **Cache Persistence**: Cached conversation telemetry is kept in memory. Given the lightweight JSON response sizes (less than a few hundred nodes/tokens per conversation), this memory footprints remain negligible.
