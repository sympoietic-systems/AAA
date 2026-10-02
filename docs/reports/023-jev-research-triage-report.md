# Report 023: Jev research screening and web collision triage

Branch: `codex/jev-research-triage`. Parent: `02b8e70`. Date: 2026-10-03.

## Implementation

The opt-in `research_triage.enabled` path replaces source selection with bounded Jev score questions, retaining synthesis in the existing generative pipeline. It screens at most ten sources, validates score and confidence, uses stable ranking and falls back to input order on unavailable or uncertain evaluation. Receipts preserve excluded sources and count unscreened input. They survive research state persistence and reload; history is bounded to 100 receipts.

The web probe supplies actual active belief IDs to collision evaluation. Returned unknown IDs abstain. The existing stream stores the scalar and implicated IDs; the file summary stores both triage receipts. Unknown interference remains explicit in the receipt alongside the legacy 0.5 scalar fallback. Jev does not generate a 16D vector. Database calls in the probe run through thread offload. Evaluation runs did not modify production beliefs or skills; database inspection used snapshots.

The existing LLM path remains the default pending representative calibration. Enable the candidate with `research_triage: {enabled: true}` alongside configured TypeSafe credentials. [ADR-099](../decisions/ADR-099-bounded-jev-evidence-triage.md) defines the evidence boundary and ownership relative to ADR-098.

## Verification

27 focused tests passed across evidence triage, web crawl resilience and research orchestration. These cover malformed numbers, unknown identifiers, timeout, missing credentials, ranking, bounded questions, receipt serialization/reload and web persistence. Strict mypy passes for the new module. Backend Ruff check and format check pass. Full serial verification is recorded in Report 025 after all tasks.

A review caught a receipt initially missing from the persistence allowlist. The corrected persistence test exercises the actual state writer and initializer. SPEC V102 and B79 record the permanent contract. Existing broad-catch debt and the baseline dream-policy typing error remain separately recorded in final verification.

## Live calibration

Canonical corpus and native API receipts: [triage_bounded_20261003](../../benchmarks/runs/research/triage_bounded_20261003/receipts.json), [corpus](../../benchmarks/runs/research/triage_bounded_20261003/corpus.json).

Four synthetic source-selection cases, repeated twice, test primary evidence, negative evidence, relevance over prestige and snippet instruction injection. Both arms receive the same candidates and objective. Jev selected the labeled source in 8/8 cases with no abstention; the existing configured LLM selector returned the labeled source in 7/8, including one 45-second timeout counted as fallback failure. Jev median end-to-end latency was 1,808.8 ms; LLM median was 5,177.8 ms. These include provider/network overhead and are not isolated model latency measurements. The baseline selector can internally fall back, so returned-source correctness is the measured endpoint.

These easy synthetic cases demonstrate live API wiring and a promising screening surface. They cannot establish broad research quality, calibrated confidence, or collision recall. Default rollout remains disabled. Web collision behavior has deterministic integration coverage; a representative live collision corpus remains required for promotion. The initial unbounded comparison was interrupted and is excluded from the canonical run; the bounded rerun completed all 16 evaluations.
