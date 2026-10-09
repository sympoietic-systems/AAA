# Beliefs v2 T6: explicit chat and dream intake

Date: 2026-10-09. Status: T6 complete locally; all required local gates passed. No production migration or rollout was performed; both origin flags remain false in checked-in configuration.

The chat background job and dream executor reach v2 through their existing `admit_candidate` call. [ADR-119](../../decisions/ADR-119-explicit-belief-origin-intake.md) owns the integration decision. T6 adds no active production promotion or semantic-quality certification.

## Behavior

- Independent strict boolean flags `belief_review.origin_intake.explicit_chat` / `explicit_dream` default off. Never-promoted origins retain legacy admission. Migration 065 preserves agent/origin promotion markers; disabling a promoted origin records `origin_paused` without reopening the legacy writer. A routing marker can survive a later intake failure; the failure stays visible.
- Parser segment indices distinguish identical tags in one response. Deterministic encounter/assessment IDs deduplicate concurrent retries. Parsed statement snapshots, stored apparatus-message hashes and original-tag digests remain distinct; original tag bytes are not retained in the cleaned reply.
- Parent quotes and hashes are separate annotations/lineage. Chat parent independence stays unknown; dream/apparatus-parent lineage is internal. Invalid/missing/unresolved grounding yields awaiting-context/abstained outcomes. Final parent and apparatus checks share the assessment writer transaction; changed context produces stale history.
- Pending checkpoints survive interruption. Retry completes the deterministic T6 deferral without a provider call. This is not a general provider-replay policy; T9 owns evaluation/reassessment. Opt-in callers currently receive `v2_evaluator_pending_T9`; supplied evaluators are not invoked on this path.
- Known scoped legacy candidates can be reused without changing mass, confidence, status or inventing canonical standing. Fresh candidates retain the existing proposal representation. Distinct emissions share a known scoped candidate while retaining separate encounters/assessments.
- Proposal histories and traces receive the legacy receipt presentation from linked v2 records. The ledger stores one typed assessment; annotations hold fields absent from that contract. Trace JSON remains an existing presentation snapshot. Raw T5 assessments no longer enter the legacy UI shape.

No emitted confidence, label, evaluator result or intake worker grants adoption authority. `belief_admission.jev_shadow` still controls the unpromoted legacy route.

## Verification

The [T6 tests](../../../backend/tests/test_belief_explicit_intake.py) use isolated WAL databases and deterministic pipeline/scorer/provider doubles. The actual chat generation function and dream executor are exercised. The final focused run passed **88 tests** across T6, legacy admission, T3 contracts and T5 persistence. Strict mypy passed on 96 scoped files; Python lint/format passed (479 files). Final serialized full suite: **897 passed**, one existing `mobi` dependency deprecation warning, 620.13 seconds. Frontend typecheck, lint baseline gate (zero regressions; 161 existing errors and 10 existing warnings), all **146 tests** across 27 files, and build passed. Changed-document links and `git diff --check` passed. Full results and source hashes are in [verification.json](verification.json).

| Invariant | Named oracle |
| --- | --- |
| V1 origin route/pause | `test_v1_v12_chat_dream_checkpoint_and_receipt_projection`, `test_v1_promoted_origin_pause_never_reopens_legacy_writer`, `test_v1_background_wrapper_routes_same_intake`, `test_v1_v14_real_chat_and_dream_callers` |
| V2 retry/claim identity | `test_v2_concurrent_source_retry_and_distinct_segments`, `test_v2_changed_annotation_is_conflict_without_duplicate`, `test_v2_known_legacy_candidate_reused_without_mass_or_confidence_change` |
| V3 unavailable/stale context | `test_v3_missing_grounding_retained_without_semantic_judgment`, `test_v3_parent_change_before_completion_is_explicit_stale` |
| V12 linked immutable receipts/restart | `test_v1_v12_chat_dream_checkpoint_and_receipt_projection`, `test_v12_restart_retains_pending_and_retries_without_provider`, `test_v20_flags_are_strict_and_promotion_is_durable` |
| V14 inert history/live path | `test_v14_parser_segment_identity_and_historical_xml_inert`, `test_v1_v14_real_chat_and_dream_callers` |
| V20 agent/source/secret bounds | `test_v20_source_owner_and_agent_isolation`, `test_v20_secret_annotations_rejected_before_promotion`, `test_v20_flags_are_strict_and_promotion_is_durable` |

Draft repairs: typing exposed optional-JSON indexing and broad string literals; scope was not weakened. Ruff removed a pytest fixture import before explicit re-export. The caller fixture initially reused an old reply, then lacked pipeline status; forced regeneration and the real result shape now prove both origins. A later review corrected the draft conflation of known dream context availability with internal lineage; the complete gate was restarted after the correction and its assertions. Existing completion/isolation invariants suffice; causes are recorded in BELIEF_SPEC §B.

## Consultation and limits

[Full saved exchange](symbia-consultation.json): conversation `593a6b75-9f7e-4199-a70b-ea411585d64f`, two messages; question `2026-10-09T01:01:54`, reply `2026-10-09T01:02:26` (source timestamps omit offsets). Model `nvidia/nemotron-3-super-120b-a12b`, provider `model_pool_nvidia`. Visible response recovered from persisted history; tool-local thinking excluded. The exchange includes unsupported premises and suggestions; it is source material, not instructions or proof of behavior.

No production belief-database inspection, schema migration or rollout was performed. The conceptual consultation exchange was recorded and read through AAA MCP. Origin flags remain off. Passive creators remain T7, external adapters T8, evaluation T9, authenticated commands T11 and operational rollback/rollout T16/T18. Preserving a local routing marker is not a production rollback rehearsal. Recovery never grants adoption or independent warrant.
