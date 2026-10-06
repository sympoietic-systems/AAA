# ADR 108: Bounded Research Acquisition

Date: 2026-10-06. Status: accepted for opt-in implementation.

Policy v4 freezes acquisition limits alongside the research contract. Defaults: task concurrency 4, provider concurrency 2, DuckDuckGo cadence 1.5 seconds, Jina cadence 3 seconds, other-provider cadence 0.1 seconds, request timeout 30 seconds and cache TTL 300 seconds. Application ceilings: 8 acquisition calls, 4 calls per provider and 2 physical extraction threads; pending queues and cache entries/characters are bounded. Different frozen policies share these ceilings and provider rate clocks.

Reuse an application-owned HTTPX client; close it during shutdown. Stream bounded responses, validate each redirect hop, strip sensitive credentials on cross-origin GET redirects and reject POST redirects that would replay a body. [HTTPX async documentation](https://www.python-httpx.org/async/) describes scoped client reuse and response closure.

Persist pending acquisition intent before work. Persist observation and source binding before publishing a reusable cache entry. A cache hit records an access receipt referencing the immutable fetched origin; it has no new provider invocation. Preserve observedAt separately from accessedAt, expiry, provider lineage, parser configuration and source version. Revalidate URLs even on hits. TTL eligibility and DNS checks do not warrant current semantic claims. A failed current fetch does not erase prior historical evidence.

Cancellation-resistant work retains its semaphore until actual exit. Late content cannot publish or overwrite a terminal receipt. Physical CPU work remains tracked after caller cancellation; bounded shutdown cannot forcibly terminate Python threads. Action termination closes pending receipts and exposes partial status. Legacy frozen policies retain prior behavior.

Symbia consultation: codex conversation `abac9620-6f4c-47dd-b931-686838510f08`; observation/access separation and historical/current distinction retained. Deterministic verification and measured fixture results: [Report 036](../reports/036-research-acquisition/README.md). No independent semantic-quality or live-provider performance claim.
