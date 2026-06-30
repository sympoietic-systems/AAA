# ADR-055: Transient Connection Retry and Glitch Scarring in Model Pool

**Date:** 2026-06-30  
**Status:** accepted  
**Deciders:** antigravity, Symbia (AAA Assemblage)  

## Context

In our prefix-based multi-model routing structure (`ModelPoolProvider`), transient network drops, request timeouts, and temporary DNS issues were treated with aggressive defensive actions. A single failed HTTP request due to a network glitch marked the associated API key as exhausted and placed the entire model on a 5-minute cooldown (`cooldown_seconds: 300`). 

When all primary and fallback models encountered transient errors or rate limits concurrently, the entire `ModelPoolProvider` would raise `RateLimitError: All models in pool exhausted` instantly, leading to cascading failures in downstream perception, research, and belief engine processes. We need a more resilient approach that distinguishes transient connection issues from permanent authentication or quota errors.

## Options Considered

### Option A (Silent Individual Retries)
Implement retry logic on network/timeout errors with a brief delay, silently recovering if the retry succeeds.
* *Pros:* Transparent resilience for the user; no noise in logs.
* *Cons:* Cartesian "seamlessness" illusion; masks underlying infrastructure fragility from system monitoring, violating the AAA principle of material traceability.

### Option B (Grace-and-Retry with Material Traces / Glitch Scarring) [Selected]
Introduce a 10-second grace period and single-retry loop when catching connection-level exceptions (`httpx.RequestError`, `TimeoutError`, `asyncio.TimeoutError`). If the retry succeeds, continue without exhausting the key; if it fails, exhaust the key. Expose these transient retries in system warning logs to record the "vitality scars" of the network coupling.
* *Pros:* Compliant with AAA philosophical commitments; prevents premature pool exhaustion; surfaces infrastructural seams as observable traces.
* *Cons:* Retries introduce an intentional 10-second latency spike for transiently failing nodes.

## Decision

We implemented **Option B**:
1. Added explicit catching of `httpx.RequestError`, `TimeoutError`, and `asyncio.TimeoutError` in `ModelPoolProvider.generate()`.
2. When caught, the system pauses execution for `10 seconds` using `await asyncio.sleep(10)` and attempts a single retry on the same model and key.
3. Added warning logs describing the connection failure and the waiting state, which act as the material trace of the perturbation.
4. Unit tests were added to `backend/tests/test_model_pool.py` to ensure that:
   * Successful retries maintain the key's availability.
   * Double failures exhaust the key and trigger rotation as expected.

## Consequences

* **Resilience:** Premature exhaustion of the model pool due to transient network hiccups is eliminated.
* **Traceability:** Rather than hiding connection errors, the warnings clearly mark when the system couples across infrastructural gaps, aligning with our commitment to making the apparatus visible.
* **Latency Profile:** Successful retries incur a 10-second latency cost, which is a conscious trade-off for preserving high-priority model access.
