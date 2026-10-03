# ADR-099: Chat Response Quality Diagnostics

**Date:** 2026-10-03
**Status:** accepted
**Deciders:** AAA maintainers

## Context

Production reports described runaway lexical repetition, empty or failed generations, and answers that stopped mid-response. Provider failures were not always distinguishable from unusable output in the application logs. A single malformed answer is also not enough evidence to label an entire conversation or model as collapsed.

Operators need enough metadata to investigate a failure while avoiding prompt and completion content in logs. A lightweight quality signal can help locate obvious response degradation, provided it remains diagnostic and does not control the reply.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| Log provider and chat completion metadata; include a bounded response-quality judgment in the existing Jev assessment | Correlates provider finish reason and request ID with empty, truncated, or clearly degraded output; adds no separate Jev request on the normal Jev path | The quality judgment can be wrong and requires later calibration against independently labeled examples |
| Add a separate evaluator request after every answer | Independent evaluator and easier to evolve separately | Adds latency, cost, and another failure point |
| Gate, rewrite, or retry answers based on the quality judgment | Could suppress some bad output automatically | Gives an uncalibrated evaluator control over user-visible answers and can introduce retry loops |

## Decision

Log safe completion metadata at the provider boundary: provider, requested and returned model, request ID when available, HTTP status, finish reason, truncation flag, visible and reasoning character counts, token usage when supplied, and effective generation controls. Log explicit errors for invalid provider JSON, missing completion choices, malformed choices, and empty or non-text completions. At the chat boundary, log unusable pipeline results with module and error types. Do not log prompt, user message, or generated text.

For the normal Jev-backed structural assessment, add one `response_quality` choice using the existing assessment call. Bound the supplied reply to the scorer's existing 3,000-character limit and the current user turn to 1,500 characters. The labels are `sound`, `degraded`, and `uncertain`. Only clear local incoherence, runaway lexical chaining, or a non-answer should be marked degraded. Log the judgment and available confidence with turn ID, model, response length, finish reason, and truncation status. Keep this judgment separate from the 16 structural dimensions and conversation-level collapse metrics.

The judgment is observational: it does not gate, rewrite, or retry a response. If Jev is unavailable or returns no valid judgment, record that the check was unavailable. Reduce the homeostatic regulator's default temperature ceiling from 1.5 to 1.0 as a bounded mitigation; this does not guarantee prevention and does not override provider-specific reasoning modes that ignore temperature.

## Consequences

- Provider and chat logs can distinguish upstream response problems from unusable application output without retaining user or assistant text.
- Truncation and visible-output length can be correlated with request IDs and effective generation settings.
- The normal Jev path gains one local quality observation in its existing request. It adds no separate evaluator request.
- A `degraded` judgment is a heuristic signal, not proof of model failure or conversation collapse. It must not trigger automated remediation until validated against independent labels.
- When a forced LLM structural scorer bypasses Jev, this Jev quality judgment is not produced; provider and chat boundary diagnostics still apply.
- Lowering the temperature ceiling limits sampling variation, but cannot prevent every pathological response.
