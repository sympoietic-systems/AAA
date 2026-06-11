# ADR-038: Creases (Background Sediment Arrivals) and Pure JS Notification Store

**Status:** Accepted (Implemented)  
**Date:** 2026-06-11

## Context
When a user sent a message and navigated away (either to a different conversation or to a different node in the conversation tree) before the agent's response generated:
1. **Focus Hijacking**: The UI would forcefully shift active focus to the newly arrived response, disrupting the user's ongoing reading or writing flow.
2. **State Corruption**: In cross-conversation scenarios, the returning generation promise would inject the message and graph state into the newly loaded conversation, causing memory state corruption.

While placing local state filters inside `useChat.ts` guarded the app from corruption, it introduced a severe performance regression:
- On every background notification arrival or dismissal, the entire `App` component and its sub-trees (chat view, inputs, sidebar) were forced to re-render.
- Since multiple generations can run in the background, layout thrashing degraded performance on rapid, sequential navigations.

## Decision
We implemented a decoupled background notifications system ("Creases") leveraging a pure JS external store to guarantee zero-overhead updates:

### 1. Pure JS External Store (`notificationStore.ts`)
- Created `frontend/src/stores/notificationStore.ts` using React 19's `useSyncExternalStore` API.
- The store maintains a pure JS array of notifications. Mutations (`addNotification`, `dismissNotification`, `clearAllNotifications`, `dismissByMatch`) are simple function calls.
- Calling these mutations causes **zero React re-renders in the caller component/hook** (such as the main chat loops in `useChat.ts`).
- Only components explicitly subscribing to the store via `useNotifications()` will re-render.

### 2. Isolated UI Subscription (`CreasesDropdown.tsx`)
- Extracted the notification list subscription and rendering into a dedicated `<CreasesDropdown />` component.
- The dropdown handles:
  - Outside click listeners.
  - Mapping raw notifications to local conversation titles.
  - Displaying the creases indicator badge and dropdown items.
- Since only `<CreasesDropdown />` subscribes to the store, adding, removing, or clearing notifications triggers re-rendering **exclusively inside the dropdown scope**. Neither `App` nor `NodeExplorer` re-renders.

### 3. Asynchronous State Guards & Auto-Dismissal
- **`useChat.ts` Guards**: The hook tracks active targets via `loadedRef` and `activeMessageIdRef`. When a generation completes, the callback checks whether the user is still viewing the initiating node/conversation. If not, it registers a notification in the store and keeps current state untouched.
- **Auto-Dismissal**: An effect in `useChat.ts` automatically calls `dismissByMatch(conversationId, activeMessageId)` when the active message changes, clearing the crease without React state updates.

## Consequences

### Positive
- **Zero Layout Thrashing**: Adding background responses generates zero re-render overhead on the main application interface. Input fields, chat lists, and metrics remain fully interactive.
- **Improved Responsiveness**: Navigation between nodes and conversations feels instantaneous, completely decoupled from background agent response completions.
- **Clean Component Hierarchy**: Cleaned up the `App.tsx` and `NodeExplorer.tsx` props, removing five separate notification-related states and callback functions.

### Risks
- **Title Mapping Sync**: To display the conversation titles in the dropdown, the `<CreasesDropdown />` must do a lookup on the list of conversations. We resolved this by passing the static list of conversations down from `App` to `<CreasesDropdown />` as a stable reference.
