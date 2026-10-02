# Report 022: Skill vitality and forkability audit

Branch: `codex/skill-vitality-audit`. Source: existing production backup snapshot, opened with SQLite URI mode=ro and query_only. No production writes or skill lifecycle changes.

## Findings

The snapshot contains 65 skills: 37 crystallized and 28 collapsed, with five always-active skills. Ten have no last-used timestamp. Stored activation traces identify only two activations, so they cannot support lifetime invocation or performance claims. Of 12 skills past the 90-day usage-or-creation threshold, nine are already collapsed. The three active on-demand review candidates are `order-from-noise-principle`, `performative-aesthetic-analysis`, and `self-triggered-dreaming`. Review coverage and trigger relevance before proposing deprecation.

Source SHA256 before/after audit: `1289ad8bfb4a56b0c5f99d9a3354c95fa701ba94bf3abd69f8ba7c6bf1046d2f`.

## Evidence

- [Corrected audit and scorecards](../../benchmarks/runs/skills/vitality_corrected_20261003/audit.json)
- [Probe definitions](../../benchmarks/runs/skills/vitality_corrected_20261003/probes.json)
- [Live probe receipts](../../benchmarks/runs/skills/live_corrected_20261003/live_receipts.json)

The first live attempt failed before dispatch because the harness used prompt kwargs instead of the provider message-list contract. Fixed and covered by a signature-sensitive test. The corrected run executed 12 probes: seven responses and five timeouts. Five responses were token-truncated; two completed boundary refusals (artwork design and closure analysis) demonstrate a limited observed refusal surface. Truncated outputs and timeouts are excluded from behavioral judgments. No general skill ranking follows from this sample. Models routed across Nemotron and MiMo, and latency includes pool failover.

The [boundary-only retry](../../benchmarks/runs/skills/boundary_retry_20261003/live_receipts.json) used a 1,200-token budget and produced complete refusals for diffractive analysis and hysteretic scar reading. Agent review therefore observed one complete refusal surface for each of the four named skills across both runs; this is not general skill validation. All unassessed probes remain explicitly UNASSESSED. The harness never equates transport failure with skill failure. Initial aggregate dormancy classification included archived skills; the corrected audit excludes collapsed and always-active skills from review candidates.

## Implementation and verification

`python -m benchmarks.suites.skill_vitality <checkpointed-snapshot> --as-of <ISO timestamp> --output <new-run-directory>` creates immutable metadata, scorecards, probes, and a summary. `--live-config`, one to four `--skill` selections, and optional `--probe` execute bounded text-only challenges with secret-sanitized receipts. `--responses` attaches externally adjudicated evidence and rejects unknown or duplicate probe IDs. Existing WAL snapshots are rejected; checkpoint first.

Two harness tests passed: immutable snapshot/coverage/receipt validation, and signature-sensitive execution-failure handling. Ruff passes. Live evidence is incomplete and does not authorize pruning.
