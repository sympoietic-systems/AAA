# ADR-045: Persistent SQLite-Backed System Notifications and History Traces

**Status:** Accepted (Implemented)  
**Date:** 2026-06-12

## Context
Previously, the AAA platform’s notification system was entirely ephemeral:
1. **Volatile In-Memory Store:** The React frontend maintained notifications inside a transient JavaScript store. When the application restarted or the browser reloaded, unread notifications (arrival notifications, errors) were wiped clean.
2. **Scattered Polling & Event Ingestion:** Core background events—such as autonomous skill lifecycle updates, document digestion jobs, or belief dynamics metabolism updates—were either polled via separate custom components or kept hidden entirely. This caused redundant network overhead and split the architectural audit trail.
3. **No Archaeologic History Log:** Once a user cleared or dismissed a notification, it vanished from the interface forever, preventing historical analysis of Symbia's cognitive changes over time.

## Decision
We transitioned the notification system to a durable, SQLite-backed architecture integrated directly into the core agent pipeline.

### 1. SQLite Database Schema (`notifications` table)
Created a new database table `notifications` to act as a permanent sedimentary record:
- `id` (TEXT PRIMARY KEY) - UUID or message-match hash.
- `type` (TEXT NOT NULL) - Category mapping to `sediment`, `glitch`, or `trace`.
- `timestamp` (TEXT NOT NULL) - ISO UTC string.
- `snippet` (TEXT NOT NULL) - A concise, human-readable summary of the event.
- `conversation_id`, `message_id`, `parent_message_id` - Entanglement context markers.
- `speaker`, `source` - Context attributes (e.g. `skill:RefineSkill`, `perception:data.pdf`).
- `read`, `dismissed` (INTEGER DEFAULT 0) - Binary flags for read status and archiving state.

### 2. Backend Repository and FastAPI Router
- **NotificationRepository:** Created repository CRUD methods supporting selective paging, search queries, active list filtering (`dismissed = 0`), single or mass read updates, and soft-deletes via a dismissed flag.
- **REST Endpoints:** Defined endpoints under `/api/notifications` for GET, POST, read/dismiss patch transitions, and clear/mark-all-read commands.

### 3. Integrated System Event Ingestion
Connected the repository to the primary asynchronous worker and database pipelines:
- **Perception/File Indexing:** [digest_worker.py] posts a `trace` notification upon successful digestion, and a `glitch` notification (with error logs) upon ingestion failures.
- **Skill Lifecycles:** [SkillRepository] injects a lifecycle trace event description on skill emergence, crystallization, revision, or collapse.
- **Belief Crystallization & Dynamics:** [BeliefRepository] inserts a trace log during new belief crystallization (`create_belief`) and subsequent dynamic shifts (`insert_belief_event`).

### 4. Hybrid Store Synchronization & Polling
- **Unified Polling:** Replaced specific database event polling (e.g., skill event loops in `CreasesDropdown`) with a single, consolidated GET request to `/api/notifications?dismissed=false`.
- **Hybrid Synchronization:** The frontend `notificationStore.ts` fetches and hydrates database state on load, optimistically applies local UI modifications, writes updates to the backend in the background, and runs a 12-second poll to align other browser instances.

### 5. Geological Archaeology History View
- Introduced a new **Traces** tab in the `/agent` interface powered by the `<TracesSection />` component.
- Styled as a monospaced geological core-sample, this section allows full search queries, type filtering, reading, and dismissing archived (folded) notifications directly.

## Consequences

### Positive
- **Zero Loss of Alerts:** Unread notifications remain in the SQLite store across container restarts and system reboots.
- **Reduced Network Overhead:** Consolidating skill events, belief events, and file ingestion status into a single notifications table removes duplicate API polling loops.
- **Archaeological Auditing:** Keeping dismissed notifications in the database under `dismissed = 1` lets developers inspect the exact timeline of Symbia's observations.

### Risks
- **Table Growth:** The `notifications` table will grow continuously as system traces accumulate.
- *Mitigation:* The API enforces a default `limit=100` page and uses index-friendly offset queries. If required, a background daemon task can prune old folded traces beyond a threshold (e.g., 30 days) in future iterations.
