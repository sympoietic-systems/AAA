# ADR-114: Persistent response quality and context exclusion

Date: 2026-10-08
Status: Accepted for implementation; production activation awaits deployment.

## Context

An assistant response in conversation `a04d68e8-9075-42cc-8cff-6931335f820d` (message 3996) began coherently, then deteriorated into repeated lexical fragments. Its OpenRouter request completed with HTTP 200, `finish_reason=stop`, and no provider truncation flag. The earlier Jev check sampled the first 3000 characters, so it missed the failing tail. The model change did not remove the underlying detection gap.

The dream path also required structural scoring and had no independent response-quality pass. Dream 3899 contained a long reasoning trace returned as the final response; the provider adapter promoted reasoning when final content was empty. Degraded messages appeared in later dream context. This supports a propagation path for some dreams; it does not establish a single cause for every degraded response.

The 14-day retrospective sampled the beginning and ending of 109 assistant messages using Jev. Eleven were assessed degraded: ten had Jev confidence at or above 0.7, and one additional reply matched its reasoning text exactly. This includes message 3996 and dream replies 3864 and 3899. Fifty-three were uncertain and remain eligible for context. Four assessed message IDs no longer resolve to a message path on the live server.

## Decision

Persist a content-hash-bound quality receipt on each assistant message. Assess both the opening and ending of long replies. Exact final-content/reasoning duplication is a deterministic degraded signal. Jev outputs below the confidence floor, malformed outputs and unavailable evaluations become `uncertain`; they do not remove material from context. These observations do not alter structural metrics, beliefs, or the original response body.

Messages marked degraded remain visible in history and export, with an inline frontend badge and reversible manual classification. The message also creates a linked Creases/Traces notification using its assistant message ID. Manual classifications survive automated reassessment until a participant changes them. Content edits invalidate the current receipt and stale writes are rejected.

Generation history, compressed context, consolidation checkpoints, and cross-conversation retrieval omit degraded assistant messages. Existing derived summaries are suppressed conservatively for conversations containing a degraded message because their provenance may include that reply. Uncertain messages remain eligible. Dreams and ordinary chat use the same assessment path regardless of their structural scorer configuration.

Provider output contract: reasoning is retained in the separate `thinking` field and is never promoted into final content. A response with `finish_reason=length` or `max_tokens`, or without non-empty final content, is rejected so the model pool can try another configured model. If all providers fail, the request returns an error instead of persisting a partial or reasoning-only reply.

Known leaked provider control markers (`<|tool_call_begin|>`, `<|tool_call_end|>`, and `<|tool_sep|>`) receive a deterministic degraded quality label and are excluded from later generation context. Degraded assessments appear in the Creases/Traces Glitch category; uncertain assessments appear under Trace for review.

For diagnosis, migration `m061_message_generation_receipt` adds one compact nullable JSON field to generated messages: provider request ID, finish reason, truncation flag, usage counts, and generation controls. Existing `model_used`, `provider_used`, and `context_sent` remain the source for model, provider, and sent context. The new receipt does not duplicate prompt, response, or reasoning text. Provider logs use the request ID and safe lengths/control metadata; no raw prompts or response bodies are logged.

## Deployment and backfill

Apply migrations `m059_message_quality` and `m061_message_generation_receipt` before enabling the application routes or processing backfill. Audit with `uv run python -m scripts.backfill_response_quality --days 14 --output <path>`. The script stores IDs and receipts, not message bodies, checkpoints by content hash and sample version, and resumes sequentially. After the server includes these migrations and the assessment endpoint, apply using the same command with `--apply`.

Seven degraded cases whose conversation paths remain available were added to live Creases/Traces on 2026-10-08. Their trace text states that context exclusion starts after migration deployment. The live server does not expose the quality fields or exclusions yet, so these traces are review links rather than evidence that production context has already changed. Four historical IDs returned 404 and received no trace because their conversation paths could not be verified. No message content was changed.

## Architectural consultation

The [architectural decision workflow](../../.agents/skills/mcp-architectural-decision/SKILL.md) consulted AAA/Symbia on 2026-10-07 in conversation `3f614e28-ad6e-4746-8423-3713ce2dcd77`. The adopted boundary separates preservation of the original inscription from its eligibility for future retrieval, retains receipts and participant overrides, and gives Jev no authority over beliefs or structural metrics.

## Verification

Focused response-quality tests passed (12 tests), dream-daemon compatibility tests passed (18 tests), the chat integration test passed (1 test), and the final targeted regression batch passed (36 tests). Frontend badge tests passed (2 tests), frontend strict type checks and production build passed, `ruff check backend/` passed, and strict Python typing passed. The full backend suite reported 668 passes and two failures: a broad-catch budget increase in the dream path and the repository-facade contract test missing the new collaborator. The catch was removed so proposal-processing failures propagate, and the facade contract now declares the quality collaborator; the focused regression batch covering both paths then passed. The full suite was not rerun after those two corrections. Production context exclusion remains unverified until deployment.
