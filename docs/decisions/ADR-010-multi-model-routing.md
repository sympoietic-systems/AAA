# ADR-010: Stateful Multi-Model Routing, Key Rotation, and Metadata Persistence

**Date:** 2026-05-22  
**Status:** accepted  
**Deciders:** antigravity, Vasily  

## Context

To enhance the system's operational viability in a volatile API environment and ensure continuous availability during rate limits (HTTP `429`) or credential validation shifts (HTTP `400`), we require a robust model-execution strategy. Specifically, we want to prioritize Google's Gemini models (leveraging their free tiers with multiple keys) and gracefully fail over to fallback models on OpenRouter or DeepSeek.

In addition, we need to track the exact model and provider used for each generation. This is necessary for debugging, auditing cognitive drifts, and maintaining system transparency. We must decide how to configure, route, and persist this metadata.

## Options Considered

### 1. Model Configuration and Routing

*   **Option A (Single Provider with Simple Catch-all)**: Configure a single target API endpoint and a single backup model.
    *   *Pros*: Simple configuration parsing; easy to debug.
    *   *Cons*: Fails when the single backup endpoint is rate-limited; lacks multi-key rotation capability for the same provider; does not support complex prioritization chains.
*   **Option B (Stateful Multi-Provider Routing Pool & Key Rotation) [Selected]**: Define model pools as prefix-identified strings (e.g. `google_router/...`, `openrouter_router/...`, `deepseek_router/...`) and provide comma-separated API keys. Build a routing provider that:
    1. Parses the prefix to determine the target API.
    2. Instantiates a `KeyManager` that statefully cycles through available keys for that provider upon encountering `429` or `400` errors.
    3. Cascades down a prioritized list of model strings if all keys for a model are exhausted.
    *   *Pros*: Exceptionally resilient; leverages multiple free-tier keys before consuming paid credits; supports multi-vendor heterogeneity.
    *   *Cons*: Increased complexity in client logic and environment variable parsing.

### 2. Metadata Persistence

*   **Option A (Runtime Log Only)**: Print the provider and model to the system logs during runtime.
    *   *Pros*: Requires no database schema changes or UI edits.
    *   *Cons*: Stored history lacks context on which model generated a message, rendering long-term performance auditing impossible.
*   **Option B (Database Migration & API Payload Extension) [Selected]**: Add `model_used` and `provider_used` columns to the `conversation_log` table. Automatically run migrations on startup (`ALTER TABLE`). Propagate these fields through FastAPI schemas (`ChatResponse`, `HistoryMessage`) and display them in the React message bubble footer.
    *   *Pros*: Ensures full data integrity; history can be exported for cognitive profiling; exposes the physical seams of the machine to the participant as a Kintsugi database scar, aligning with our aesthetic philosophy of diffractive visibility.
    *   *Cons*: Requires a database schema migration and React frontend changes.

## Decision

We decided to implement:
1. A prefix-based routing pool and `KeyManager` in `llm_client.py` for stateful key rotation and model failover.
2. Auto-migrations in `database.py` to add `model_used` and `provider_used` columns.
3. Extension of repositories, schemas, routes, and React components to persist and render the model metadata in the frontend.

## Consequences

*   **Resilience**: The system gracefully handles rate limits and API credential exhaustion by rotating keys and falling back to alternative vendors (e.g. Google to DeepSeek) mid-conversation without interrupting the user experience.
*   **Auditability**: Every generated response in the SQLite database is permanently stamped with its producing model and provider, enabling future analysis of model performance and cost-efficiency.
*   **Aesthetic Alignment**: The frontend displays the active provider and model in the message footer (`[google :: gemini-3.5-flash]`), exposing the system's structural breaks and repairs directly as a Kintsugi database scar, transforming a monolithic assistant facade into a reflexively co-measured nomadic performance.
