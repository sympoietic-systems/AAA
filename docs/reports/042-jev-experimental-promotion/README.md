# 042 — T69 experimental Jev promotion

Date: 2026-10-06. Classification: provisional-label exploration and explicitly authorized experimental rollout. Implementation branch: `codex/research-v2`; comparison code started from `b74bd8a`.

The user explicitly requested “promote Jev based on the LLM labeled data.” T69 is completed under that bounded exception: the research configuration enables Jev with unchanged confidence guards and a standard-selector fallback for uncertain search decisions. Independent quality certification and downstream release review remain T71.

## Observations

The immutable private run is `benchmarks/runs/research/t69_comparison_20261006/`, with metadata, per-trial telemetry, summary and guard diagnostics. Its input is the T74 packet, SHA-256 `c8c9544ae3f8f7eacf7ec1c404133cebfdf0e7ef6821a2c91b9fba164a87a307`. Source texts and annotations remain in the ignored run directory. Six held-out queries across four task families were tested three times in original/reversed candidate order, giving 54 attempts across three arms. Repeats are not independent samples.

| Arm | Attempts | Valid selections | Other outcomes | Median attempt latency, ms |
| --- | ---: | ---: | --- | ---: |
| Legacy NVIDIA | 18 | 8 | 10 unavailable | 2745.891 |
| Jev combined score | 18 | 0 | 18 abstentions | 1691.514 |
| Jev separate axes | 18 | 0 | 18 abstentions | 1668.091 |

The NVIDIA model was `nvidia/nemotron-3-ultra-550b-a55b`; Jev was the actual configured `typesafe/jev-1.13` endpoint. Legacy failures comprise nine HTTPStatusError receipts and one ReadTimeout. All 36 Jev attempts returned uncertain answers that failed the unchanged 0.7 confidence guard. These latencies include unsuccessful attempts and do not establish a useful-selection speedup.

Legacy's provisional relevance fraction was 1.0 and contrary retention 0.4 among its eight valid selections. Jev's corresponding values are null because it produced no accepted selection. These are agreement measures against provisional labels, not accuracy. The NVIDIA baseline model also supplied part of the annotation packet, creating model dependence. The remaining annotations explicitly identify the main Codex agent. Neither group is independent human gold. Monetary cost and independent quality remain unknown; downstream support review was not run.

## Decision and controls

The empirical runner retains its original `promotion: BLOCKED` output and strict independent-gold tooling remains unchanged. The later user authorization is a separate policy exception. Activation does not claim Jev outperformed the baseline. Current observations predict frequent use of the standard selector after Jev abstains, with additional request latency.

Search now preserves the original Jev receipt and records separate standard-fallback IDs. Accepted Jev selections bypass the standard selector. Disabling `research_triage.enabled` restores the existing standard route. No confidence threshold was lowered and no held-out answer was used to tune the guard. See [operating instructions](../../guides/RESEARCH_JEV.md).

## Verification

Focused verification covers exploratory trial accounting, held-out filtering, checkpointing, provisional-label completeness, exclusion of failed/fallback trials, triage confidence guards and search fallback receipt separation. The focused suite passed 46 tests covering evidence/belief triage, exploratory comparison, calibration and labeling. Ruff lint and format checks passed for all four changed Python files. The checked YAML enables the route; toggling it off constructs no triage instance. `git diff --check` passed. An initial test run passed 24 tests but hit a Windows temporary-directory permission error for one fixture; rerunning with a fresh workspace basetemp passed. Repository-wide checks were not repeated for this scoped change; existing global limitations remain recorded in Report 040. Generated verification artifacts remain outside the commit after an earlier cleanup action was blocked by policy.

## Subsequent disposition — 2026-10-06

After reviewing the abstentions, the user instructed: “mark it and so not use Jev for this task.” The experimental activation described above was withdrawn. `research_triage.enabled` is false; orchestrator research selection uses the standard selector without a Jev call. T69 remains complete with a non-adoption decision for the evaluated setup. This does not establish that Jev is unsuitable for every decision task; the observed limitation concerns this prompt, candidate representation and confidence guard. Historical comparison receipts and the earlier rollout record remain unchanged.

Withdrawal verification: repository YAML parses with triage disabled, configuration constructs no Jev triage instance, 11 focused evidence-triage tests pass, and git diff whitespace checks pass.
