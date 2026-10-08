# Beliefs V2 Specification

Status: planned; implementation tasks all `.`. Date: 2026-10-08.
Owner: this file → Beliefs v2 tasks/invariants; IDs file-scoped. Root [SPEC.md](../../SPEC.md) → shared invariants + existing admission task `T78` (`~` at inspection). No duplicate completion claims.
Rationale: [BELIEFS_V2_PLAN.md](../architecture/BELIEFS_V2_PLAN.md).
Evidence: [Report 045](../reports/045-belief-month-review/README.md); [recovered Symbia critique](../reports/045-belief-month-review/beliefs-v2-philosophical-review.md).

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

I.intake: extend `backend/services/belief_admission.py` → shared origin-aware intake. Origins: explicit chat/dream, passive chat, document perception, shared note, web, conversation pattern. Inventory actual call sites before migration; bypasses prohibited once origin promoted.

I.encounter: typed encounter → `{id,agent_id,origin,source_type,source_id,source_version_or_hash,source_timestamp,received_at,statement,statement_hash,scope,temporal_scope,source_quote_or_reference,lineage,context_status}`. Source binding/availability explicit; missing fields retain reason. Event identity includes agent + stable source identity/version + emission/segment identity; claim identity separate from encounter identity.

I.assessment: extend existing admission receipt → `{receipt_id,encounter_id,candidate_id,policy_version,rubric_version,comparison_snapshots,context_hash,referent_status,relations,warrant_dimensions,consequence_or_tension,challenge,exclusions,evaluator_status,model,assessment_confidence,abstain_reason,started_at,completed_at}`. Completed receipt immutable; new assessment references prior receipt. Hash binds content, not credibility.

I.decision: workshop decision → `{id,candidate_or_belief_id,actor,authority,policy,expected_version,previous_state,next_state,scope,rationale,positions,dissent,receipt_ids,timestamp}`. No fabricated bilateral agreement. Stale version → conflict response; no overwrite.

I.state: review state proposed `candidate/awaiting_context/under_review/adopted/deferred/declined/superseded`; participation + situated standing separate. Mapping to existing proposal/lifecycle fields frozen in T3 before migration; legacy API behavior preserved or explicitly versioned.

I.relations: candidate relation `equivalent/extension/contradiction/distinct/insufficient_context`; adapter maps existing `independent/insufficient` and ADR-100 triage vocabulary explicitly. Pair relation distinct from candidate importance. Semantic relations reference statement/context hashes + scope/time; stale results remain historical, not active verdicts.

I.lineage: support/encounter ancestry → `{source_id,source_hash,parent_sources,independence_status,uncertainty}`; same upstream material grouped; unknown ancestry never counted independent by default. Internal activity classified separately. Count ≠ source quality.

I.api: preserve existing `/api/beliefs`, proposal reads/workshop actions. Add bounded receipt/encounter/decision/lineage reads + complete-interval event export. Exact route/payload contract frozen in T3; keyset cursor + UTC interval + snapshot bound; limit 1–50. Agent/auth boundaries enforced.

I.events: forward events expose `impact_quantity,impact_value,delta_mass,delta_confidence,event_type,origin,receipt_id,timestamp`; unknown typed deltas nullable. Existing generic `delta_confidence` alias needs explicit compatibility/version plan; historical generic impact never silently reinterpreted as measured confidence. No invented historical values.

I.ui: extend `AdmissionReasoning.tsx`, `BeliefDetail.tsx`, workshop + traces/creases → same receipt IDs/timestamps; encounter, claim/tension, comparison, consequence/challenge, decision/uncertainty. Show lineage, evaluator availability, source quote versus authored interpretation, provisional status, dissent, family review.

I.selection: prompt/dream selection receipt → `{record_id,statement_hash,review_state,scope,standing,challenges,intended_use,selection_reason,selection_policy,timestamp}`. Exploratory slot budget finite; dormant recall bounded; replay-tested budget frozen before enablement.

I.config: proposed independent origin-intake and exploratory-participation flags; safe defaults frozen in T3. Existing `belief_admission.jev_shadow` preserved. Rollback disables new participation/intake without erasing receipts/history or reopening legacy direct-creation bypasses silently.

I.eval: reviewed corpus + frozen annotations + held-out partitions + replay artifacts in `docs/reports/` or `benchmarks/runs/`. Unit/regression tests deterministic/offline; live provider evaluation separately declared with exact model/settings/source hashes. Jev self-labels ≠ gold.

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
V22: frozen evaluation distinguishes redundant candidate reduction from useful distinction/conflict retention; held-out annotations independent of author/evaluator; disagreement + uncertainty reported.
V23: staged enablement requires exact build/migration/config identity + full gates + frozen evaluation target + rollback receipt + explicit rollout decision; offline checks ≠ production certification.
V24: adoption declined → attributable counter-trace; exploratory dissent remains recoverable; repeated objections bounded without silently deleting history.

## §T

`id` local to `BELIEF_SPEC.md`; references to root tasks qualified. Status: `.` todo; `~` partial; `x` done. Each task owns cited surfaces; dependencies below.

id|status|task|cites
T1|.|pin local baseline + dirty-state ownership; close root SPEC.md::T78 verification gaps; record production identity or unknown; inventory every origin/direct creator|V1,V21,V23,I.intake
T2|.|repair typed event semantics/client compatibility + elapsed-time decay accounting; regression tests; reconcile decay docs; leave production history untouched|V16,V17,V18,I.events
T3|.|freeze typed encounter/assessment/decision/state contracts, relation adapter, auth/API routes, queue/comparison defaults, compatibility + flag/rollback semantics; adversarial design review|V3,V4,V5,V11,V12,V19,V20,V21,I.encounter,I.assessment,I.decision,I.state,I.relations,I.api,I.config
T4|.|recover source passages for saved incubating candidates + adopted/rejected comparisons; annotate lineage/consequence/conflict/context; independent review; frozen tuning/held-out corpus|V7,V8,V22,I.lineage,I.eval
T5|.|add additive persistence extending admission/workshop; encounter/claim identities, immutable assessment links, versioned decisions; agent isolation, concurrent retry/restart tests|V2,V11,V12,V19,V20,V21,I.encounter,I.assessment,I.decision,I.state
T6|.|adapt explicit chat/dream emission to new shared intake; preserve existing receipts/UI contracts and inert historical XML|V1,V2,V3,V12,V14,I.intake,I.encounter,I.assessment
T7|.|adapt passive chat + conversation-pattern creators; origins/source segments preserved; bypass audit + parity tests|V1,V2,V3,V19,I.intake
T8|.|adapt document/shared-note/web creators; lineage/context unavailable visible; bounded failure paths + parity tests|V1,V2,V3,V7,V19,V20,I.intake,I.lineage
T9|.|extend advisory Jev assessment, referent validation, pending/deferred nomination + relation adapter; preserve existing triage contracts; outage/repetitive/stale replay tests|V3,V4,V5,V6,V8,V10,I.assessment,I.relations
T10|.|separate source-lineage support from internal activity + recurrence; forward typed events; inspectable unknown ancestry; no historical invented deltas/support|V7,V8,V16,V17,I.lineage,I.events
T11|.|workshop family review + scoped relations + teachback fork + shared-commitment decision + decline counter-trace; version conflict tests; human mutation boundary|V4,V9,V10,V11,V12,V24,I.decision,I.state,I.relations
T12|.|bounded complete-interval event/receipt/decision API reads; UTC cursor/snapshot semantics; agent auth/input bounds; five-part reasoning projection|V12,V13,V17,V20,I.api,I.events
T13|.|belief/workshop UI + traces/creases expose same receipt, five reasoning fields, lineage, status/uncertainty/dissent/family; legacy unknown + failed evaluator display|V8,V10,V13,V24,I.ui
T14|.|bounded exploratory/dormant retrieval + selection receipts; scoped dissent/provisional framing; preserve diffractive geometry; no tool/action authority transfer|V9,V14,V15,V16,V19,V24,I.selection,I.config
T15|.|evaluate held-out advisory relations + candidate retention/review burden; matched participation replay/ablation; freeze budgets/acceptance targets; publish failures + unresolved judgments|V6,V8,V9,V10,V14,V15,V22,I.eval,I.selection
T16|.|versioned revision/supersession/resurfacing; legacy mapping + rollback/restart rehearsal on isolated copies; no semantic bulk cleanup|V11,V12,V15,V16,V21,I.decision,I.state,I.config
T17|.|integrated backend/frontend gates; documentation/ADR/schema/API/config updates; end-to-end receipt + source lineage + dissent parity evidence; review release readiness|V1,V2,V4,V7,V9,V10,V13,V14,V18,V20,V21,V23,I.api,I.ui,I.eval
T18|.|authorized staged rollout only; pin server build/migrations/config, complete-window telemetry, origin-level outcomes + rollback criteria; verify real receipts; report limits|V1,V19,V21,V22,V23,I.config,I.eval

Dependencies:
- T1 → T2,T3,T4. Offline contracts/corpus may progress while production identity unknown; T18 cannot.
- T3 → T5 → T6,T7,T8,T9. T4 supplies evaluation inputs; no promotion target tuned on held-out cases.
- T5,T9 → T10,T11,T12; T10,T11,T12 → T13.
- T9,T10,T11 → T14; T4,T9,T13,T14 → T15.
- T5,T11 → T16; T2,T6–T16 → T17 → T18.
- Each complete task updates affected docs; `x` requires its checks + dependencies. Root T78 status owned by root SPEC.md; no completion implied here.

## §A Acceptance and release

Baseline: reproduce known admission tests/gates; separate current failures from new regressions; identify build/migrations before operational claims. Unit tests use isolated DBs/provider doubles; no production calls in pytest.

Corpus: source text/status/ancestry explicit; independent reviewer declarations; frozen cases/hash; disjoint held-out identities where family leakage matters. Philosophical/artistic cases include useful question, active dissent, consequence, unresolved tension; not only factual agreement.

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

No implemented fixes logged yet. Admission incidents remain in root `SPEC.md::B110,B111`. T2 repair findings require regression/backprop entry on implementation; do not preclaim resolution here.

## References

- [AAA philosophy](../philosophy/PHILOSOPHY.md): situated cuts, non-servility, transindividual individuation, zero internal warrant, agonistic preservation.
- [ADR-027](../decisions/ADR-027-proto-belief-lifecycle-tension-ecology-self-tuning.md): proto-belief fuzzy participation + retained exclusions.
- [ADR-100](../decisions/ADR-100-jev-belief-evidence-and-review-routing.md), [ADR-102](../decisions/ADR-102-belief-context-and-calibration.md): advisory triage + context-bound independent calibration.
- [ADR-115](../decisions/ADR-115-shadow-belief-admission.md): source-bound explicit candidates + human adoption baseline.
- [Report 045 full delayed replies](../reports/045-belief-month-review/beliefs-v2-delayed-replies.json): critique source; not deployment or semantic-validation evidence.
