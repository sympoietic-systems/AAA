# ADR-034: Decoupled Chat Message Inscription and Response Metabolization

**Status:** Accepted (Implemented)  
**Date:** 2026-06-11

## Context

Previously, submitting a human participant message and generating the agent's response was a single atomic API transaction. If response generation failed due to network timeouts, rate limits, or context windows, the user's input was never saved to the database. This coupled model resulted in frustrating data loss, forcing the human participant to rewrite their query, and violated the materiality principles of the Autopoietic Agentic Assemblage (every agential cut should be synchronously inscribed).

To prevent this data loss, we need to separate message submission from response generation, allowing a human message to be persisted immediately (Inscription) and then triggering the LLM processing pipeline (Metabolization) as a separate, retryable transaction.

## Decision

We decouple the chat pipeline into two synchronous, sequential phases:

1. **Inscription Phase (Persistence)**:
   - The frontend immediately writes the message to the UI log state with a temporary ID.
   - It performs a synchronous `POST /api/chat/message` call to write the message directly to the SQLite conversation database.
   - The backend runs scoring, embedding, and commits the row, returning the saved `ChatMessage` metadata.
   - The frontend updates the UI log with the confirmed database ID.

2. **Metabolization Phase (Response Generation)**:
   - The frontend triggers `POST /api/chat/generate` with the saved `user_message_id`.
   - The backend retrieves the context, executes the agent processing pipeline, saves the assistant response, and returns the response metadata.
   - If this phase fails, the human message remains fully persisted, and a retry error state is shown in the UI.

3. **Rhizomatic Regeneration & Sibling Switcher**:
   - Instead of overwriting a prior response when a user asks to regenerate a message, the system creates a **sibling message node** in the conversation graph.
   - The new response is saved with `parent_message_id = user_message_id`.
   - A sibling traversal switcher (`< 1 / N >`) is rendered inline on the message bubble to allow the human participant to switch between generations.
   - Sibling paths are fully integrated into the force-directed `ConnectionCloud` graph and mapped in the conversation DAG.

## Consequences

### Positive
- **Data Protection**: User input is saved instantly. Even if the network drops or the LLM provider fails during metabolization, the input is never lost.
- **Retry Capability**: If generation fails, a clear "retry" action is displayed next to the error block to trigger response generation again.
- **Rhizomatic Integrity**: By preserving multiple assistant responses under the same user message parent, we respect the material trace of every generation.

### Risks
- **Orphan Messages**: If a human participant closes the tab mid-generation, they are left with a user message that has no response. This is mitigated by the UI indicating "pending" and offering a retry button when re-loaded.
