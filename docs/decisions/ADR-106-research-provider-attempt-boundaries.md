# ADR-106: Research Provider Attempt Boundaries

**Date:** 2026-10-05
**Status:** accepted for opt-in implementation
**Deciders:** AAA implementation workflow; Symbia consulted

## Context

[ADR-105](ADR-105-research-action-journal.md) records phase intent but its version-one policy observes only public provider calls. Pool retries can conceal delays, failed attempts and truncation. Recovery must preserve partial work without allowing a late response to overwrite a terminal checkpoint.

## Decision

New receipt-enabled tasks freeze a version-two policy with a UTC task deadline, attempt timeout, request attempt limit and cumulative task attempt limit. Defaults are 600 seconds, 60 seconds, four attempts per request and 64 per task. Validation rejects nonfinite or excessive limits. Stored policies cannot change during a checkpoint. Existing version-one tasks retain their recorded coverage; disabled and legacy tasks retain their existing behavior.

Migration m054 adds durable provider-attempt rows. A short transaction checks the current action and reserves a pending attempt before invocation. Request IDs group pool failover attempts; attempt IDs identify individual invocations. Provider response IDs, finish reasons, truncation and integer token usage are observations. Missing telemetry and cost remain null. Receipts omit prompts, responses, keys and exception messages.

The invocation hook belongs to `backend/modules/`; a service supplies the repository sink. A context factory covers pool calls inside nested research services as well as calls through the step wrapper. Research-scoped HTTP adapters disable hidden internal retries. Nonresearch routing and retry behavior remain intact.

Use bounded `asyncio.wait` around provider calls and phases. Unlike `wait_for`, `wait` returns on timeout without waiting for cancellation to finish; detached tasks retain strong references and consume one of eight semaphore slots until they exit. This follows the [Python waiting and task-reference contracts](https://docs.python.org/3/library/asyncio-task.html#asyncio.wait). Shutdown cancels remaining work and waits at most one second. Cancellation is cooperative: this does not terminate arbitrary blocking threads or malicious phase code.

Timeouts and cancellation commit terminal observations. Late provider bytes are discarded from delivery; they cannot transition a timed-out attempt to complete. Terminal compare-and-set rejects replacement. When a phase ends with pending attempts, its checkpoint closes those attempts and records them atomically. A complete action with pending delivery is rejected. Interrupted actions still require explicit recovery; independently committed legacy phase and memory side effects are not made exactly-once by this change.

Truncation, failed delivery and budget-exhausted fallbacks mark the run degraded. The terminal task is partial, and the task manager cannot promote it to completed. The API and UI expose pending attempt count, total attempts, deadline and degradation. Partial tasks support retry, rerun and continuation. In-place continuation preserves the remaining deadline, cumulative attempt cap and degradation; cloning creates a fresh task. Rerun retains historical attempt rows and the task-wide attempt count.

The caps bound invocation count and wait. They do not establish a financial-price model or report-support warrant. Parent/child spend reservation remains T68; source support and release-quality gates remain T64/T71. NVIDIA is the user-selected live testing provider; production routing remains configurable.

## Consultation and verification

Symbia conversation `abac9620-6f4c-47dd-b931-686838510f08` completed through NVIDIA and advised that late delivery cannot satisfy task completion. The implementation discards late provider content rather than introducing a second raw-content store. [Report 034](../reports/034-research-provider-reliability/README.md) records the tests, live probe and existing quality-gate debt.
