# Report 035: T64 Evidence Substrate

Date: 2026-10-06. Scope: opt-in storage, provenance, pipeline and export contracts.

## Verification

- Initial evidence tests: 11 passed. Broader evidence/journal/state/phases/import run: 68 passed. Final evidence/receipts/provider limits/provider observations/synthesis/API regression run: 55 passed. Runs overlap; counts are not independent benchmark samples.
- Final evidence tests cover exact Unicode representation offsets; restart and offline exported URI resolution; contrary references; quality/hash/coordinate tampering; immutable version history; unavailable reasons; resolvable quote without semantic promotion; hard rubric/resource revision protection; archived import without execution authority; tampered export rejection; input clamping before allocation; legacy digest objections/exclusions; late decision rejection with retained source; JSON import/re-export origin preservation; parse-to-digest packets; atomic contract/policy initialization rollback.
- Backend lint passes. All 17 changed Python files pass format checks. Strict mypy passes for seven directly checked implementation files. Configured global mypy checks 57 files and retains the known `backend/services/keyed_lock.py:13` missing Task type argument.
- No frontend behavior changed. Earlier repository-wide backend and frontend lint debt remains in [Report 034](../034-research-provider-reliability/README.md); these runs do not establish a green repository-wide suite.

## Corrections during verification

Test fixtures initially omitted required policy version and action budget; cross-task resolution correctly raises rather than returns null. Fixtures corrected; no new runtime invariant needed. Strict typing caught mixed-record inference and a reused optional source variable. Export appendix uses one Markdown string rather than extending its characters.

## Evidence boundary

No live model call required for these deterministic provenance checks. NVIDIA remains the selected provider for live testing/debugging; the prior live transport observation is owned by [Report 034](../034-research-provider-reliability/README.md). No duplicated empirical record or new quality/latency claim.

Legacy parser route and original bytes remain unknown. Legacy learnings are unverified interpretations. Human support judgments, independent annotations, OCR evaluation and release ablations remain subsequent task gates.
