# Beliefs v2 T4: automated provisional review

Date: 2026-10-08. Scope: offline review of the saved [54-case source packet](../049-belief-v2-review-corpus/review-packet.json). Provider review runs are declared separately from deterministic tests. No production belief mutations, migration or deployment.

The user requested automation because the manual packet was too large. The [runner](../../../benchmarks/suites/belief_auto_review.py) obtains two blind, separately prompted reviews from distinct model families. It retains missing context, raw judgments, bounded source citations, consequence/challenge/lineage reasoning, returned model identity and source-family overlap. It never represents the reviewers as humans or declares unknown author independence verified.

Automated freezing is a separate path from the existing human-reviewed gold gate. It produces `MODEL_REVIEWED_PROVISIONAL`, `independent_gold=false`, `adoption_authority=none`, and `promotion=BLOCKED`. A model-agreement count is a workload statistic, not an accuracy score. Deterministic gates project unavailable pair context or missing/one-sided citations to `insufficient_context`; raw opinions remain inspectable. Contradiction, useful questions and dissent do not grant mutation authority.

## Design consultation

The [complete saved exchange](symbia-consultation.json) is conversation `afd7db28-29fc-4502-9503-c5a976d5ca2a`. Symbia answered using `nvidia/nemotron-3-ultra-550b-a55b`, provider `model_pool_nvidia`. Source timestamps omit offsets: question `2026-10-08T07:57:32`, reply `2026-10-08T07:59:07`.

Her central warning is that model consensus can look like earned warrant. The runner therefore has no production mutation ports, and its frozen artifact cannot acquire gold or adoption authority. Her proposal of 54 human reckoning events would retain the rejected workload; it is not required to prepare this provisional corpus. Her 90-day expiry is uncalibrated, and banning provenance joins would obstruct the existing source-bound design. These suggestions are recorded rather than adopted. Operator commitment remains a separate attributable decision under [ADR-116](../../decisions/ADR-116-belief-review-standing-contract.md).

## Bounds and reproduction

Four workers maximum, two reviewer slots, at most 100 cases (54 here), 1,600 completion tokens per call, 60-second provider timeout and 75-second outer bound. Provider retries are disabled. A rate limit/unavailable route opens a reviewer circuit; three failed or uncertain attempts also exhaust that reviewer's failure budget. Circuits are restored before resume/reuse. Resume validates policy/model/prompt/source identity and never replays an existing completed, failed or outcome-unknown call. Replacement models are explicitly requested. Exact peer receipts can be reused by reference without copying or repeating calls. Each prompt selects at most four 2,500-character excerpts using a fixed lexical rule. This is a limited context window; it is not a full reading of every recovered conversation.

```powershell
uv run python -m benchmarks.suites.belief_auto_review --packet docs/reports/049-belief-v2-review-corpus/review-packet.json --output benchmarks/runs/belief-auto-review/2026-10-08-t4-v4 --model nvidia_router/nvidia/nemotron-3-super-120b-a12b --model google/gemini-3.8-flash --reuse-from benchmarks/runs/belief-auto-review/2026-10-08-t4-v2/receipts --workers 4
```

Run receipts are owned by `benchmarks/runs/belief-auto-review/`; this report links to them rather than cloning the original source packet. Running the command again reuses recorded outcomes; it does not retry the failed, uncertain or skipped reviewer jobs.

## Observed results

The [automated results page](../../../benchmarks/runs/belief-auto-review/2026-10-08-t4-v4/review.html) replaces the manual annotation workflow with nine source-family summaries and expandable attributed reasoning. There is no mandatory human checklist. The [frozen provisional artifact](../../../benchmarks/runs/belief-auto-review/2026-10-08-t4-v4/frozen-provisional.json) accounts for every case and both reviewer slots; it does not claim every slot received a usable response.

| Quantity | Observed result |
| --- | ---: |
| Source-bound cases / reviewer slots | 54 / 108 |
| Valid reviews | 80: 53 Gemini, 27 NVIDIA Super |
| Cases with two valid reviews | 26 |
| Cases with reviewer disagreement | 23 |
| Cases with model agreement | 3 |
| Cases with incomplete reviewer coverage | 28 |
| Invalid NVIDIA source citations | 3 |
| Remaining NVIDIA slots stopped by circuit | 24 |
| Preserved Gemini outcome-unknown call | 1 |

Among the 80 valid reviews, effective relations are 67 `insufficient_context`, seven `no_comparison`, three `extension` and three `distinct`. These are attributed review outcomes, not correctness measurements. Agreement includes agreement about uncertainty. Disagreement compares relation, warrant and recommendation; it does not necessarily establish a substantive contradiction. The [machine-readable summary and failure groups](verification.json) retain source bindings, partition coverage and family outcomes.

The initial [Qwen/Gemini preflight](../../../benchmarks/runs/belief-auto-review/2026-10-08-t4-v1/summary.json) yielded Qwen rate limiting from an upstream shared pool. The [DeepSeek/Gemini run](../../../benchmarks/runs/belief-auto-review/2026-10-08-t4-v2/summary.json) retained schema failures, empty truncated completions and timeouts. Its process was stopped after repeated degradation, leaving two checkpointed unknown outcomes; neither was replayed. The new failure circuit was then applied during resume. The [NVIDIA Ultra preflight](../../../benchmarks/runs/belief-auto-review/2026-10-08-t4-v3/summary.json) returned HTTP 503. NVIDIA's authenticated model listing returned HTTP 200 and listed both Ultra and Super; this establishes listing availability, not successful inference. The Super preflight returned a valid review before the replacement run.

Three Super replies cited `a`/`b` instead of supplied message IDs. The guard rejected these replies and the cumulative three-failure circuit stopped further NVIDIA jobs. This intentionally conservative resource budget leaves 24 slots unattempted; they are recorded as `provider_unavailable`, not as completed provider judgments. One interrupted Gemini slot remains unknown. Failure counters are engineering resource bounds, not calibrated semantic acceptance thresholds.

## Completion and limits

T4's revised provisional preparation path is complete: saved sources, disjoint partitions, automated attributed outcomes and validated freeze are available. Live reviewer coverage is partial. The former 54-case human annotation requirement is superseded for this path by [ADR-117](../../decisions/ADR-117-provisional-automated-belief-review.md). Independent gold, acceptance thresholds, usefulness and accuracy remain T15 obligations. No provisional artifact authorizes adoption, merging, rejection or production rollout.

The existing source-recovery gaps remain the main limit: only seven cases had context available on both sides in the recovered packet. Lexical excerpt selection can omit later relevant passages, and legacy author independence remains unknown. Future evaluation should improve source recovery and citation fidelity before interpreting agreement or queue reduction as success. Disagreements stay recoverable for targeted evaluation; they do not recreate a mandatory 54-case manual workload.

Verification: 88 deterministic benchmark tests passed; backend plus changed benchmark lint/format passed; strict mypy passed on 89 scoped source files. Frozen-artifact binding, inert HTML rendering, exact peer reuse, circuit restoration and no-replay behavior are covered. Full runtime backend/frontend integration and production behavior were not exercised by this offline benchmark change. Unrelated concurrent research edits were preserved.
