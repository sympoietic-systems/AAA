# Backend Security & Python Refactoring / Frontend Hardening

## §G

Harden backend network, upload, auth, persistence, logging, lifecycle boundaries; preserve valid API behavior & existing sediment.
Refactor async I/O, dependency typing, state ownership, oversized modules, error policy, tests, and static analysis without contract drift.
Implement frontend review: fail-closed sessions, explicit transport, safe Markdown/print, request ownership, modularity & progressive static gates.
Close conversation telemetry loop: metrics select observable, provider-supported interventions; next-turn uptake judges effect; benchmarks isolate causal contribution.
Revalidate conversation benchmark after participant cap removal; prove sensor referents before controller promotion.

## §C

- Python 3.11+, FastAPI, Pydantic 2, httpx, SQLite WAL.
- Preserve route paths & successful response shapes unless security contract requires change.
- Dependency flow: `api` → `services` → `modules` → `storage`; ⊥ FastAPI concepts below `api`.
- Blocking sync work reached from `async def` → exactly one `asyncio.to_thread` boundary.
- SQLite access → `@with_connection`; write transactions minimal; ⊥ await inside transaction.
- Background workers bounded; app-owned tasks retained, cancelled, awaited @ shutdown.
- Frontend review implementation authorized: session auth, explicit transport, Markdown policy, request ownership, modularity & quality ratchet.
- Tests ⊥ live LLM calls, production DB, external network.
- No migration unless persisted schema changes.
- New architectural boundary → ADR + Symbia consultation when MCP available; unavailable consultation recorded, ⊥ fabricated.
- Refactors behavior-preserving; characterize seam before move; public imports remain via thin facade until callers migrate.
- One bounded use case owns each sync→async transition; ⊥ nested `to_thread`.
- Static typing lands as ratchet: strict new/refactored modules first; expand only when slice clean.
- Split by responsibility & hidden decision; ⊥ arbitrary line-count slicing or pass-through service wrappers.
- Verification iteration → changed-boundary tests only; ⊥ repeat full backend suite after frontend/small edits (user preference 2026-09-25).
- Conversation calibration → offline first; live model only after focused gates; historical receipts immutable.
- Control experiments → identical model, prompt prefix, seed/routing where provider permits; ≥3 repeated runs per live arm.
- Metric intervention failure := kinematic gain with flat/negative task progress or dialogue uptake over next 2 participant turns.
- No persisted schema migration for intervention receipts; benchmark artifacts own causal traces.
- Participant simulator prompt requests 1–3 sentences; client ⊥ hard completion-token cap; provider/model limits recorded.
- Benchmark phase order: completion validity → receipt/isolation validity → sensor manipulation check → controller ablation.
- Invalid participant completion remains auditable but ∉ uptake/progress statistics.
- Historical Report 019 receipts immutable; corrected run receives new run id + report lineage.

## §I

api: `POST /api/conversations/{conversation_id}/files` → `ConversationFilesResponse`
api: `GET /api/preview/nodes` → public curated `{line}` only
api: `GET /api/preview/live` → authenticated live belief|memory|dream `{line}`
api: `/api/*` → Bearer API auth or bounded browser session when `AAA_PASSWORD` set
api: `POST/DELETE /api/auth/session` → same-origin session create/revoke; HttpOnly cookie
api: `/api/auth/verify` → auth status without credential disclosure
api: research export download → authenticated fetch/blob; ⊥ reusable secret query
domain: outbound fetch → validated URL, bounded redirects/body/time, typed failure
domain: file ingestion → bounded stream, cached path, queued digestion status
domain: backup → WAL-consistent SQLite snapshot + integrity verification
error: Glitch → `{status,kind,message,entity?,details?}`; ⊥ internal path/traceback
env: `AAA_PASSWORD` → optional local auth secret
env: upload limits & worker concurrency → positive bounded integers
env: outbound fetch limits & timeouts → positive bounded numbers
internal: `app.state.services` → typed `AppServices`; legacy state aliases temporary
internal: route → typed service use case → repository/module ports
internal: conversation serialization → app-scoped bounded lock registry
quality: `mypy` strict package allowlist → expands per completed refactor
internal: `homeostatic_recommendations` → chosen move + requested generation controls + applied control receipt
benchmark: conversation intervention receipt → pre-response metrics, intervention, outbound controls, response metrics, next-2-turn uptake/progress
benchmark: participant completion receipt → `{content,finish_reason,native_finish_reason?,usage,model,provider,validity}`
benchmark: validity summary → completion/format/empty/truncation rates + exclusion reasons
internal: unresolved-issue state → issue identity + status + prior mode/outcome + bounded conversation lifecycle

## §V

V1: ∀ dynamic outbound URL & redirect target → `validate_safe_url` before request.
V2: ∀ outbound body → streamed bytes ≤ configured type limit; redirects ≤ configured hops; time ≤ configured timeout.
V3: ∀ upload request → file count, per-file bytes, aggregate bytes bounded before digestion.
V4: ∀ uploaded file → sanitized name + allowed extension + magic-byte check + `safe_resolve_path` before persistence.
V5: upload processing memory ⊥ duplicate full-file buffers; worker concurrency ≤ configured limit.
V6: ∀ digestion job → terminal `ready|error|cancelled`; timeout/cancel cleans partial state & files per contract.
V7: `pytest` import ≠ auth bypass; tests use FastAPI dependency override.
V8: reusable auth secret ∉ query strings, access logs, browser history; credential compare constant-time.
V9: anonymous preview content ∈ curated public pool; live beliefs/memory/dreams require auth.
V10: backup of live WAL DB → SQLite online backup API + `PRAGMA integrity_check=ok` before retention prune.
V11: ∀ log sink & persisted error → secrets redacted after exception formatting.
V12: ∀ app-owned async task → retained handle + cancel/await during lifespan shutdown.
V13: API input strings, identifiers, arrays, pagination, `max_tokens` → explicit bounds at Pydantic membrane.
V14: client error payload ⊥ filesystem paths, SQL, credentials, traceback; internal log retains redacted stack fidelity.
V15: sync DB/file/CPU work ⊥ event loop; offload exactly once.
V16: service/module layers ⊥ FastAPI request/response/dependency types.
V17: existing successful public API contracts remain compatible except §I security changes.
V18: verification leaves ⊥ `*test*.db*`, scratch uploads, root/backend `__pycache__`.
V19: `.svg|.html|.htm` uploads blocked as active content; extension allowlist ≠ executable safety claim.
V20: rejected upload batch → ⊥ conversation/file DB mutation & ⊥ partial cache residue.
V21: user-controlled outbound fetch → automatic redirects disabled; each DNS result public at connection boundary.
V22: backend package `__init__.py` → import-safe; ⊥ eager cross-package re-export cycles.
V23: async route/service → sync DB/file/CPU use case crosses exactly one offload boundary; ⊥ direct sync repository call on event loop.
V24: FastAPI dependency getter → concrete annotated value or structured 503; ⊥ optional `Any`/silent `None`.
V25: app runtime dependencies owned by typed `AppServices`; lifecycle assembly/shutdown share same instance.
V26: conversation lock count bounded by active keys; locks app/loop-scoped; idle key removed.
V27: Pydantic mutable field default → `default_factory`; timestamps UTC-aware; project-owned test warnings = 0.
V28: module split preserves public behavior/import path; extracted module owns coherent policy & tests.
V29: service/module catches expected domain errors; broad catch only at process/API/worker boundary + redacted context + re-raise/terminal state.
V30: strict type checker passes configured refactor allowlist; new module enters allowlist in same task.
V31: route/controller owns HTTP translation only; orchestration & repository sequencing live in service use case.
V32: temporary `app.state.*` alias is object-identical to `app.state.services.*`; dependency overrides & lifespan teardown use same object.
V33: architecture debt inventory monotonic ↓; new sync-route/broad-catch exception requires explicit boundary rationale; T13 leaves sync-route inventory empty.
V34: dependent multi-repository mutation runs in one synchronous unit/transaction or explicit compensation; ⊥ await/offload between partial writes.
V35: temporary diverged `app.state.*` dependency override remains effective; alias rebind restores identity with `AppServices`.
V36: browser auth requires validated status; password never persisted; sessions bounded, expiring, revoked on logout/password rotation; bearer clients compatible.
V37: cookie-auth mutation requires same-origin Origin + custom CSRF header; remote cookies Secure/HttpOnly/SameSite; loopback HTTP supported.
V38: untrusted Markdown cannot supply arbitrary CSS/classes; annotation styling application-owned; raw HTML sanitized before rendering/export.
V39: async UI results/errors/loading commit only to current request/entity/session; polling single-flight & disposed with owner.
V40: API calls explicit; global fetch unchanged; credentials restricted to normalized same-origin API paths.
V41: hooks unconditional; frontend static debt monotonic down; new boundary modules strict; route failures recoverable.
V42: conversation metric state isolated by `conversation_id`; interleaving/restart replay = isolated replay within tolerance.
V43: ∀ metric-driven generation control → requested value recorded; provider-applied/unsupported status explicit; ⊥ silent claim of actuation.
V44: diffractive activation reachable for labeled persistent stagnation with ordinary vitality; productive deep focus false-positive rate ≤10%.
V45: intervention mode ∈ `clarify|counterexample|experiment|reframe|consolidate|compress`; selector uses pressure + resolution + uptake; repeated failed mode escalates or changes.
V46: intervention success judged from next ≤2 participant turns by task progress + uptake; velocity/novelty gain alone ⊥ success.
V47: benchmark arm changes exactly 1 controller dimension; receipt records model, provider, prompt hash, controls, seed availability, errors, latency.
V48: calibration winner requires no regression in DRR/Paskian health beyond 0.02 and improves uptake/progress with 95% bootstrap CI or remains explicitly inconclusive.
V49: receipt ordering explicit: human-turn metrics → intervention/control request → outbound request → agent-turn metrics → next-turn outcomes; ⊥ relabel post-response metric as trigger.
V50: controller state reconstructed from sediment or bounded by active conversation lifecycle; ⊥ unbounded process-local conversation maps.
V51: benchmark model calls resolve from LLM-provider configuration; ⊥ reuse public AAA application URL as an OpenAI-compatible endpoint.
V52: background semantic-knot embedding uses the registered `EmbedderModule.process` contract; integration test ⊥ mock-only legacy method.
V53: ∀ simulated participant completion → content + finish reason + usage + model/provider recorded; empty/truncated/missing provenance → invalid outcome.
V54: policy ranking requires participant validity ≥95% `finish_reason=stop`, ≥95% 1–3 sentences, 0 empty valid turns; gate failure → validity report only.
V55: causal receipt pre/post metrics independently sampled & temporally labeled; identical aliased snapshot ⊥ causal delta; unavailable post-state explicit `null`.
V56: ∀ live benchmark arm/repetition → isolated temporary DB + conversation/controller/background state; production DB writes = 0.
V57: control observability requires requested → forwarded/effective or explicit unsupported trace; nonempty mappings alone ≠ applied.
V58: boringness diagnosis requires predictable move + no participant state revision + unresolved issue unadvanced; repetition/disagreement alone ⊥ boredom.
V59: sensor manipulation corpus separates dead loop from productive focus, spiral return, and legitimate disagreement before live controller test.
V60: intervention selector includes `abstain`; transition receipt names actual predicate + prior mode/outcome; tests prove every mode reachable.
V61: unresolved-issue hypothesis tested active-memory vs write-only sham vs current selector; active arm changes memory read only.
V62: controller promotion requires ≥10 paired valid repetitions/scenario, counterbalanced order, positive state-revision effect, V48 health bounds, no disagreement-depth loss.
V63: annotation belief writeback uses the concrete repository contract for node creation, mass, and events; contract-shaped test required.
V64: lexical state/progress evaluators account for explicit negation; refusing a test, measure, or comparison cannot count as issue advancement.
V65: transient outbound web-crawl failures retain TLS/SSRF boundaries and yield empty crawl content; daemon cycle remains available.
V66: HTTP-200 LLM responses without a valid completion are typed provider glitches; credential rotation occurs only for authentication/rate-limit failures.
V67: empty token-truncated LLM completions are typed provider glitches; pools fall back without exhausting credentials, and interactive chat exposes a masked 502 provider glitch.
V68: belief proposal vetting & synthesis gracefully resolves procedural skill and bridge targets (`skill:*`); ⊥ 404 target not found on valid skill identifiers.
V69: web crawler detects PDF content and extracts font-aware headings/text via thread offload and temporary file cleanup; non-HTML academic PDFs ⊥ dropped or passed to HTML parser.

V100: Message insertion honors outer atomic rollback; invalid parent fails structurally; committed parent visible across worker connections.

V101: Skill audit reads checkpointed snapshot in SQLite URI read-only mode; activation gaps ≠ lifetime nonuse; archived skills ∉ pruning candidates; probe failure ≠ skill failure.
V102: Jev evidence triage ≤10 candidates; finite scores + confidence required; unknown IDs/uncertainty abstain; excluded sources inspectable; receipts survive task restart; no belief/vector authorship; default promotion requires calibration.
V103: Belief Jev service has no write port; similarity nominates only; mass weights stakes, never contradiction; mature confidence band retained; absorbability uncertainty cannot erase contradiction; prior verdict excluded from classifier state; matrix application fresh copy only + atomic stale-evidence rejection.
V104: SSRF unit verification uses deterministic public/restricted DNS fixtures; environment DNS cannot override safe fixture; restricted hostname resolution remains denied.

V105: bridge storage faults → propagate; PDF parser/I/O failures → bounded fallback; unexpected extraction faults → propagate + temp cleanup; dream budget transition state ! explicit optional tuple

V106: activation trace ! assembly-owned bounded IDs + selected/injected + origin; legacy NULL → unknown; chat/dream parity; provenance ≠ response influence; ⊥ automatic pruning

V107: belief classification ! statement-bound scope/time/provenance + explicit referent bindings; missing/ambiguous/stale context → abstain before model; replay ⊥ unvalidated context; held-out gold ! independent provenance + leakage check
V108: research calibration ! raw candidates before selection + source IDs/exclusion receipts; archived survivors ⊥ gold pools; independent relevance/quality/contrary/injection labels + frozen task-family splits; fallback ⊥ valid model trial; repeats ⊥ independent sample count; promotion ! reviewed downstream evidence

## §T

id|status|task|cites
T1|x|add security test fixtures + passing characterization tests for URL, upload, auth, logging, backup seams|V1,V3,V4,V7,V10,V11
T2|x|add bounded outbound fetch component + regression tests; migrate research/web HTTP call sites|V1,V2,V14,V17,V21,I.domain
T3|x|stream uploads to safe cache + regression tests; enforce count/per-file/aggregate/image limits & atomic rejection|V3,V4,V5,V13,V15,V19,V20,I.api,I.domain
T4|x|bound digestion subprocess queue + regression tests; add timeout, cancellation, terminal states|V5,V6,V12,V15,I.domain
T5|x|centralize auth config + regression tests; remove pytest/query bypass; use authenticated export fetch; split curated public vs authenticated live preview|V7,V8,V9,V13,V17,I.api,I.env
T6|x|replace file copy backup with configured SQLite online backup + restore tests; integrity-check; lifecycle ownership|V10,V12,V15,I.domain
T7|x|redact formatted exceptions/access URLs + regression tests; normalize Glitch domain/API boundary|V11,V14,V16,V17,I.error
T8|x|clamp request schemas + regression tests; remove FastAPI coupling from services; tighten typed dependencies/offloading|V13,V15,V16,V17,I.api,I.error
T9|x|write ADR; run focused + full pytest, ruff check/format; clean ephemeral artifacts|V1,V2,V3,V4,V5,V6,V7,V8,V9,V10,V11,V12,V13,V14,V15,V16,V17,V18,V19,V20,V21
T10|x|characterize sync-route/broad-catch/import/warning debt; add monotonic architecture tests; pin `mypy` + strict initial allowlist; correct stale auth docs|V8,V15,V16,V17,V23,V28,V30,V31,V33
T11|x|add typed `AppServices` assembly + required dependency helper; keep object-identical temporary `app.state.*` aliases; migrate dependency getters|V12,V17,V24,V25,V31,V32,V35,I.internal
T12|x|move conversation/history/agent/note/file/preview DB workflows into typed service use cases; offload once per use case|V15,V16,V17,V23,V24,V29,V30,V31,V33
T13|x|move research task/step/artifact DB workflows into typed services; isolate state transitions & transaction scopes; empty sync-route debt inventory|V10,V12,V15,V23,V24,V29,V30,V31,V33,V34
T14|x|replace `ChatService._conversation_locks` with app-owned bounded keyed lock registry + cancellation/concurrency tests|V12,V26,V30,I.internal
T15|x|replace Pydantic mutable defaults; use UTC-aware timestamps; fix unawaited `AsyncMock`; assert project-owned warning-free suite|V13,V17,V27
T16|x|split `MessageRepository` into core/history/vector-search/graph collaborators behind compatibility facade|V17,V22,V28,V30
T17|x|split `modules/llm_client.py` into provider protocol, HTTP providers, pool/rate-limit policy, JSON parser; preserve facade imports|V2,V8,V11,V17,V28,V29,V30
T18|x|split research orchestrator into state store, step executor, sedimentation sink; retain orchestrator facade & state-machine tests|V12,V15,V17,V23,V28,V29,V30,V31
T19|x|split belief service into query/proposal/mutation/version use cases; add narrow repository ports & atomic mutation tests|V10,V15,V17,V23,V28,V29,V30,V31,V34
T20|x|split dream daemon trigger policy/execution/maintenance jobs; retain lifecycle owner & bounded worker semantics|V5,V12,V15,V17,V23,V28,V29,V30
T21|x|define domain exception taxonomy/translation; audit refactored modules; install monotonic broad-catch boundary allowlist|V11,V14,V17,V29,V31,V33
T22|x|expand strict `mypy` allowlist across refactored slices; ADR; full pytest/ruff/type/frontend gates; clean artifacts|V17,V18,V23,V24,V25,V26,V27,V28,V29,V30,V31,V32,V33,V34,V35,I.quality
T23|x|frontend session/transport & Markdown regression tests + fixes|V8,V17,V36,V37,V38,V40
T24|x|isolate search/research/notes/chat requests; own notification polling|V39,V41
T25|x|extract chat/canvas responsibilities; tighten frontend quality gates; ADR & verification|V28,V30,V41
T26|x|add causal receipt + uptake/progress evaluator; replay historical baseline; archive run|V46,V47,V48,V49,I.benchmark
T27|x|isolate metric state by conversation; wire reasoning controls + applied-status receipt through provider boundary|V42,V43,V49,V50,I.internal
T28|x|test 3 diffractive activation hypotheses in isolated branches; adopt empirical winner|V44,V47,V48
T29|x|add progress-aware intervention selector + failed-mode progression; integrate regulator prompt|V45,V46,I.internal
T30|x|run focused/full offline + repeated live conversation benchmarks; compare causal arms; publish Report 019 + ADR|V42,V43,V44,V45,V46,V47,V48,I.benchmark
T31|x|run full ruff/format/mypy/pytest + frontend gates; clean ephemeral artifacts; reconcile article/report claims|V18,V30,V42,V43,V44,V45,V46,V47,V48,I.quality
T32|x|complete participant cap removal; return structured completion receipt; add invalid-turn filter + request/receipt tests|V46,V51,V53,V54,I.benchmark
T33|x|replace aliased trigger/response snapshots; implement effective-control observability + temporal receipt tests|V43,V47,V49,V55,V57,I.benchmark
T34|x|isolate temp DB, controller, conversation, consolidation per arm/repetition; assert production DB untouched|V42,V50,V56,I.benchmark
T35|x|run 2-pair × 8-turn validity probe; publish completion/format/exclusion audit; ⊥ policy ranking unless V54 passes|V53,V54,V56,I.benchmark
T36|x|build labeled dead-loop/productive-focus/spiral/disagreement corpus; validate boringness conjunction + state-revision evaluator|V44,V46,V58,V59,I.benchmark
T37|.|add bounded unresolved-issue state, `abstain`, predicate receipts, mode reachability; implement active/sham/current arms|V45,V50,V58,V60,V61,I.internal,I.benchmark
T38|.|run counterbalanced ≥10-pair multi-scenario ablation; exclude invalid turns; report dispersion, state revision, disagreement depth, health|V47,V48,V53,V54,V56,V59,V61,V62,I.benchmark
T39|.|publish Report 020 + ADR amendment; reclassify Report 019 as invalid causal ranking while preserving receipts|V48,V53,V54,V55,V56,V57,V62,I.benchmark
T40|.|run focused/full backend gates; regenerate figures; link check; clean ephemeral artifacts|V18,V30,V53,V54,V55,V56,V57,V58,V59,V60,V61,V62,I.quality
T41|x|recover empty truncated LLM completions; preserve credentials on nested retry provider errors; emit bounded dream-budget transitions|V66,V67,I.error
T42|x|unfilter skill-beliefs in UI, tag `[Skill]` vs `[Belief]`, resolve skill targets gracefully in `merge_proposal` and `synthesize_merge_statement`|V68,I.api
T43|x|add PDF content detection and fallback extraction via `SimpleChunkDigester` and `pdfplumber` in `RhizomeWebProbe.crawl`|V69,I.domain

T47|x|close message transaction and parent validation gaps|V100,V34,V17

T48|x|implement read-only skill vitality and adversarial evidence harness|V101,V56
T49|x|implement and calibrate opt-in Jev source screening and grounded web collision receipts|V102,V30
T50|x|implement dry-run Jev candidate review routing and inspectable tension matrix producer|V103,V30

T51|x|restore baseline failure boundaries and strict dream state typing|V105,V29,V30

T52|x|persist assembly provenance and audit coverage; review stale skill probes|V106,V101,V23

T53|x|guard belief context; export independent annotation corpus; implement held-out calibration gates|V107,V103,V56
T54|x|export real research queries; capture raw pools; independent annotation + frozen three-arm comparisons|V108,V102,V56

## §B

id|date|cause|fix
B1|2026-09-23|`backend.services.__init__` eager imports → `services.file` circular import|V22
B2|2026-09-23|`backend.api.routes.__init__` eager compatibility re-exports → route import cycle|V22
B3|2026-09-23|ambient `AAA_PASSWORD` made unrelated route tests environment-dependent|V7
B4|2026-09-23|`backend.core.__init__` eager exports expanded leaf imports/type-check scope across packages|V22
B5|2026-09-23|new architecture test imports violated configured stdlib ordering|V30
B6|2026-09-23|`backend.bootstrap.__init__` eager exports evaluated type-only names during leaf import|V22
B7|2026-09-23|typed dependency getter ignored a diverged legacy state override and leaked stale app state across tests|V35
B8|2026-09-23|lazy imports let dotenv repopulate deleted test auth secret after fixture setup|V7
B9|2026-09-23|required-dependency migration replaced the concrete default agent identity with an unnecessary 503|V24
B10|2026-09-23|service factory bypassed a diverged legacy repository override by injecting the typed container|V35
B11|2026-09-23|agent use-case extraction left an unused route import rejected by Ruff|V30
B12|2026-09-23|conversation use-case extraction introduced a broad service-layer embedding catch|V29,V33
B13|2026-09-23|typed dependency additions duplicated an import instead of extending the existing import|V30
B14|2026-09-23|moving preview selection into services exposed four broad fallback catches to the debt ratchet|V29,V33
B15|2026-09-23|new service modules entered strict mypy with route-era bare collections and heterogeneous selector output|V30
B16|2026-09-23|silent legacy imports erased repository return types at the new strict service boundary|V30
B17|2026-09-23|final static gate found split imports from the same contract modules in the architecture test|V30
B18|2026-09-23|research lifecycle adapter aliases were not in Ruff's canonical import order|V30
B19|2026-09-23|T13 route offloading edits passed lint but missed Ruff's formatting gate across eight files|V30
B20|2026-09-23|adding an AppServices default factory shadowed the existing `field` loop variable|V30
B21|2026-09-23|removing ChatService's class locks left its `asyncio` import unused|V30
B22|2026-09-23|the ChatService lock rewrite missed Ruff's formatting gate|V30
B23|2026-09-23|untyped `with_connection` erased repository signatures and hid stale downstream casts|V30
B24|2026-09-24|LLM extraction carried bare mappings and untyped provider kwargs into the strict allowlist|V30
B25|2026-09-24|narrowing parser exceptions left the extracted module outside Ruff's canonical format|V30
B26|2026-09-24|step executor extraction passed the collaborator where phase processors require the orchestrator facade|V17,V28
B27|2026-09-24|legacy defensive routing-patch branch obscured the typed `RoutingPatch` contract|V30
B28|2026-09-24|executor extraction relocated approved orchestration catches to an unbaselined path|V29,V33
B29|2026-09-24|mechanical executor extraction missed Ruff formatting in both touched modules|V30
B30|2026-09-24|sedimentation-sink wiring changed a formatted call block without rerunning Ruff first|V30
B31|2026-09-24|belief extraction exposed implicit state attributes, bare result mappings, and hidden compatibility exports|V30
B32|2026-09-24|atomic rollback test used nested context managers rejected by the Ruff simplification gate|V30
B33|2026-09-24|belief-service extraction relocated approved boundary catches to unbaselined module paths|V29,V33
B34|2026-09-24|typed repository-port import left the query collaborator outside Ruff formatting|V30
B35|2026-09-24|daemon extraction split a method signature from its maintenance body|V17,V28
B36|2026-09-24|daemon extraction relocated approved boundary catches to unbaselined module paths|V29,V33
B37|2026-09-24|error-taxonomy edit left an intentional compatibility export implicit and a new test unformatted|V17,V30
B38|2026-09-24|strict typing exposed research metabolism calling an attribute that was never initialized|V17,V29,V30
B39|2026-09-24|typing expansion left import order and formatting outside Ruff's canonical form|V30
B40|2026-09-24|ADR metadata used Markdown hard-break spaces and the commit sequence did not stop after `diff --check`|V30
B41|2026-09-24|legacy-import migration left four import blocks + one package file outside Ruff canonical form|V30
B42|2026-09-25|cold strict-mypy run exposed duplicate branch-local annotation for LLM request body|V30
B43|2026-09-25|LLM request-body annotation fix missed Ruff format gate|V30
B44|2026-09-25|new quality protocol used a Markdown hard-break space rejected by the commit whitespace gate|V30
B45|2026-09-25|login trusted HTTP 200; malformed auth JSON implied auth disabled|V36
B46|2026-09-25|Markdown schema allowed arbitrary style/classes; renderer applied supplied CSS|V38
B47|2026-09-25|conditional research hooks & unowned async completions crossed entity boundaries|V39,V41
B48|2026-09-25|notification polling inferred auth from persistent password; global fetch hid transport policy|V36,V39,V40
B49|2026-09-25|new TypeScript error class used constructor parameter properties forbidden by erasableSyntaxOnly; replaced with explicit fields|V41
B50|2026-09-25|shared Markdown plugin extraction removed a still-used KaTeX import; migrated remaining render site|V38,V41
B51|2026-09-25|new backend session code missed canonical Ruff format; format before final gates|V30
B52|2026-09-25|canvas extraction retained whitespace-only lines; staged diff check caught them before commit|V30
B53|2026-09-25|adaptive participant simulator reused public `AAA_API_BASE` and sent model requests to a non-LLM route|V51
B54|2026-09-25|participant simulator forwarded AAA's provider-qualified model alias to the OpenRouter wire API|V51
B55|2026-09-25|participant simulator sent a chat completion whose final message had assistant role|V51
B56|2026-09-25|participant simulator reasoning consumed its response budget and emitted clipped prompt fragments|V46,V51
B57|2026-09-25|semantic-knot service called removed mock-only `EmbedderModule.embed_text`; live compaction failed|V17,V52
B58|2026-09-25|progression test assumed the rejected experimental policy remained the production default|V48
B59|2026-09-25|T30 commit sequence did not stop after Markdown whitespace failure|V30
B60|2026-09-25|full format gate found two earlier benchmark-branch files outside Ruff canonical form|V30
B61|2026-09-25|sandboxed Vitest could not load Tailwind's native Windows binding; rerun with build-equivalent access|V30
B62|2026-09-26|report plot treated universally undefined first-turn metrics as numeric aggregates and failed lint ordering|V30
B63|2026-09-26|human-readable report header used Markdown hard-break whitespace rejected by the diff gate|V30
B64|2026-09-26|participant hard token cap + discarded completion metadata yielded 1–8-word followups scored as dialogue|V53,V54
B65|2026-09-26|benchmark passed same turn list as trigger/response inputs; 48 receipts duplicated metric snapshots|V55
B66|2026-09-26|control coverage treated nonempty request/applied mappings as proof of actuation|V57
B67|2026-09-26|live arms shared runtime DB + background consolidation state|V56
B68|2026-09-26|Report 019 attributed ladder resets to uptake despite pressure/streak selector predicates|V60
B69|2026-09-27|scar-fold belief writeback retained obsolete repository argument, mass, and event names; live benchmark logged TypeError and dropped events|V63
B70|2026-09-27|boringness evaluator counted “do not want a test” as issue advancement and missed a near-duplicate at the threshold edge|V58,V64
B71|2026-09-29|Windows test worker lacked permission to create the default pytest temporary root; use an explicit writable temporary base for verification|environment
B72|2026-09-29|certificate-verification failure from a harvested remote page escaped the crawl fallback and terminated the dream daemon cycle|V65
B73|2026-09-29|HTTP-200 upstream LLM error envelope was indexed as `choices` and poisoned model/key exhaustion state|V66
B74|2026-09-29|empty token-truncated completion was treated as a successful call, then surfaced from interactive chat as a validation 400|V67
B75|2026-10-02|filtering `skill:*` beliefs hid suggested merge targets and targeting skill IDs threw 404 in proposal use cases|V68
B76|2026-10-02|crawler fed binary PDF payloads into HTML parser, discarding academic search results|V69


B77|2026-10-03|message insert directly committed inside atomic scope; missing parent surfaces raw foreign-key exception|V100

B78|2026-10-03|audit URI lacked uri=True; live harness passed unsupported prompt keyword; archived skills falsely flagged for pruning|V101
B79|2026-10-03|triage receipt omitted from orchestrator persistence allowlist; numeric answer inference lost strict collection type|V102,V30
B80|2026-10-03|absorbability confidence incorrectly gated contradiction; synthetic seed violated belief origin and anchor schema|V103,V23
B81|2026-10-03|SSRF unit test depended on live DNS; example.com resolved to restricted benchmark network here and correctly failed closed|V104,V23

B82|2026-10-03|bridge faults disguised missing targets; PDF catch hid unexpected faults; dream tuple inferred None|V105

B83|2026-10-03|provenance serializer imported prompt builder from storage → cognitive import cycle; pure schema moved storage leaf|V22,V106
