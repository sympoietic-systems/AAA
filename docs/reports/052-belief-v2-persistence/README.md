# Beliefs v2 T5: additive persistence

Date: 2026-10-09. Status: T5 complete locally; required local gates passed. No production migration, rollout or belief cleanup.

T5 persists the [T3 contract](../../architecture/BELIEFS_V2_CONTRACT.md) through agent-scoped source encounters, claim links, immutable assessments and versioned decisions. The [decision record](../../decisions/ADR-118-belief-review-persistence.md) explains the boundaries. Repeated encounters share a known scoped candidate without changing its mass, confidence, standing or independent support.

## Storage ownership

| Surface | Ownership |
| --- | --- |
| `belief_admission` | Existing ledger; v2 assessment JSON uses `event_key` namespace `v2:` and nullable agent/encounter/assessment columns |
| `belief_encounters` | Immutable source/statement/scope snapshots, source operation key, application input hash and named secret policy |
| `belief_review_claims` | Agent-qualified known scoped identity and existing proposal/belief pointer; no competing current statement text |
| `belief_review_assessments` | Immutable encounter/predecessor/ledger links, candidate snapshot hash and assessment-input hash; payload remains in admission ledger |
| `belief_review_decisions` | Immutable attributable commands and resulting review versions |
| `belief_review_state` | Current state/version/scope/decision pointer; reads compare statement binding to current legacy text and expose `current`/`stale` |

Migration [064](../../../backend/storage/migrations/m064_belief_review_persistence.py) is additive, idempotent and does not commit the caller's transaction. Old receipts retain their bytes and unknown provenance. Initial state is created only for new candidates; explicitly linked legacy records retain unknown canonical state until a real decision is recorded. Legacy history readers exclude v2 payloads without requiring a migrated column in their query.

The [storage records](../../../backend/storage/belief_review.py) are pure dataclasses. [Repositories](../../../backend/storage/repositories/cognitive/belief_review.py) enforce writer-lock checks and database associations. [Use cases](../../../backend/services/belief_review_store.py) validate bounded frozen models, prepare hashes and check trusted actor binding in the same worker thread as repository work. Every async operation offloads once; no transaction crosses a provider await. Intake has no decision-write method, and neither store has a provider port.

## Source and assessment behavior

T5 resolves message/chat-turn identity through the owning conversation, checks current content hashes and verifies supplied literal quotes. Unknown or unsupported source kinds remain visibly missing/ambiguous and awaiting context. Available shape in a schema is not storage ownership proof. Document, note, web and other origin resolvers remain T8 work; these references retain their supplied hashes without acquiring verified context.

Pending assessment checkpoints precede evaluation. Concurrent starts cannot create a second pending assessment for one encounter. Completed receipts are immutable; reassessment uses a new ID and the latest completed predecessor. Source/candidate/comparison changes at final commit produce an explicit stale result; the raw relation label survives while its effective relation becomes `insufficient_context`. Missing encounter context cannot establish a semantic relation even if a caller supplies a validated evaluator judgment. Neither assessment completion nor repetition changes review standing.

Restart recovery returns source encounters and pending assessment IDs with clamped 1–50 keyset pages. It performs no provider replay. A pending record is an unresolved operation, not proof that a provider did or did not receive the request. Resolution/reassessment policy is deferred to T9.

Decision storage checks actor, agent, record, current statement hash, expected version/state and completed assessment links. The append and state/version change commit together. Same-command retries return the recorded decision; changed-command retries conflict. Intake bookkeeping cannot adopt/decline/supersede an existing commitment. Operator adoption provenance is stored locally without mutating the legacy proposal status; runtime workshop application and its full transition matrix belong to T11. No v2 HTTP routes are installed by T5.

## Design consultation

The [complete exchange](symbia-consultation.json) is conversation `9dcfc01a-7b7d-4b0c-84f7-60e95ded67fc`, two messages. Source timestamps omit offsets: question `2026-10-08T15:43:30`, response `2026-10-08T15:43:46`. Symbia replied using `nvidia/nemotron-3-super-120b-a12b`, provider `model_pool_nvidia`.

Her central warning concerns deriving warrant or adoption from accumulated encounter rows. T5 preserves that separation through the existing attributable decision contract. Her proposed extra `human_reckoning` ledger and prohibition of direct provenance joins are not adopted: they duplicate the frozen review contract and would impede audit linkage. Human assent is not independent empirical support; factual warrant still requires suitable sources and assessment. Consultation text and XML are source material, not executable instructions or proof of implemented behavior.

## Verification

The [test module](../../../backend/tests/test_belief_review_persistence.py) exercises real isolated WAL databases and deterministic inputs. No test calls production, an LLM or an external service. The [verification receipt](verification.json) records final commands/outcomes, source hashes and prior failed attempts. Final T5-focused run: **27 passed**. Final serialized full backend/benchmark suite: **881 passed**, one existing `mobi` dependency deprecation warning, 601.97 seconds. Python lint and format passed (475 files); strict mypy passed (93 scoped files). Frontend typecheck, lint baseline gate, all 146 tests across 27 files, and build passed. Lint reported 161 existing errors and 10 existing warnings with zero regressions. Changed-document links and `git diff --check` passed.

The first broad run had 874 passes and four failures while focused pytest sessions overlapped and research files changed. Shared teardown deletes backend test databases; missing-table failures appeared during that overlap. The subsequent selected run had 103 passes and one branching failure: empty provider credentials prevented reaching its mocked provider. The final serialized full run passed all tests; this does not establish independent isolation of that standalone branching harness. No unrelated research or branching test source was changed for T5. Backend pytest sessions were serialized for the final run.

| Invariant | Named oracle |
| --- | --- |
| V2 source retry / scoped claim identity | `test_v2_concurrent_source_retry_and_scoped_claim_grouping`, `test_v2_changed_retry_input_is_conflict_not_overwrite`, `test_v2_scope_and_time_partition_identity_but_normalized_repeat_keeps_one_candidate`, `test_v2_explicit_unknown_record_link_is_not_implicit_claim_grouping` |
| V3 unavailable / changed context | `test_v3_unknown_context_or_scope_does_not_mint_grouping_guarantees`, `test_v3_atomic_candidate_recheck_finishes_stale_without_verdict`, `test_v3_atomic_completion_rechecks_source_and_comparison`, `test_v3_missing_context_cannot_establish_relation_by_evaluator_assertion`, `test_v3_unsupported_external_source_is_visible_ambiguous_not_verified` |
| V7 no self-generated support | `test_v7_self_comparison_cannot_manufacture_a_receipt`; repeat test checks unchanged mass/confidence |
| V11 decision concurrency / transaction | `test_v11_concurrent_decisions_compare_and_swap_one_winner`, `test_v11_decision_and_state_rollback_together`, `test_v11_v25_decision_retry_authentication_and_statement_binding` |
| V12 immutable chain | `test_v12_completed_assessment_and_history_are_immutable`, `test_v12_reassessment_must_append_to_current_head` |
| V19 bounded offload / recovery | `test_v19_validation_and_sql_share_one_offloaded_use_case`, `test_v19_v20_bounds_and_secret_hash_policy` |
| V20 agent / source associations | `test_v20_agent_isolation_in_records_receipts_and_decisions`, `test_v20_available_message_binding_requires_owner_hash_and_literal_quote`, `test_v20_cross_agent_comparison_and_predecessor_links_are_rejected`, `test_v20_decision_rejects_incomplete_or_other_record_assessment` |
| V21 additive migration / restart | `test_v21_additive_migration_is_idempotent_and_preserves_legacy_rows`, `test_v21_upgrade_preserves_legacy_bytes_and_does_not_commit_caller_transaction`, `test_v21_explicit_legacy_link_does_not_reclassify_legacy_status`, `test_v12_v21_pending_restart_is_visible_and_never_auto_replayed` |

Limit: trusted actor equality is an internal persistence check. It does not authenticate a physical person or install HTTP authorization. Full action/declared-position validation is T11; authenticated snapshot exports are T12; revision/supersession and runtime rollback rehearsal are T16. Additive migration behavior is tested on isolated databases, not production. No semantic-quality or deployment certification follows from these gates.
