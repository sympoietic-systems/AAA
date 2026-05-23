# ADR-012: Conversation Pagination, On-Demand Detail Loading, and Render Memoization

**Date:** 2026-05-23  
**Status:** accepted  
**Deciders:** antigravity, Vasily  

## Context

As conversations accumulate text and media files over time, loading the entire chat history and its associated document sediments in monolithic API payloads creates severe computational bottlenecks. The React DOM footprint grows extremely large, causing render delays, typing stutter, and high memory usage. 

Specifically:
1. **Payload Bloat:** Monolithic history fetches load large fields (`thinking` traces, global context sent prompts, and file summaries) that are rarely inspected by the participant in a normal flow.
2. **Render Bottlenecks:** Rendering dozens of heavy Markdown bubbles concurrently blocks the main UI thread during parent state changes (such as the 5-second homeostatic metrics updates).
3. **Scroll Instability:** Prepending historical messages when scrolling up causes sudden viewport jumps, disrupting user navigation.

We need a strategy to keep the initial render weight lightweight, fetch heavy columns only when explicitly queried, stabilize scroll offsets on prepending, and restrict React re-renders to modified components.

## Options Considered

### 1. Message Rendering & Pagination
*   **Option A (DOM Virtualization / Windowing):** Use a virtualization library (e.g., `react-window`) to only render items within the visible viewport.
    *   *Pros:* Scales to infinite conversations; highly performant DOM footprint.
    *   *Cons:* Extremely complex to implement with highly variable, dynamic-height elements (Markdown text, code blocks, expandable metrics panels).
*   **Option B (Incremental Pagination & Scroll Anchoring) [Selected]:** Implement pagination on the `/api/history` endpoint with scroll-anchored loading. On startup, load a small slice of recent messages (e.g. `PAGE_SIZE = 3`), prepending older chunks as the user scrolls up, adjusting the scroll position relative to the height difference to prevent jumping.
    *   *Pros:* Simple DOM layout, natural scroll navigation, low initial render cost.
    *   *Cons:* Older messages are still added to the DOM once loaded (mitigated by memoization).

### 2. Large Field Retrieval
*   **Option A (Full Payload on Request):** Continue sending `thinking`, `context_sent`, and file `summary` in the list responses but hide them behind CSS collapses.
    *   *Pros:* No additional backend endpoints required.
    *   *Cons:* Significant network and database overhead; database connections block transferring large fields that may never be read.
*   **Option B (Lazy On-Demand Details Loading) [Selected]:** Omit `thinking`, `context_sent`, and file `summary` from standard list responses (setting them to `None`/`null`). Implement dedicated GET endpoints to load them on-demand. When the user expands a bubble or summary section, fetch the content via the API and render it. Unmount the elements from the HTML DOM entirely when collapsed.
    *   *Pros:* Minimizes network transfer and database load; keeps the HTML DOM extremely lean; aligns with our aesthetic commitment to relational opacity (loading metadata first, details only on closer interaction).
    *   *Cons:* Introduce small loading spinner delays when expanding columns.

### 3. Rendering Redundancy
*   **Option A (Standard React Rendering):** Let React re-render the entire message list on any state change.
    *   *Pros:* Simple code structure.
    *   *Cons:* Markdown parsing is heavy; typing stutter occurs on every metrics update or background poll.
*   **Option B (React Component Memoization) [Selected]:** Wrap `MessageBubble` in `React.memo` with a custom equivalence checker comparing message ID, speaker, contents, thinking state, context text, and metrics.
    *   *Pros:* Prevents outdated messages from being parsed or re-rendered, reducing render overhead to $O(1)$.
    *   *Cons:* Requires careful reference comparison functions to avoid missing updates.

## Decision

We decided to implement **Option B** for all three areas:
1. **Database-level pagination (`LIMIT / OFFSET`)** starting with a light initialization of 3 messages.
2. **Dedicated lazy-loading API endpoints** for message thinking, context, and file summaries.
3. **On-demand fetching UI states** that completely unmount collapsed details from the HTML DOM.
4. **React memoization (`React.memo`)** for message bubbles to optimize rendering performance.
5. **Scroll height offset anchoring** inside `ChatView.tsx` during chunk prepending.

## Consequences

*   **Responsiveness:** Typing lag and scroll stuttering are completely eliminated. React ignores old message bubbles when homeostatic metrics are polled or updated.
*   **Reduced Bandwidth & Connection Time:** Typical conversation payload size drops from megabytes of hidden thinking logs to a few kilobytes of text.
*   **UI Experience:** When scrolling up, previous message chunks load seamlessly and are prepended without throwing the scrollbar position off-course. Collapsed nodes are cleanly pruned from the DOM.
