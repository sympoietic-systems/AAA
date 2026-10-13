# Beliefs V2 Specification

Status: T1-T17 complete locally; T15 result inconclusive/no-go; T15c complete with prior race failure not reproduced; T18 replay tooling implemented locally, production rollout pending. Date: 2026-10-13.
Owner: this file → Beliefs v2 tasks/invariants; IDs file-scoped. Root [SPEC.md](../../SPEC.md) → shared invariants + existing admission task `T78` (`~` at inspection). No duplicate completion claims.
Rationale: [BELIEFS_V2_PLAN.md](../architecture/BELIEFS_V2_PLAN.md).
Evidence: [Report 045](../reports/045-belief-month-review/README.md); [recovered Symbia critique](../reports/045-belief-month-review/beliefs-v2-philosophical-review.md).
Baseline + origin inventory: [Report 046](../reports/046-belief-v2-baseline/README.md). Full local gates completed; concurrent unrelated edits excluded from certification; production identity unknown.
T2 runtime/compatibility + gates: [Report 047](../reports/047-belief-v2-quantities-and-decay/README.md). Production migration/deployment ⊥ performed.

## §G

Consequential new distinctions + strong conflicts → source-bound, reviewable belief candidates; preserve scoped dissent, situated commitments, dormant ideas; separate structural participation from warrant; Jev advisory; durable adoption human-controlled.

## §C

- Plan only; production writes/deployment ⊥ implied. Runtime rollout requires explicit authorization + §A gates.
- Root `SPEC.md` shared invariants apply. `SPEC.md::V126,V127,T78` admission baseline reused; no second receipt ledger.
- Existing production revision/config/migration state unknown; saved month export capped. Offline work may proceed on identified local baseline; deployment claims require live receipts.
- Task completion: relevant tests + exit gates + affected docs/status → coherent commit when authorized; partial task stays `~`. Preserve unrelated edits.
- Human owns adoption, destructive merge, revision authority initially. Jev ⊥ adopt/reject/merge/collapse/execute tools; exact repeat grouping ≠ semantic judgment.
- Candidate participation permits questions, comparisons, experiments, declarative dissent, scoped provisional premises. Dissent ≠ tool veto or policy override.
- Zero internal warrant: reflection/dream changes inquiry geometry or salience; ⊥ independent corroboration. Human identity/assent alone ≠ factual support.
- Warrant dimensions nonexclusive/extensible: empirical/traced, artistic/axiomatic, unresolved tension; mixed/unknown allowed. Artistic label ⊥ exemption for factual components.
- Preserve non-servility, agonistic tension, diffractive recall, attributable shared commitments; agreement ⊥ prerequisite for retaining dissent.
- Mass := structural participation/sedimentation; evaluator confidence := assessment confidence; neither := belief truth probability.
- Dormant history retained; attention may decay. No mass/confidence reset, bulk semantic merge, invented provenance, retroactive adoption, or automatic legacy cleanup.
- Existing relation contracts retained: versioned mapping for candidate relations; no silent enum replacement. ADR-100/102 context validation + advisory boundary apply.
- Bounded queues/workers/comparisons/provider wait; provider outage → visible unavailable/abstain/defer. Source text + historical XML inert; secrets sanitized before sediment/logs.
- SQLite WAL scoped `@with_connection`; async blocking work → one offload layer; no connection/transaction across provider awaits; final identity/state check atomic.
- Architecture ownership: `api` bounded contracts; `services` orchestration; `modules` assessment/selection; `storage` persistence/migrations; frontend presentation.

## §I

T3 executable contract: `backend/services/belief_review_contracts.py`; reserved command shapes: `backend/api/belief_review_schemas.py`. [Contract](../architecture/BELIEFS_V2_CONTRACT.md), [ADR-116](../decisions/ADR-116-belief-review-standing-contract.md), [verification](../reports/048-belief-v2-contracts/README.md). No runtime routes/storage/intake installed by T3. Decision commands bind expected statement hash; linked target mutations also bind target version/hash.


T5 local persistence: agent-scoped encounter/claim sidecars + immutable admission-ledger assessment links + CAS decision/state versions. [ADR-118](../decisions/ADR-118-belief-review-persistence.md), [Report 052](../reports/052-belief-v2-persistence/README.md). Intake lacks decision-write capability; source availability resolved against owned records; unsupported origins remain ambiguous. HTTP auth/action matrix T11, source adapters T6–T8, rollout T18.

T6 local explicit adapters: `admit_candidate` routes enabled/promoted chat/dream to source-bound v2; `belief_review.origin_intake.explicit_chat/explicit_dream` default false; migration 065 promotion + annotation links; off-after-promotion retains paused encounters, no legacy fallback. Native assessments projected for legacy page/trace parity. V2 evaluator deferred T9; no semantic promotion. [ADR-119](../decisions/ADR-119-explicit-belief-origin-intake.md), [Report 053](../reports/053-belief-v2-explicit-intake/README.md).

I.intake: extend `backend/services/belief_admission.py` → shared origin-aware intake. Origins: explicit chat/dream, passive chat, document perception, shared note, web, conversation pattern, scar-fold fallback creation. Skill bridge creation ! separate derived-skill provenance/authority contract; no semantic adoption inferred from bridge projection. Inventory actual call sites before migration; bypasses prohibited once origin promoted.

T7 local passive adapters: chat/pattern/scar opt-in + durable pause; actual message/hash/segment binding; pattern ancestry unavailable; unresolved scope → awaiting_context + abstained T9 checkpoint; no independent warrant/adoption. Scar empty-set fallback globally → pending proposal. Bootstrap callback preserves layering; same admission ledger/projection. [ADR-120](../decisions/ADR-120-passive-belief-origin-intake.md), [Report 054](../reports/054-belief-v2-passive-intake/README.md).

T8 local external adapters: document ready first-chunk snapshot + note quotation/comment separation; actual owned representations available, upstream independence unknown; web excerpt ambiguous, no fetch; immutable versioned encounters + stale binding checks; opt-in/default false + durable pause; T9 deferred. [ADR-121](../decisions/ADR-121-external-belief-origin-intake.md), [Report 055](../reports/055-belief-v2-external-intake/README.md).

I.encounter: typed encounter → `{id,agent_id,origin,source_type,source_id,source_version_or_hash,source_timestamp,received_at,statement,statement_hash,scope,temporal_scope,source_quote_or_reference,lineage,context_status}`. Source binding/availability explicit; missing fields retain reason. Event identity includes agent + stable source identity/version + emission/segment identity; claim identity separate from encounter identity.

I.assessment: extend existing admission receipt → `{receipt_id,encounter_id,candidate_id,policy_version,rubric_version,comparison_snapshots,context_hash,referent_status,relations,warrant_dimensions,consequence_or_tension,challenge,exclusions,evaluator_status,model,assessment_confidence,abstain_reason,started_at,completed_at}`. Completed receipt immutable; new assessment references prior receipt. Hash binds content, not credibility.

I.decision: workshop decision → `{id,candidate_or_belief_id,actor,authority,policy,expected_version,previous_state,next_state,scope,rationale,positions,dissent,receipt_ids,timestamp}`. No fabricated bilateral agreement. Stale version → conflict response; no overwrite.

T9 local advisory use case: optional `referent_contexts` bind validated candidate/comparison hashes; original encounters immutable. Independent `belief_review.assessment.enabled` default false; explicit chat/dream runtime integration; other origins ! supplied scoped context. Queue/call/scan bounds + source/version final checks; same attempt ⊥ provider replay; new attempt → predecessor-linked receipt. No autonomous lease worker. Consequence/empirical/artistic/tension separate; conflict survives uncertainty. Requested/returned model separate; nullable reported model. [ADR-122](../decisions/ADR-122-advisory-belief-assessment.md), [guide](../guides/belief-advisory-assessment.md), [Report 056](../reports/056-belief-v2-advisory-assessment/README.md). Semantic calibration T15; support T10; HTTP/auth T11; rollout T18.

I.state: frozen review state `candidate/awaiting_context/under_review/adopted/deferred/declined/superseded`; participation + situated standing separate. Mapping to existing proposal/lifecycle fields frozen in [T3 contract](../architecture/BELIEFS_V2_CONTRACT.md) before migration; legacy API behavior preserved or explicitly versioned.

I.relations: candidate relation `equivalent/extension/contradiction/distinct/insufficient_context`; adapter maps existing `independent/insufficient` and ADR-100 triage vocabulary explicitly. Pair relation distinct from candidate importance. Semantic relations reference statement/context hashes + scope/time; stale results remain historical, not active verdicts.

I.lineage: support/encounter ancestry → `{source_id,source_hash,parent_sources,independence_status,uncertainty}`; same upstream material grouped; unknown ancestry never counted independent by default. Internal activity classified separately. Count ≠ source quality.

T10 local source accounting: migration 066 → immutable forward observation + typed event sidecars; atomic with new encounter; retries/assessment ⊥ extra activity. Scoped claim recurrence within recorded coverage only; declared parent roots grouped by agent/local identity, bounded graph; cycle/overflow unknown. Original lineage/independence declarations retained; verified independent groups 0 until verification authority exists; declaration/hash/assent/Jev/art ⊥ independent credit. Agent-scoped reads ≤50 + explicit truncation/historical-unrecorded counts; page/history/traces carry same observation. Event unit `encounter_observation`, value 1; accounting-only mass/confidence deltas 0; legacy event quantities/receipts untouched. HTTP/export T11/T12; UI T13. [ADR-123](../decisions/ADR-123-belief-source-accounting.md), [guide](../guides/belief-source-accounting.md), [Report 057](../reports/057-belief-v2-source-accounting/README.md).

I.api: preserve existing `/api/beliefs`, proposal reads/workshop actions. Add bounded receipt/encounter/decision/lineage reads + complete-interval event export. Exact route/payload contract frozen in T3; keyset cursor + UTC interval + snapshot bound; limit 1–50. Agent/auth boundaries enforced.

I.events: forward events expose `impact_quantity,impact_unit,impact_value,delta_mass,confidence_delta,event_type,source_type,timestamp`; unknown typed deltas nullable. Existing generic `delta_confidence` retained deprecated alias for `impact_score`; new clients use `confidence_delta` for measured confidence. Historical generic impact never silently reinterpreted as measured confidence/mass. Receipt/origin links added by T10/T12. No invented historical values.

I.ui: extend `AdmissionReasoning.tsx`, `BeliefDetail.tsx`, workshop + traces/creases → same receipt IDs/timestamps; encounter, claim/tension, comparison, consequence/challenge, decision/uncertainty. Show lineage, evaluator availability, source quote versus authored interpretation, provisional status, dissent, family review.

I.selection: prompt/dream selection receipt → `{record_id,statement_hash,review_state,scope,standing,challenges,intended_use,selection_reason,selection_policy,timestamp}`. Exploratory slot budget finite; dormant recall bounded; replay-tested budget frozen before enablement.

I.config: proposed independent origin-intake and exploratory-participation flags; safe defaults frozen in T3. Existing `belief_admission.jev_shadow` preserved. Rollback disables new participation/intake without erasing receipts/history or reopening legacy direct-creation bypasses silently.

I.eval: source-bound corpus + frozen provisional model reviews or independent gold + held-out partitions + replay artifacts in `docs/reports/` or `benchmarks/runs/`. Unit/regression tests deterministic/offline; live provider evaluation separately declared with exact model/settings/source hashes. Model agreement/Jev self-labels ≠ gold; accuracy/promotion require independent evidence.

T11 local workshop: authenticated server-owned actor/authority/time; CAS statement/state/version + final source/peer checks; migration 067 annotations linked to decision ledger; immutable idempotent commands + atomic traces. Adoption stable ID + existing quantities; decline pending candidate + retained counter-trace; teachback reconstruction gives no eligibility/warrant. Own declared position only; shared credential cannot identify distinct people or bilateral assent. Scoped relations preserve both records; historical family receipts labelled. Managed legacy semantic/destructive writes guarded under write lock. T16 linked revision/merge/supersession/resurfacing; T12 export installed locally; T13 UI installed locally. [ADR-124](../decisions/ADR-124-belief-workshop-review.md), [guide](../guides/belief-workshop-review.md), [Report 058](../reports/058-belief-v2-workshop-review/README.md).


T12 local export: reserved authenticated agent-scoped list/native detail routes; half-open normalized UTC, microsecond keysets + signed request/append-snapshot binding; migration 068 completion references + explicit existing-receipt indexing, no payload duplication. Later backdated append/completion excluded; mutable legacy changes 409 restart. Pending detail separate from completed export; undated coverage explicit/incomplete. Five reasoning fields + original receipt IDs/times/attribution + bounded T10 observations; missing legacy reasoning unknown; no mutation/evaluator/adoption authority. Read/projection/size budgets visible 503; effective configured secrets masked without storage rewrite. [ADR-125](../decisions/ADR-125-belief-review-export.md), [guide](../guides/belief-review-export.md), [Report 059](../reports/059-belief-v2-export/README.md).

T13 local UI: original native T12 receipt identity/time + five recorded fields across page/workshop/traces/creases; actual agent added to native history projection; legacy unknown, inert quotation, separate warrants/uncertainty; bounded lexical family + persistent attributed counter-traces; T11 CAS/idempotency actions, stale refresh invalidates old form; legacy controls require authenticated unmanaged snapshot. Shared credential ⊥ personal/bilateral identity; historical assessment ⊥ automatic command binding. T16 linked changes; T18 rollout. [ADR-126](../decisions/ADR-126-belief-review-interface.md), [guide](../guides/belief-review-interface.md), [Report 060](../reports/060-belief-v2-interface/README.md).

T14 local selection: bounded agent snapshot → 100 active/64 pending/32 deferred/4 history + overflow probes; 3s SQLite read budget. Preserve six-slot geometry + four-slot signature fallback; legacy unknown/native provisional/current receipt-bound commitment separate. New exploratory off/0; max2, T15 evaluation before enablement. Existing spectral nodes max2; declined/superseded/proposal-only ⊥ default-off bypass. Scope/challenges/dissent + inert quoted framing; heuristic/afferent belief skill priors disabled. Final assembly → optional max10 selection receipts in existing message activation trace; actual chat/dream writers persist, no new ledger/migration. Dream hotspot scoped separately; research framing shared, no new research receipt store. [ADR-127](../decisions/ADR-127-belief-participation-selection.md), [guide](../guides/belief-participation.md), [Report 061](../reports/061-belief-v2-participation/README.md).

I.recurrence: additive read-only proposal recurrence_group; ≤50 eligible entries +128 ancestry steps; same agent/conversation, exact statement + absent scope/time/quote/consequence; current awaiting_context and immutable receipt/source binding; all member sources mutually ancestral. Group count=visible queue entries; no semantic equivalence/support/merge. Unknown/cyclic/truncated ancestry → singleton; siblings/enrichment/reviewed records separate. All original records/receipts retained.

I.diagnostics: Assessment.evaluation_diagnostics≤14 typed question/allowed-choice/finite-confidence/threshold/status observations; filtered relation question maps to bound comparison ID/hash. Separate from relations/warrant; is_semantic_verdict=false. Missing/invalid raw payload omitted; defaults empty for historical receipts, no backfill/provider replay. Same immutable receipt projected through native page + Traces/Creases/export; thresholds/adoption unchanged.

## §V

V1: ∀ promoted origin → source-bound encounter + visible assessed/deferred/failed outcome; no direct proposal bypass.
V2: same source retry → same encounter operation outcome; distinct encounter of same scoped claim → separate receipt, ≤1 exact-repeat candidate; atomic latest-state check under concurrency.
V3: missing/stale/ambiguous source/context/referents → visible abstain/awaiting_context; no invented antecedents or semantic equivalence.
V4: Jev output changes no adoption/rejection/merge/collapse/tool state; geometric or lexical nomination ≠ semantic verdict.
V5: relation assessment compares pending + adopted records; bounded deferred/history candidates when relevant; scopes/time explicit; policy + input hashes replay-bound.
V6: prior evaluator verdicts retained as provenance, never sent as independent classifier evidence; malformed/repetitive/unavailable output → visible abstain/defer.
V7: reflection/dream/repeated assent → no new independent warrant/adoption; lineage grouping prevents retries/derived artifacts from inflating independent support.
V8: empirical, artistic, tension warrants non-interchangeable; mixed/unknown valid; artistic warrant cannot substantiate embedded factual claim.
V9: unadopted candidate may express scoped dissent/provisional premise; no automatic permission, tool veto, durable adoption, or evidential increase from dissent.
V10: contradiction can persist with scoped coexistence; no forced merge/rejection/collapse; reviewed decision preserves rationale + participant disagreement.
V11: adoption/revision ! actor + authority + expected version + scope + consequence + challenge + dissent + UTC timestamp; no fabricated shared agreement.
V12: encounter/assessment/decision distinct + linked; completed assessment immutable; source hashes/quotes ≠ credibility; later revision retains earlier statement/receipt.
V13: all five reasoning fields + receipt identity available in belief page/workshop and traces/creases; missing legacy reasoning → unknown, not invented.
V14: candidate/contested/dormant retrieval carries standing + scope + challenges; provisional content cannot masquerade as adopted axiom; historical emission XML inert.
V15: non-use reduces attention only; dormant encounter/decision history remains recoverable; resurfacing preserves standing and adds no independent evidence by itself.
V16: mass, warrant, review state, evaluator confidence remain separate; legacy confidence unchanged without explicit evaluated migration.
V17: event delta exposes quantity/unit; generic legacy impact remains documented/nullable typed fields; API/client compatibility tested; no inferred historical confidence delta.
V18: elapsed-time decay charges each interval at most once; same-clock/retry/restart idempotent; reinforcement timestamp retains its meaning; turn-decay floor behavior independently tested.
V19: origin queue/worker/comparison/provider limits finite; exhaustion visible; no receipt silently lost or candidate promoted on failure; no provider await inside SQLite transaction.
V20: source/statement/receipt reads and writes bound to agent/auth; payloads bounded; secrets absent from persisted receipts/traces/logs; untrusted source text cannot grant instructions/authority.
V21: additive migration preserves legacy beliefs/proposals/receipts; rollback retains history; restart recovers unfinished encounter visibly; no forced reclassification/bulk cleanup.
V22: frozen evaluation distinguishes redundant candidate reduction from useful distinction/conflict retention; accuracy/promotion ground truth independent of author/evaluator; provisional model reviews explicitly non-gold; disagreement + uncertainty reported.
V23: staged enablement requires exact build/migration/config identity + full gates + frozen evaluation target + rollback receipt + explicit rollout decision; offline checks ≠ production certification.
V24: adoption declined → attributable counter-trace; exploratory dissent remains recoverable; repeated objections bounded without silently deleting history.
V25: reviewed standing ! attributable adoption receipt bound to agent, record, current statement hash + scope; legacy lifecycle/skill application ⊥ semantic adoption; supersession retains adoption provenance; no belief standing grants tool authority.
V26: automated corpus review uses two blind distinct returned model families; no historical status/prior verdict/peer answer in review metadata; source text inert; finite call/token/time/worker bounds; source/prompt bindings rechecked on freeze; missing/one-sided context → insufficient_context; disagreement/failure retained; checkpoint before call; no automatic replay of completed/failed/unknown outcomes; rate limit or three failed/uncertain attempts opens reviewer circuit, restored on resume/reuse; replacement reviewer explicit, exact peer receipts reused without replay; frozen model review provisional, non-gold, no adoption/promotion authority.

V27: exact incomplete recurrence display groups only verified mutually ancestral same-agent/conversation sources; reviewed/enriched/stale records excluded; bounded scan explicit; every member/detail/deep link preserved; count adds zero warrant/mass/authority. Tests test_v27_branch_context_and_readonly_grouping + RecurrenceList.test.tsx.

V28: uncertain/malformed Jev dimensions retain bounded valid observations + specific failure status, never accepted semantic relations/warrant; comparison diagnostic bound to exact snapshot/hash; threshold unchanged; original receipt identity/time preserved in page/traces/export; old receipts remain immutable. Tests test_v28_abstained_dimensions_persist_without_relations + EvaluationDiagnostics.test.tsx.
V29: passive chat/user assertion/conversation-pattern nucleation requires source-bound intake receipt; missing/disabled/unpromoted intake → abstain, ⊥ legacy direct-proposal fallback; explicit legacy notes retain declared compatibility route.
V31: adopted proposal/belief aliases resolve to persisted belief kind; revision creates linked candidate with zero mass/confidence/signature, preserves prior commitment + receipt; supersession links adopted target; resurfacing preserves state/warrant. Tests test_v31_revision_alias_and_lineage + test_v16_resurface_preserves_standing_and_adds_no_evidence + test_v16_supersession_requires_adopted_target_and_preserves_both_commitments.
V32: duplicate suggested labels cannot block explicit adoption or mutate prior node; stable ID and quantities retained. Test test_v32_duplicate_suggested_label_keeps_adoption_atomic.
V33: V1 replay binds exact source snapshot to same record; legacy status/mass/confidence untouched; missing source/scope/time → V2 abstention; ⊥ replay-as-new-nucleation/adoption. Tests test_v1_replay_links_legacy_record_and_abstains_without_provider_or_context + test_changed_v1_snapshot_is_rejected_without_replacing_replay_history.

## §T

`id` local to `BELIEF_SPEC.md`; references to root tasks qualified. Status: `.` todo; `~` partial; `x` done. Each task owns cited surfaces; dependencies below.

id|status|task|cites
T1|x|pin local baseline + dirty-state ownership; close root SPEC.md::T78 verification gaps; record production identity or unknown; inventory every origin/direct creator|V1,V21,V23,I.intake
T2|x|repair typed event semantics/client compatibility + elapsed-time decay accounting; regression tests; reconcile decay docs; leave production history untouched|V16,V17,V18,I.events
T3|x|freeze typed encounter/assessment/decision/state contracts, relation adapter, skill-bridge provenance/authority, auth/API routes, queue/comparison defaults, compatibility + flag/rollback semantics; adversarial design review|V3,V4,V5,V11,V12,V19,V20,V21,V25,I.encounter,I.assessment,I.decision,I.state,I.relations,I.api,I.config
T4|x|[source packet](../reports/049-belief-v2-review-corpus/README.md) + [automated provisional freeze](../reports/051-belief-v2-automated-review/README.md); all 54 cases accounted; 80 valid outputs, 26 dual-reviewed cases; source-bound lineage/consequence/conflict/context + disagreement/failure outcomes retained; live coverage partial; independent gold remains V22/V23 promotion condition|V7,V8,V22,V26,I.lineage,I.eval
T5|x|additive persistence: source-bound encounter/claim identities, immutable admission-ledger assessment links, CAS review decisions; agent isolation + concurrent retry/restart; [Report 052](../reports/052-belief-v2-persistence/README.md): 27 focused + 881 full tests passed, strict/static/frontend gates passed|V2,V11,V12,V19,V20,V21,I.encounter,I.assessment,I.decision,I.state
T6|x|explicit chat/dream opt-in v2 intake; default-off flags + durable promotion/pause; legacy page/trace receipt projection + inert historical XML; [Report 053](../reports/053-belief-v2-explicit-intake/README.md): 88 focused + 897 full tests passed; strict/static/frontend gates passed; evaluation deferred T9|V1,V2,V3,V12,V14,I.intake,I.encounter,I.assessment
T7|x|passive chat/pattern/scar source-bound intake; durable pause + preserved unknown ancestry; scar fallback → pending proposal; [Report 054](../reports/054-belief-v2-passive-intake/README.md): 87 focused + 914 isolated full tests passed; strict/static/frontend gates passed; T9 evaluator deferred|V1,V2,V3,V7,V19,I.intake
T8|x|adapt document/shared-note/web creators; lineage/context unavailable visible; bounded failure paths + parity tests|V1,V2,V3,V7,V19,V20,I.intake,I.lineage
T9|x|advisory Jev use case + explicit runtime flag; validated referents + bounded pending/adopted/deferred nomination; versioned relation adapter; immutable replay/outage/stale handling; [Report 056](../reports/056-belief-v2-advisory-assessment/README.md): focused/full/static/frontend gates closed; calibration T15, rollout T18|V3,V4,V5,V6,V8,V10,I.assessment,I.relations
T10|x|migration 066 forward source-lineage observations + typed events atomic with encounter; separate internal activity/recorded recurrence; unknown/declared independence ⊥ verified credit; immutable bounded reads + projection; no historical backfill; [Report 057](../reports/057-belief-v2-source-accounting/README.md): focused/full/static/frontend gates closed|V7,V8,V16,V17,I.lineage,I.events
T11|x|authenticated bounded family review + scoped relations + teachback reconstruction + attributed operator decision + retained decline counter-trace; CAS/idempotency/source checks + atomic traces + legacy write guards; [Report 058](../reports/058-belief-v2-workshop-review/README.md): isolated full/static/frontend gates closed; UI T13, linked revision T16, rollout T18|V4,V9,V10,V11,V12,V24,I.decision,I.state,I.relations
T12|x|authenticated bounded encounter/completed-receipt/decision/event reads; UTC append-snapshot cursors + completion ordering; attributed five-part reasoning + T10 source accounting + unknown legacy fields; [Report 059](../reports/059-belief-v2-export/README.md): 1079 full + 85 focused tests, static/strict gates closed; UI T13, production T18|V12,V13,V17,V20,I.api,I.events
T13|x|belief/workshop UI + traces/creases expose same receipt, five reasoning fields, lineage, status/uncertainty/dissent/family; legacy unknown + failed evaluator display|V8,V10,V13,V24,I.ui
T14|x|bounded exploratory/dormant retrieval + selection receipts; scoped dissent/provisional framing; preserve diffractive geometry; no tool/action authority transfer|V9,V14,V15,V16,V19,V24,I.selection,I.config
T15|x|close evaluation with frozen limits: production slots=0; floor=0.85 unchanged; 44 heldout cases/1 source family; human anchor declined; independent gold + situated usefulness absent; semantic thresholds unset; result inconclusive/no-go, promotion remains blocked; [Report 071](../reports/071-belief-t15-closeout/README.md)|V6,V8,V9,V10,V14,V15,V22,I.eval,I.selection
T15a|x|read-only exact incomplete recurrence queue grouping + expandable original entries; bounded source ancestry; [Report 065](../reports/065-belief-recurrence/README.md): 3 stored proposals →1 expandable verified branch group; 1123 full tests + browser keyboard/detail checks; ADR-128; no admission/threshold change|V2,V3,V13,V20,V22,V27,I.recurrence,I.ui
T15b|x|typed per-question uncertainty diagnostics + source-bound persistence/export/page/trace projection; [Report 066](../reports/066-belief-dimension-diagnostics/README.md): frozen six-call replay retains34 observations, all abstained, no accepted relations/adoption; 1147 full tests; no live retries/threshold tuning|V3,V4,V6,V8,V12,V13,V20,V22,V28,I.diagnostics,I.assessment,I.ui
T15c|x|frozen hypothetical challenge;8 topic families,16 cases; family-disjoint folds; blind non-Jev references, nongold; [Report 067](../reports/067-belief-challenge/README.md):29 valid opinions,10 successful Jev calls all abstain,3 source guards,3 unavailable; prior workshop race retained; current full backend gate 1048 pass, not reproduced; no threshold tuning/promotion|V3,V4,V6,V8,V19,V20,V22,V26,V28,I.eval,I.assessment
T15d|x|offline shadow projection compares aggregate gate with per-dimension floor; binds scope/time/quote; no provider calls, persistence joins, adoption or tuning; [Report 068](../reports/068-belief-shadow-gate/README.md):35 frozen cases,12 observations in 7 hypothetical cases,0 from 6 saved contrast assessments +13 recorded conversation nominations,16 context-blocked; usefulness unresolved|V3,V4,V6,V8,V20,V22,V26,V28,I.eval,I.assessment
T16|x|versioned revision/supersession/resurfacing; legacy mapping + rollback/restart rehearsal on isolated copies; no semantic bulk cleanup|V11,V12,V15,V16,V21,V31,I.decision,I.state,I.config
T17|x|integrated backend/frontend gates; authenticated receipt/source-lineage/dissent parity oracle; contract/config review; local readiness is not production certification; [Report 072](../reports/072-belief-v2-integration-readiness/README.md)|V1,V2,V4,V7,V9,V10,V13,V14,V18,V20,V21,V23,I.api,I.ui,I.eval
T18|~|operator V1 proposal review packet + idempotent V2 replay; staged rollout only after explicit authorization, pin server build/migrations/config, complete-window telemetry, origin-level outcomes + rollback criteria; verify real receipts; report limits|V1,V19,V21,V22,V23,V33,I.config,I.eval

Dependencies:
- T1 → T2,T3,T4. Offline contracts/corpus may progress while production identity unknown; T18 cannot.
- T3 → T5 → T6,T7,T8,T9. T4 supplies evaluation inputs; no promotion target tuned on held-out cases.
- T5,T9 → T10,T11,T12; T10,T11,T12 → T13.
- T9,T10,T11 → T14; T4,T9,T13,T14 → T15.
- T5,T11 → T16; T2,T6–T16 → T17 → T18.
- Each complete task updates affected docs; `x` requires its checks + dependencies. Root T78 status owned by root SPEC.md; no completion implied here.

## §A Acceptance and release

Baseline: reproduce known admission tests/gates; separate current failures from new regressions; identify build/migrations before operational claims. Unit tests use isolated DBs/provider doubles; no production calls in pytest.

Corpus: source text/status/ancestry explicit; frozen cases/hash; disjoint held-out identities where family leakage matters. T4 permits attributed provisional model review with unknown author independence, no gold/adoption/promotion authority. T15 accuracy/acceptance still requires independent ground truth; no mandatory 54-case human annotation for provisional preparation. Philosophical/artistic cases include useful question, active dissent, consequence, unresolved tension; not only factual agreement.

Shadow: all origins accounted for; source retry + concurrent duplicate + evaluator outage + queue full + missing context → visible bounded outcome; no advisory write authority. Entire intake/review/delta route tested, not only XML parsing.

Participation: matched settings + exact model/provider + inputs + variants + outcome rubric; candidate/adopted/conflict/dormant framing checked. Test dismissive collaborator against scoped dissent; retaining dissent must not create tool veto. Record degraded outputs separately from usefulness judgments.

Evaluation targets: T15 freezes justified thresholds + exploratory budget from baseline before final held-out run. Report false equivalence/merge nominations, missed conflicts/useful distinctions, abstention, redundant reviewer burden, lineage unknowns, downstream usefulness. Smaller queue alone ⊥ success. No invented accuracy thresholds or Jev promotion.

Full milestone gates after cross-cutting change:
```text
uv run ruff check backend/
uv run ruff format --check backend/
uv run mypy
uv run pytest
cd frontend
npm run typecheck
npm run lint
npm run test
npm run build
```
Strict-mypy scope ratchet for new/substantially changed modules; no scope weakening. Baseline failures reported separately; full gate remains partial until resolved. `git diff --check` + changed documentation links + ephemeral DB/cache hygiene required.

Rollout: only T18 mutates production under explicit authorization. Independent origin enablement + participation flags; exact applied build/migrations + smoke receipt + rollback rehearsal. Failed gate → no promotion. Migration/replay verification ≠ semantic quality proof. Bulk historical cleanup separate task/authorization.

## §B

id|date|cause|fix
B1|2026-10-08|scar-fold fallback creates crystallized belief without admission; origin omitted from initial intake inventory|T7 repaired locally: pending fallback + opt-in v2 source/segment intake; V1,V7; default-off and promoted fallback regression tests; no production rollout
B2|2026-10-08|generic impact serialized as confidence delta; wall-clock sweep repeatedly charges total inactivity; event insert failure swallowed|T2 resolved locally; V17,V18; typed nullable actual deltas + atomic checkpoint/mass/event; shared legacy helper route; report 047
B3|2026-10-08|accretion could label delta from stale caller snapshot as measured persisted change|T2 resolved locally; V17; writer-lock reread + mutation/event transaction; rollback + stale snapshot tests; report 047
B4|2026-10-08|post-annotation import edit missed final formatter run|ruff format + full format check; mechanical; existing completion gate sufficient
B5|2026-10-08|adapter constant inferred broad str while contract requires literal version|explicit literal annotation; root V30; mechanical typing repair
B6|2026-10-08|draft decision lacked statement-bound hash, allowing receipt reuse after text change; standing enum alone could launder legacy/skill authority|T3 resolved locally; V25; explicit standing variants + receipt/statement/scope/agent binding; Symbia critique recovered
B7|2026-10-08|draft corpus checked candidate context alone, allowing unresolved comparison source to acquire semantic relation|T4 preparation repaired; V3,V22; separate comparison context + unavailable-pair regression; independent review pending
B8|2026-10-08|draft CLI lambda + post-edit formatter mismatch failed static gates|explicit reader function + final format check; mechanical; existing quality gate sufficient
B9|2026-10-08|post-lint digest use lacked restored import; new freeze-integrity test failed|restore import + rerun static/tests; existing completion gate sufficient
B10|2026-10-08|live Qwen preflight rate limited; DeepSeek repeatedly timed out/returned empty truncated output; NVIDIA Ultra HTTP503|V26; retain failures + two interrupted unknowns; three-failure circuit restored before resume; explicit NVIDIA Super replacement + exact Gemini reuse; no automatic replay
B11|2026-10-08|test insertion split existing rate-limit assertions across functions; lint caught undefined locals|restore assertion ownership + rerun full benchmark/static gates; mechanical; existing completion gate sufficient

B12|2026-10-09|draft storage treated source availability as caller assertion and current standing lacked stale binding visibility|T5 guarded owned source/hash/quote, unavailable-origin normalization, read binding status; V3,V20,V25 existing invariants; named regression oracles report 052
B13|2026-10-09|draft reassessment ordering could use lexical IDs instead of committed append order; explicit unknown record link collided with nullable claim identity|T5 ledger append order + explicit scoped identity check; V2,V12; reassessment-head and explicit-unknown-link tests
B14|2026-10-09|parallel pytest sessions share conftest cleanup of all backend test DBs; broad run had missing tables while focused run exited; causal attribution uncertain|serialize final backend runs; retain failed gates separately; existing quality isolation rule sufficient; no production impact

B15|2026-10-09|T5 proposal-history reader returned native assessment JSON into legacy receipt UI; separate admission reader already filtered namespace|T6 unified history projection; V12,V14 existing; real chat/dream page/trace parity + native T5 receipt filtering
B16|2026-10-09|draft explicit grounding checked parent before checkpoint but final completion bound only apparatus message|T6 parent/apparatus recheck in same writer transaction; V3,V20 existing; parent-change regression yields stale assessment
B17|2026-10-09|draft literals/optional indexing failed mypy; Ruff removed fixture import; real-caller fixture reused old reply then omitted pipeline status|typed membrane + fixture re-export + regeneration/result-shape repair; existing strict/static/isolation gates sufficient; 88 focused tests passed

B18|2026-10-09|draft marked known dream context ambiguous solely because lineage was internal, conflating availability with independence|retain available owned source + internal lineage; V3,V7; chat/dream parity asserts available context without independent support; restart full gate against corrected code

B19|2026-10-09|T7 draft tests assumed empty initial belief set despite seeded skill projections; fallback branch not reached; fixture table typo + lint/format corrections|compare pre-existing standing; explicit empty-set fixture + actual bootstrap routes; V1,V7 existing; no new invariant
B20|2026-10-09|T7 sync pattern extraction moved broad catch to new helper, violating architecture-debt ratchet|retain catch at existing async boundary; helper propagates errors; root quality ratchet + V19; architecture regression test
B21|2026-10-09|shared-checkout T7 full gate included concurrent research edits; research-child metabolism assertion failed (1 vs 2); second pytest process observed|retain 922-pass/1-fail receipt; isolate T7 over completed T6 in managed worktree; no unrelated repair; V21 + existing isolation rule

B22|2026-10-09|T8 fixture tried to configure real scorer method as mock; external binding bool inferred Any|inject scorer at actual boundary; explicit bool conversion; existing V1,V20 + typing gate; no new invariant

B23|2026-10-09|T8 draft credited intake agent as external author; apparatus parent lineage unknown; owned representation availability conflated with upstream independence|unknown authorship + internal parent lineage + owned source resolvers; V3,V7,V20 existing; source/parent and stale oracles
B24|2026-10-09|T9 draft stale-check import missing; fixture guessed proposal mass columns and omitted required seed fields; stale summary header despite T8 closed row|mechanical import + schema-bound nucleation_mass/confidence oracle + complete seeds + header correction; existing V3,V4,V16 + static/status gates; no new invariant
B25|2026-10-09|T9 draft attached every warrant dimension to internal nomination, hiding separately bound human parent quotation; zero capacity wait always timed out even with free slot|quote source refs + unknown/internal parent ancestry distinct from nomination; immediate free-slot acquisition; V7,V8,V19 existing; parent-source + zero-wait oracles
B26|2026-10-09|TypeSafe legacy model fallback could appear as reported provider identity; error logs echoed raw provider body|separate nullable returned_model; preserve legacy model field; status/class-only diagnostics; V6,V20; missing-model + sanitized-error oracles

Entries distinguish observed cause from planned repair; B1 resolved locally in T7, no production claim. Admission incidents remain in root `SPEC.md::B110,B111`. B2,B3 ! local full gates in report 047. Nullable legacy telemetry stays unknown; migration checkpoint starts now, no reconstructed charge history.

B27|2026-10-09|T10 draft used unsupported float Literal annotations; fixture mismatched source/lineage, missing legacy FK target, reused initial segment identity|exact bounded numeric fields + schema-bound fixtures + distinct segment IDs; existing V2,V7,V16,V17 + strict/event/retry oracles; no new invariant

B28|2026-10-09|legacy adoption aliases proposal/belief IDs; naive review read rejects legitimate linked representation; draft SQL guessed version timestamp; transition Literal/cast/lint typing|accept only same-agent exact-statement evolved_from_proposal alias; schema-bound created_at + typed transitions; V11,V12,V25 + alias/conflicting-alias/adoption oracles; no new invariant

B29|2026-10-09|new test filename collided with existing legacy workshop tests; restored existing module + separate v2 module; workshop test fixture reused source/segment event identity for different claim; lint imported fixture shadowing; route-only write guard admits provider-await race|distinct peer segment + local fixture wrapper; atomic storage writer guards; V11,V12,V25 regression assertions; no new invariant

B30|2026-10-09|legacy merge without statement change can bypass target statement guards; target may become managed during scorer await|guard target inside merge write transaction, run writer in to_thread; V11,V16,V25 direct/no-statement + provider-await race oracles; no new invariant

B31|2026-10-09|PowerShell stdin + Python locale default introduced a CP1252 em-dash into UTF8 docs index|explicit UTF8 reads/writes; owned-doc decode and local-link oracle; existing documentation/quality protocol, no new belief invariant

B32|2026-10-11|full suite: upload path-traversal fixture launched real digest subprocess against shared test state; missing perception tables; 1020 passed, 1 failed|fresh app + migrated temporary DB/upload dir, mock digest/daemon work; keep real sanitization/persistence and safe worker-argument assertions; quality isolation oracle, no new belief invariant

B33|2026-10-11|snapshot lint inherited scratch Gitignore and reported zero files; shared-checkout research work changed verification context|Ruff no-respect-gitignore + explicit file-count proof; archive baseline plus owned-file hashes, independent snapshot DB; existing quality/isolation protocol, no new belief invariant

B34|2026-10-11|T12 harness omitted parent basetemp directory; reassessment fixture started before predecessor completion; reasoning comparison union inferred too narrowly; tiny budget fixture never reached SQLite progress callback|create scoped test-run parent; ordered fixture times; explicit projection union; sufficient real WAL scan + aggregate budget oracle; existing V12,V19 and quality isolation, no new invariant

B35|2026-10-11|T12 final review exposed original lineage declarations without T10 recorded observation in export projection|bounded owned immutable source-accounting read + native event/legacy unknown parity assertions; existing V7,V8,V13,V20, no new invariant

B36|2026-10-11|T12 response redaction compared raw configured secrets while authentication trims surrounding whitespace|trim configured secret components at response membrane; padded/unpadded secret projection regression; existing V20, no new invariant

## References

- [AAA philosophy](../philosophy/PHILOSOPHY.md): situated cuts, non-servility, transindividual individuation, zero internal warrant, agonistic preservation.
- [ADR-027](../decisions/ADR-027-proto-belief-lifecycle-tension-ecology-self-tuning.md): proto-belief fuzzy participation + retained exclusions.
- [ADR-100](../decisions/ADR-100-jev-belief-evidence-and-review-routing.md), [ADR-102](../decisions/ADR-102-belief-context-and-calibration.md): advisory triage + context-bound independent calibration.
- [ADR-115](../decisions/ADR-115-shadow-belief-admission.md): source-bound explicit candidates + human adoption baseline.
- [Report 045 full delayed replies](../reports/045-belief-month-review/beliefs-v2-delayed-replies.json): critique source; not deployment or semantic-validation evidence.

B37|2026-10-11|T13 first harness used frontend-relative report path; legacy detail mock omitted new review dependency; assertions matched visible summaries plus raw receipt data and ignored inherited fieldset disablement|correct rooted report path + explicit review double + scoped/multiple text assertions + disabled pseudo-class oracle; existing V11,V13 and quality protocol, no new invariant

B38|2026-10-11|T13 strict frontend check found unused test transport argument|explicit unused-argument name + rerun strict gate; mechanical, existing quality protocol sufficient

B39|2026-10-11|T13 review found old form briefly enabled while stale-conflict refresh awaited a new snapshot|invalidate loaded snapshot before refresh; agent-qualified legacy action gate; V11,V20 existing, deferred-refresh regression

B40|2026-10-11|T13 local browser fixture used Windows absolute path as Node ESM module URL|explicit file URL + restart owned fixture; harness-only, existing quality protocol sufficient

B41|2026-10-11|T13 browser fixture returned bare refusal array instead of existing response object, triggering route boundary|schema-bound fixture object + fresh browser load; harness-only, existing quality protocol sufficient

B42|2026-10-11|T13 browser select label matcher included nested option text; stale fixture server survived overly narrow process filter|explicit select label association + exact owned server PID restart; V13 accessibility and quality harness boundaries, no new invariant

B43|2026-10-11|T13 final review found agent-bound native receipts linked to default-agent workshop page|carry agent in native family/trace links + scoped belief-list read/reload; V13,V20 existing, nondefault-agent deep-link oracle

B44|2026-10-11|T13 real belief-list component test lacked jsdom matchMedia browser capability|scoped desktop media-query double + real read/decision/reload assertions; harness-only, existing quality protocol sufficient
B45|2026-10-11|T13 removed two belief-list any casts; lint debt gate detected stale baseline|remove only resolved entry; existing quality ratchet sufficient
B46|2026-10-11|T14 first static pass detected local import order; review found query placeholder count and missing skill-router asyncio import|fix mechanical errors before runtime oracle; existing quality/concurrency invariants sufficient
B47|2026-10-11|T14 focused run found invalid test origin enum, seed-dependent first-item assertion, native encounter candidate labelled legacy without a decision row|authored fixture + identity lookup; derive provisional candidacy from recorded encounter, never adoption; V14,V25 existing
B48|2026-10-11|T14 isolated fixture inherited migration-seeded skill bridge, breaking exact geometry/count assertions|remove seed only inside fresh selection fixture; transport test retains real seeded receipt; harness-only
B49|2026-10-11|T14 review found second belief-mass skill-prior route in afferent router|exclude selection-receipt items in heuristic + afferent routes; paired ranking oracle; V9 existing
B50|2026-10-11|T14 review found whole-JSON secret masking misses escaped credentials; decision binding lacked version check|scrub fields before JSON + quoted-secret oracle; bind state/decision versions; V20,V25 existing
B51|2026-10-11|T14 review found low-confidence declined proposals could enter always-on legacy spectral path|legacy spectral requires node representation and excludes declined/superseded; default-off decline oracle; V14,I.config existing
B52|2026-10-11|T14 full suite dream daemon doubles lack SQLite repository identity|retain identified nonpersistent adapter path capped100 + explicit unknown meta standing; real SQLite errors never fallback; existing compatibility/concurrency boundaries sufficient
B53|2026-10-11|T15 fixture expected missing comparison to count as unavailable-pair abstention|assert no_comparison separately; V22 existing; provisional opinions remain nongold
B54|2026-10-11|T15 identical-geometry synthetic replay: deterministic friction/resonance repeatedly reach only2 of12 eligible records across2 signatures; held-out44 cases share1 source family|retain coverage failure + family count; defaultoff/0; recorded coverage/generalization/usefulness unresolved; V22 existing

B55|2026-10-11|recorded context may end with system role; initial replay assumed last user role|preserve contiguous role sequence; source-bound role regression; V22 existing
B56|2026-10-11|exact quoted excerpts with outer quote envelopes failed review binding|derive labeled projection from immutable receipt; strip only matching envelope, reject changed text/schema; V22 existing
B57|2026-10-11|review validation failures exhausted shared generation circuit|separate role/model circuits; retain finite budgets and no retry checkpoints; V19,V22 existing
B58|2026-10-11|live replay: three bounded generation truncations and malformed/unbound reviews; unchecked case ID could enter receipt path|retain raw failures; numeric unique case IDs + traversal regression; no production enablement; V20,V22 existing

B59|2026-10-11|intake replay harness relied on init_db migration env and initially misnamed encounter table|explicit isolated migrations + absolute run path + real repository regression; V20 existing
B60|2026-10-11|unscoped exact recurrence produces new pending proposal; six live Jev contrasts all abstain at existing confidence floor|retain backlog + raw uncertain choices; scoped V2 unchanged; no threshold tuning/adoption; T15 acceptance unresolved, V22 existing

B61|2026-10-12|recurrence draft read oldest receipt from newest-first native history|latest index0 + enrichment regression; V27 existing
B62|2026-10-12|recurrence component exported helper and failed React refresh lint contract; import ordering failed Python gate|separate pure helper module + sorted imports; existing quality protocol sufficient
B63|2026-10-12|first full verification workshop concurrent same-key test returned4/6 results; grouping paths absent from that test; cause unconfirmed|retain failed log; isolated2 + final1123 pass; no workshop rewrite or new invariant; existing V11 concurrency contract
B64|2026-10-12|advisory gate erased all dimensions on one uncertain answer and dropped returned model on abstention|bounded typed diagnostics separate from accepted relations; retain reported model; immutable trace/export parity + malformed/nonfinite/missing regressions; V28
B65|2026-10-12|challenge reviewer closure left loop case unbound in lint; fixture records initially lacked required trigger|bind case in each callback; neutral trigger on all premises, exclude from reference prompt; static + real intake regression; V22,V26 existing
B66|2026-10-12|migration051 auto-resolved live structural evaluator during benchmark setup; legacy replay total calls uninstrumented|benchmark-only unavailable-scorer guard + no-network regression; retain contamination erratum; no production migration change; V19,V22
B67|2026-10-12|reference prompt left uncertainty type unspecified; NVIDIA numeric uncertainty rejected by v1 text schema; provider connections then failed|separate v2 projection retains numeric self-report uncalibrated; raw failures immutable; supplement only unattempted cells after connectivity restoration; V26
B68|2026-10-12|aggregate assessment status hides independently confident dimensions from quick inspection|offline namespace projection keeps each above-floor observation and unresolved dimensions distinct; scope/time/quote binding required; no persisted join or adoption authority; V22,V28 existing
B69|2026-10-13|default-off passive chat intake returned None then legacy engine directly created proposal from ordinary task turn|fail closed for passive chat/user assertion/conversation pattern absent source-bound intake receipt; explicit legacy notes preserved; test_v29_default_off_passive_chat_abstains_without_legacy_proposal; V29
B70|2026-10-13|adopted proposal/belief alias read exposed proposal kind first, blocking linked revision|resolve actual backing kind; test_v31_revision_alias_and_lineage; V31
B71|2026-10-13|revision hash used canonical JSON digest instead of raw statement SHA256|hash exact UTF-8 statement; test_v31_revision_alias_and_lineage; V31
B72|2026-10-13|second explicit adoption collided on per-agent label uniqueness and rolled back|suffix colliding fallback label by stable record ID; test_v32_duplicate_suggested_label_keeps_adoption_atomic; V32
B73|2026-10-13|strict mypy rejected optional inferred workshop transition state|narrow transition result to ReviewState; existing strict typing gate
B74|2026-10-13|revision proposal inherited predecessor vector, implying unmeasured geometry for changed statement|initialize neutral zero signature; V31
B75|2026-10-13|lineage assertions landed in unrelated idempotency test and referenced unbound successor|place assertions in revision test; Ruff scope check
B76|2026-10-13|new replay test asserted mapping access after service result became typed dataclass|use typed attributes; focused tests + strict typing; mechanical; existing quality gates sufficient
