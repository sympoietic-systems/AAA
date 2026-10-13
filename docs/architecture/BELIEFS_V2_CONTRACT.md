# Beliefs v2 intake and review contract

Status: T3 frozen shapes, 2026-10-08; T5 persistence implemented locally, verification in [Report 052](../reports/052-belief-v2-persistence/README.md). T11 workshop and T12 export routes are implemented locally; T18 production origin enablement remains future work. [BELIEF_SPEC.md](../systems/BELIEF_SPEC.md) owns implementation status. [Report 047](../reports/047-belief-v2-quantities-and-decay/README.md) records the completed T2 repair.

## Record ownership and authority

An encounter records what arrived. An assessment records an interpretation of that encounter. A decision records an attributable commitment or review action. Each has its own stable ID, agent ID, UTC timestamp, schema version, and links to the other records. A hash binds content; it does not establish credibility or grant authority.

Extend the existing `belief_admission` receipt ledger and proposal/workshop boundaries. Completed assessments remain immutable; reassessment appends a linked assessment with a new ID and attempt identity. Canonical review state is a versioned sidecar to existing proposals/beliefs. It must not become a competing source of statement text or legacy lifecycle. The storage binding and additive migration are implemented in T5, with legacy receipt reads retained.

The initial decision authority is an explicit authenticated operator action, corresponding to the human review boundary in the plan. The backend derives the principal and authorization context from the request; a model output or request field cannot supply them. Jev and intake workers have no decision write capability. Existing shared-password/session authentication identifies an operator credential, not a uniquely verified physical person. Record that limitation instead of inventing personal attribution or bilateral agreement. Trusted human-channel attribution must be established by the application boundary; a string such as `human_approved` is not proof.

Agent FLUX remains an additional guard for direct authored-belief editing and destructive revision/merge surfaces. It is not proof of reviewer identity. Ordinary workshop adoption preserves the existing explicit operator action boundary. Future APIs must reconstruct authorization server-side and enforce agent ownership on every lookup and linked record.

## Typed records

All new record schemas reject unknown fields, non-finite numeric values, and naive timestamps. IDs are bounded identifiers; hashes are lowercase SHA-256 hex. Strings and arrays have explicit limits. Unknown information is nullable with a reason; no empty placeholder pretends to be known context. Completed records use immutable representations, including nested collections.

| Record | Required fields and types | Unknown or optional fields |
| --- | --- | --- |
| Source reference | `source_type: str[1..64]`, `context_status: available/missing/stale/ambiguous`, `activity: internal/external/unknown` | `source_id: str[1..200]?`, `source_version: str[1..200]?`, `source_sha256: hash?`, `source_timestamp: UTC?`, `quote: str[0..2000]`, `reference: str[0..500]`, `unavailable_reason: str[0..500]` |
| Encounter | `id`, `agent_id`, `origin`, `segment_id: str[1..100]`, `received_at: UTC`, `statement: str[1..4000]`, `statement_sha256`, `scope: str[0..500]`, `temporal_scope: str[0..250]`, `source`, `lineage: tuple[0..50]` | `candidate_id?`, `trigger: insight/conflict/counterexample/evidence/unknown`, source/context exclusions |
| Comparison snapshot | `record_id`, `agent_id`, `record_kind: proposal/belief/skill_projection`, `statement`, `statement_sha256`, `scope`, `temporal_scope` | `review_state?`, `review_version?`, `legacy_status?`, source/context limitations |
| Relation observation | `comparison_id`, `comparison_statement_sha256`, `relation: equivalent/extension/contradiction/distinct/insufficient_context`, `scope`, `temporal_scope`, `adapter_version` | `raw_relation?`, `raw_contract?`, `assessment_confidence: float[0..1]?`, uncertainty/reason |
| Warrant dimension | `name: str[1..64]`, `basis: str[0..1000]`, `source_refs: tuple[0..50]` | `uncertainty`, `challenge`, `independence_status: independent/derived/internal/unknown` |
| Assessment | `id`, `agent_id`, `encounter_id`, `policy_version`, `rubric_version`, `context_hash`, `referent_status`, `comparison_snapshots: tuple[0..10]`, `relations: tuple[0..10]`, `warrant_dimensions: tuple[0..16]`, `consequence_or_tension`, `challenge`, `exclusions: tuple[0..20]`, `evaluator_status`, `started_at: UTC` | `candidate_id?`, `previous_assessment_id?`, `requested_model?`, `returned_model?`, `assessment_confidence?`, `abstain_reason?`, `completed_at: UTC?` |
| Decision | `id`, `agent_id`, `record_id`, `statement_sha256`, `actor`, server-owned `authority`, `policy_version`, `expected_review_version: int>=0`, `previous_state`, `next_state`, `scope`, `rationale`, `consequence`, `challenge`, `positions: tuple[0..20]`, `dissent: tuple[0..20]`, `assessment_ids: tuple[0..50]`, `timestamp: UTC` | Participant positions remain unknown unless attributed to a declaration; no generated consensus |
| Skill projection | `kind: skill_projection`, `agent_id`, `belief_id`, `skill_id`, `skill_version`, `skill_statement_sha256`, `application_authority`, `semantic_adoption_authority: none` | `skill_event_id?`, `application_actor?`; absent legacy application provenance remains unknown |

Available source context requires a stable source identity/hash and a quote or reference. A source with missing/stale/ambiguous context requires a reason and cannot receive an established semantic relation. Source quotes and stored XML remain inert data. Hashes and quote binding are recomputed by the application against current source material, before final receipt commit. Persist sanitized snapshots with a named redaction policy; the sanitized assessment-input hash is distinct from the original source binding hash.

Encounter identity includes agent, origin, stable source identity/version, and segment/emission identity. Claim identity separately includes normalized statement, scope, and temporal scope. Exact-repeat lookup is an indexed identity check over current eligible records, rather than the bounded semantic nomination window. Missing source identity produces a visible unavailable/deferred encounter; it must not manufacture an idempotency guarantee.

Empirical/traced, artistic/axiomatic, and unresolved-tension dimensions are nonexclusive, extensible names rather than an exhaustive enum. A factual component cannot borrow artistic warrant. Unknown ancestry remains unknown; internal reflection and repeat encounters cannot declare themselves independent corroboration. Completed assessments preserve source quotation, authored interpretation, and application-owned validation separately.

## Review states and compatibility

### T5 storage binding

Migration 064 extends the admission ledger and adds immutable encounter/claim/assessment/decision associations plus a versioned state sidecar. Assessment JSON remains in `belief_admission`; legacy history readers omit its `v2:` namespace. New candidate statements stay in existing proposal storage. Explicit legacy links retain unknown canonical state. Known scoped claim keys and source-operation keys are separate; unknown scope/time or source binding cannot manufacture those keys. Explicit record links must retain their scoped identity.

`BeliefReviewStore` / `BeliefReviewRepository` expose intake and assessment operations without decision-write capability. `BeliefDecisionStore` / `BeliefDecisionRepository` require a matching trusted actor and atomically check version/state/current statement and completed record-bound assessment links. The caller establishes authentication; T5 does not install HTTP routes. Current standing reports a stale binding when legacy statement text changes; historical receipts survive.

T5 verifies message/chat-turn sources through agent-owned conversations, actual content hashes and literal quotes. Unsupported source kinds become explicitly ambiguous until their origin resolver exists. Pending work is durable and recoverable through clamped keyset reads; recovery never replays a provider. Completed assessments and links are immutable; new assessments append to the latest completed predecessor. `reject-secrets-v1` checks recognized secret patterns and configured credentials before storage; it rejects unsafe inputs instead of silently changing their bound hashes. Original source hashes and application input hashes remain separate.

### T6 explicit origin binding

Chat/dream retain their shared `admit_candidate` entry point. Strict boolean `belief_review.origin_intake.explicit_chat` / `explicit_dream` flags default off. Migration 065 retains agent/origin promotion markers and immutable emission annotations. Once promoted, disabling an origin keeps v2 encounters with `origin_paused`; it cannot restore legacy writes. Never-promoted origins preserve legacy admission.

Explicit encounters bind the actual apparatus message and stable parser segment index. Original tag digest, cleaned-message hash and statement snapshot are distinct; parent quote/hash/lineage is separate. Chat parent independence stays unknown; dream/apparatus-parent lineage is internal. Final parent binding rechecks share the completion transaction. T6 v2 assessments explicitly defer evaluation to T9 and grant no adoption authority. Linked annotation/assessment records project the existing page/trace receipt shape without another authoritative ledger payload. [ADR-119](../decisions/ADR-119-explicit-belief-origin-intake.md), [Report 053](../reports/053-belief-v2-explicit-intake/README.md).

Canonical review states are `candidate`, `awaiting_context`, `under_review`, `adopted`, `deferred`, `declined`, and `superseded`. Review state does not derive from mass, confidence, lifecycle stage, or a relation label. Standing carries scope, challenges, warrant dimensions, lineage uncertainty, and decision provenance. Participation is a separate bounded intended use: question, comparison, experiment proposal, scoped dissent, or provisional premise. None grants a tool veto or execution authority.

T7 passive chat/pattern/scar adapters reuse the same ledger, promotion markers and annotation projection. Their flags default off; promoted pauses retain encounters. Actual message hashes bind chat/scar observations; patterns retain unknown ancestry and null conversation links. Scope/time remain unresolved, so distinct unscoped observations do not fabricate an exact-repeat claim identity. Scar fallback globally creates a pending proposal instead of a crystallized belief. An injected bootstrap callback preserves module/service layering; synchronous intake is offloaded once. [ADR-120](../decisions/ADR-120-passive-belief-origin-intake.md), [Report 054](../reports/054-belief-v2-passive-intake/README.md).

| Existing representation | Compatibility projection | Authority limit |
| --- | --- | --- |
| `pending` proposal | Legacy status retained; candidate workflow hint | No invented assessment or commitment |
| `refined` proposal | Legacy status retained; reviewed-formulation hint | Agent refinement is not operator adoption |
| `rejected` proposal | Legacy status retained; canonical decision unknown without a recorded decision | It may represent automatic collapse; do not invent an operator decline |
| `adopted` proposal / crystallized belief | Legacy lifecycle/status retained; canonical decision unknown without attributable provenance | Crystallization alone is not a reviewed shared commitment |
| Derived skill bridge | `kind=skill_projection`, application provenance separate | Skill application authority cannot automatically transfer to semantic adoption |
| V2 decision-backed record | Canonical state and review version alongside legacy fields | State changes require expected-version and previous-state checks |

Legacy workflow hints are explicitly non-authoritative. A null canonical review state or decision is rendered as unknown; no migration retroactively adopts, declines, or reclassifies a record. V2 candidates continue to use pending/refined proposal storage; deferred/awaiting-context states use the sidecar without erasing encounters. An explicit decline retains the counter-trace. Adoption retains the stable record ID and links the adopted belief to its proposal and decisions. Supersession preserves earlier statements and decisions.

Initial state transitions separate app bookkeeping from commitments. Intake may create candidate/awaiting-context records, start under-review assessment, or defer on missing context/capacity. It may not adopt, decline, merge, revise, or supersede a commitment. Operator decisions may adopt, decline, defer, or request further context/review; revision, merge, and supersession require their explicit commands. Relation assessments never invoke these transitions. Persistence checks the latest version atomically; a stale decision returns conflict rather than overwriting.

Skill application preserves its existing tier rules, including autonomous high-confidence application and explicit approval for always-active skills. The bridge records the actual skill application authority and source version. Reviewing the bridge as a semantic commitment requires a separate decision. Legacy bridges lack invented application events or principal identities.

### Standing receipt binding

`SituatedStanding` distinguishes `legacy_sediment`, `skill_projection`, `situated_candidate`, and `reviewed_commitment`. Every linked decision must match the agent, record, current statement hash and scope. Current review state must match the latest decision. Adopted standing requires an operator adoption receipt; superseded commitment also retains its original adoption receipt. Legacy sediment and skill application cannot supply canonical semantic adoption. Known skill application requires version, hash, event and actual actor provenance; missing legacy provenance remains unknown.

Standing includes bounded challenges, warrant dimensions and permitted participation modes. The standalone models validate record shape; later persistence must resolve and authenticate the referenced receipts. The schemas do not change current prompt assembly or existing legacy mass/confidence.

## Relation adapter

Version: `belief-relation-adapter-v1`. Retain raw contract, label, context status, and reason with every adapted observation. The adapter nominates review; it does not create a relation edge or authorize a merge.

| Input contract | Input | Candidate relation | Qualification |
| --- | --- | --- | --- |
| Explicit admission v1 | `equivalent`, `extension`, `contradiction` | Same name | Context and scope/time must be validated |
| Explicit admission v1 | `independent` | `distinct` | Preserve nomination/assessment uncertainty |
| Explicit admission v1 | `insufficient` | `insufficient_context` | Retain reason |
| ADR-100 triage | `contradiction` | `contradiction` | Retain original signal/confidence disagreement rules; no edge application |
| ADR-100 triage | `orthogonal` | `distinct` | Semantic nomination with validated context |
| ADR-100 triage | `endorsement` | `insufficient_context` | Support does not resolve equivalence versus extension; fresh pair assessment needed |
| ADR-100 triage | `abstain` | `insufficient_context` | Retain reason |
| Any | Unknown label or missing/stale/ambiguous context | `insufficient_context` | Never infer a semantic verdict |

Contradiction persists as a reviewable split. Pair relation and candidate consequence are separate fields. Statement/scope/time hashes bind active observations; changed inputs make the old observation historical. Prior evaluator verdicts remain provenance outside classifier context.

## Installed API boundary

The T3 paths below are installed by T11/T12. Existing `/api/beliefs` and workshop routes remain compatible. The `/api/beliefs/v2/agents/{agent_id}` namespace is registered before generic belief-ID routes when implemented.

| Route under `/api/beliefs/v2/agents/{agent_id}` | Method | Contract |
| --- | --- | --- |
| `/encounters`, `/assessments`, `/decisions`, `/events` | GET | Required UTC `from`/`to`; exclusive `to`; `limit` 1–50, default 25; keyset cursor bound to agent, resource, interval, filters, and snapshot |
| `/encounters/{id}`, `/assessments/{id}`, `/decisions/{id}` | GET | Typed record; cross-agent IDs return not found |
| `/records/{record_id}/review` | GET | Current standing, review version, decision/assessment links, legacy unknowns; bounded history pages |
| `/records/{record_id}/decisions` | POST | Explicit action, expected review version/state/statement hash; merge/supersede also require target version/hash; bounded rationale/scope/consequence/challenge, attributed declarations; server constructs actor/authority |

Read routes use existing authentication and agent selection, with database-level agent predicates on records and source joins. The current shared operator credential permits agent selection; it does not establish per-person tenancy. `agent_id` is never inferred from a supplied record belonging to another agent.

Event export uses half-open UTC intervals and stable `(timestamp,id)` keysets. The snapshot is an append-order watermark captured on the first page, rather than only the greatest event timestamp: a concurrently backdated event must not slip into a previously bounded export. Bind the cursor to the request and snapshot; reject tampered or mismatched cursors. Legacy rows do not need backfilled timestamps. The implementation must account for snapshot ordering across additive migration and restarts without rewriting historical quantities.

Validation failures return structured glitches; missing/cross-agent records return 404; stale review versions return 409; resource exhaustion returns a visible deferred receipt or explicit failure. No client-supplied actor/authority field is accepted in decision commands. Arbitrary source content cannot become instructions or a mutation request.

## Resource defaults and rollout

These are operational bounds, not calibrated semantic acceptance thresholds. Configurable values are validated against finite maxima. T15 owns evaluation targets and any exploratory budget promotion.

| Control | Initial default | Hard bound |
| --- | --- | --- |
| Active assessment queue per agent | 128 persisted work items | 1–1024 |
| Assessment workers per application process | 2 | 1–4; deployment records process count |
| Worker claim lease | 60 seconds | 15–300; restart recovers expired work visibly |
| Wait for evaluator capacity | 2 seconds | 0–5; persist defer on timeout |
| Evaluator call | 10 seconds outer bound | 1–30; existing provider timeout retained |
| Comparisons in assessment | 10 total | 1–10; include pending/adopted kinds when available |
| Nomination scan | 200 records total | At most 100 adopted, 64 pending/refined, 32 deferred, 4 dormant/history |
| New exploratory participation | Disabled; zero slots | Up to 2 slots only after evaluated opt-in |

Semantic nomination limits do not constrain indexed exact-repeat checks. Completed receipts survive queue exhaustion. Intake persists a minimal source-bound defer/failure before returning, or reports that receipt persistence itself failed. It never silently drops a candidate or treats an evaluator outage as approval. Database leases, final identity checks, and receipt commits are bounded transactions; no provider await holds a database connection.

Each origin has an independent intake flag and a durable promotion marker. Before an origin is promoted, the explicit chat/dream route retains the existing admission service; other legacy creators remain identified as unpromoted. New v2 origin flags default off until their T6–T8 parity gates pass. Once promoted, disabling its evaluator/intake participation pauses assessment and retains encounters; it cannot silently reopen direct proposal/belief creation. Rollback retains additive schema, receipts, and the promotion marker. Disabling exploratory participation restores its zero-slot budget without deleting candidates or dissent. Existing `belief_admission.jev_shadow` remains the advisory flag, with no new adoption authority.

## Adversarial review findings

| Evidence | Failure in a naive implementation | Required correction |
| --- | --- | --- |
| `belief_engine._accrete_belief` and legacy decay rejection | Map every rejected proposal to operator decline | Nullable canonical decision; legacy status retained |
| `skill_workshop._apply`, `belief_proposal._resolve_target_belief` | Treat bridge crystallization as adopted semantic claim | Derived projection provenance and separate adoption decision |
| `belief_triage.recompute`, admission relation questions | Treat endorsement as equivalence | Versioned lossy mapping with explicit insufficient-context reason |
| `AdmissionRepository.finish/comparisons` hardcodes Symbia | Reuse the ledger without agent-qualified identity/state checks | T5 must add agent predicates and validate every source/comparison link |
| Existing proposal vet request contains no review version | Permit concurrent reviewed decisions to overwrite | Expected version/state and atomic append/check in T11 |
| Existing assessment semaphore has unbounded waiters | Claim bounded workers alone bound review work | Persisted finite queue, bounded capacity wait, visible deferral |
| Timestamp-only export cursor | Admit later inserted, backdated records into a frozen export | Append-order snapshot watermark bound to the cursor |

The executable shape and adapter checks cover these boundaries. T5 must validate source identity, agent ownership and database links; T11 must enforce the complete action/state transition matrix and authorization atomically; T12 must implement authenticated snapshot cursors. Schema validation alone cannot establish factual warrant or authenticated provenance.

The recovered Symbia consultation is preserved in [Report 048](../reports/048-belief-v2-contracts/README.md). Her warning is that a bare adopted label can launder procedural habit into semantic authority, and that a schema preserving dissent can still lose it during prompt assembly. The contract binds standing to an actual decision; T14/T15 retain responsibility for participation behavior and replay evidence. Her proposed automatic calibrated gate is not adopted: the initial commitment boundary remains authenticated operator review, and warrant dimensions remain open and nonexclusive. No belief standing grants tool execution authority.

## T10 forward source-accounting boundary

Migration 066 adds immutable `belief_source_observations` and `belief_review_events`, atomic with newly registered encounters. Retries and assessments do not add observations. Source/lineage declarations remain distinct from verified independence; current resolvers establish no verified independent credit. Recorded recurrence uses existing scoped claim identity and excludes pre-migration coverage. Bounded agent-scoped typed reads expose truncation and historical-unrecorded counts. New accounting events retain quantity/unit/value and zero accounting-only mass/confidence changes; legacy events remain unchanged. Same receipt observation reaches page/history/traces. [ADR-123](../decisions/ADR-123-belief-source-accounting.md), [guide](../guides/belief-source-accounting.md), [Report 057](../reports/057-belief-v2-source-accounting/README.md).

## T9 advisory assessment boundary

Optional `referent_contexts` preserve supplied validated scope/time and antecedents bound to candidate/comparison hashes; original encounters remain immutable. Empty contexts preserve pre-T9 checkpoint digests. Separate `belief_review.assessment.enabled` defaults false. Callable assessment and explicit chat/dream integration reuse the ledger, two-slot semaphore and versioned relation adapter. Active queue claims are atomic; T9 introduces no autonomous leased worker. The worker lease above remains a future scheduler contract.

Consequence, empirical grounding, artistic grounding and tension remain separate advisory judgments; conflict can survive uncertain warrant. Classifier inputs exclude prior verdicts. Bound quotation ancestry and internal interpretation stay distinct. Attempts retain predecessor links; outages/cancellation do not automatically replay. Page/history/trace projection retains current context and original uncertainty. [ADR-122](../decisions/ADR-122-advisory-belief-assessment.md), [guide](../guides/belief-advisory-assessment.md), [Report 056](../reports/056-belief-v2-advisory-assessment/README.md).

## T8 external representation boundary

Document/shared-note/web creators use independent default-off flags and the same durable promotion/receipt contract. Ready first parsed chunks and shared-note quotations are owned local representations; document summaries and caller note text cannot replace them. Representation availability, upstream independence and claim referent resolution remain separate. Web excerpts retain ambiguous upstream context. Versioned snapshots bind retries; note/document changes are stale at completion. No semantic/adoption authority is introduced. [ADR-121](../decisions/ADR-121-external-belief-origin-intake.md), [operator guide](../guides/belief-external-intake.md), [Report 055](../reports/055-belief-v2-external-intake/README.md).

## T11 authenticated workshop boundary

Agent-scoped family reads and operator commands now enforce server actor/authority/time, expected statement/state/version and final comparison/source checks. Migration 067 links immutable command annotations to the existing decision ledger; trace failure rolls back state and adoption representation. Exact retries return historical receipts. Adoption preserves stable IDs and existing structural quantities without scoring. Decline retains the candidate and a counter-trace through later adoption. Teachback reconstruction grants no eligibility or warrant; shared credentials establish no separate participant identity. Other declared positions require a verified declaration channel. Legacy managed writes are guarded at API and transaction boundaries. Historical relations/assessments are labelled before reuse. T16 owns linked revision/merge/supersession/resurfacing; T12 export is installed locally; T13 dedicated UI is installed locally. [ADR-124](../decisions/ADR-124-belief-workshop-review.md), [guide](../guides/belief-workshop-review.md), [Report 058](../reports/058-belief-v2-workshop-review/README.md).


## T12 installed export boundary

Migration 068 adds a completion sequence referencing existing admission receipts and export identity/generation metadata. Existing completed receipts carry `existing_receipt` indexing provenance; forward completion indexes in the existing transaction. No second payload ledger or historical reasoning is created. Snapshot cursors bind agent/resource/UTC interval/limit/database/append watermarks and last normalized timestamp/namespaced ID through a purpose-specific HMAC derived from operator authentication. Later backdated inserts and later completion cannot enter frozen pages. Restart preserves cursors; rotation invalidates them. Legacy edits/deletes/ownership changes cause explicit 409 restart, conservatively across agents.

List exports cover dated, agent-attributable rows at snapshot; assessments cover completed receipts only, with pending native detail reads available. Unknown dates count explicitly and prevent `interval_complete`. Reasoning retains native/legacy distinctions, actual receipt attribution and unknown fields. Decision comparison projection caps ten links with explicit truncation; original bounded link lists remain intact. No evaluator/adoption/mutation ports. Reads: three-second SQLite budget, ten-second aggregate projection checks, 256 KB stored payload cap, 2 MB response cap, visible 503 on exhaustion. Source date normalization may scan histories; production capacity is unverified. See [ADR-125](../decisions/ADR-125-belief-review-export.md), [guide](../guides/belief-review-export.md), [Report 059](../reports/059-belief-v2-export/README.md).


## T13 frontend review boundary

Native pages, workshop receipts, traces and creases use the same authenticated T12 detail projection and original agent/receipt/timestamp. Additive native history field `agent_id` supplies recorded ownership; historical gaps remain unknown. Five reasoning fields, warrant registers, source-accounting uncertainty and stored dissent remain separate. T11 commands bind current hash/state/version and retain exact retry identity; stale refresh invalidates old form. Legacy mutations require a successful unmanaged snapshot. No provider call, automatic assessment binding or inferred shared agreement. [ADR-126](../decisions/ADR-126-belief-review-interface.md), [guide](../guides/belief-review-interface.md), [Report 060](../reports/060-belief-v2-interface/README.md).

## T14 scoped participation boundary

Bounded agent-owned selection retains six-slot geometry and four-slot signature fallback; native candidates, legacy standing and current scoped adoption remain distinct. Optional exploratory slots default off/zero and cap at two. Existing spectral-node recall caps at two within four historical nominations; declined/superseded/proposal-only records cannot bypass opt-in. Scope, challenges and retained counter-traces accompany inert quoted context. Recall grants no independent warrant, mutation or skill/tool authority. Final assembly appends optional bounded selection receipts to existing activation provenance; actual chat/dream writers persist them with their message. Dream hotspot context is independently scoped; research shares framing without a new ledger. T15 owns replay/calibration; T18 rollout. [ADR-127](../decisions/ADR-127-belief-participation-selection.md), [guide](../guides/belief-participation.md), [Report 061](../reports/061-belief-v2-participation/README.md).

## T16 linked lineage boundary

An operator revision creates a new pending candidate linked to the adopted source; predecessor text, adoption receipt, dissent and assessments remain untouched. Successor starts at zero mass/confidence and receives no copied evidence. Supersession links a source commitment to a distinct, current adopted target using both statement hashes and expected versions; source text and adoption receipt remain readable under `superseded` standing. Resurfacing records operator attention against unchanged statement/standing, rejects attached assessments, and changes no warrant, mass or confidence. Legacy records remain unmapped until an explicit command establishes a link; no bulk semantic cleanup. Merge remains unsupported. Migration 069 adds immutable lineage links; application rollback retains additive history. [ADR-129](../decisions/ADR-129-belief-linked-lineage.md), [guide](../guides/belief-workshop-review.md).

## T18 V1 proposal replay boundary

`review_legacy_beliefs.py` previews one agent's pending/refined V1 proposals read-only, then optionally replays the bounded selection into existing V2 encounter/assessment records. Replay binds the exact V1 snapshot hash to its existing record ID; unchanged retry returns the same operation, changed snapshot is rejected. Legacy lifecycle, mass, confidence, suggested wording, and prior assessment fields are not V2 verdicts. Missing message-bound source/scope/time persists as ambiguous/unknown and yields `candidate_context_unavailable` before any provider call. The generated packet keeps legacy text escaped and inert and separates human annotations from persisted workshop decisions. No adoption, new proposal, duplicate row, migration, or automatic cleanup. [ADR-130](../decisions/ADR-130-belief-v1-review-replay.md), [operator guide](../guides/belief-legacy-review.md), [Report 073](../reports/073-belief-v2-legacy-review/README.md). T15 remains inconclusive/no-go; T18 production execution remains separately gated by V23.
