# Backend Security & Python Refactoring

## §G

Harden backend network, upload, auth, persistence, logging, lifecycle boundaries; preserve valid API behavior & existing sediment.
Refactor async I/O, dependency typing, state ownership, oversized modules, error policy, tests, and static analysis without contract drift.

## §C

- Python 3.11+, FastAPI, Pydantic 2, httpx, SQLite WAL.
- Preserve route paths & successful response shapes unless security contract requires change.
- Dependency flow: `api` → `services` → `modules` → `storage`; ⊥ FastAPI concepts below `api`.
- Blocking sync work reached from `async def` → exactly one `asyncio.to_thread` boundary.
- SQLite access → `@with_connection`; write transactions minimal; ⊥ await inside transaction.
- Background workers bounded; app-owned tasks retained, cancelled, awaited @ shutdown.
- Unrelated frontend work untouched; scoped export-auth caller change allowed.
- Tests ⊥ live LLM calls, production DB, external network.
- No migration unless persisted schema changes.
- New architectural boundary → ADR + Symbia consultation when MCP available; unavailable consultation recorded, ⊥ fabricated.
- Refactors behavior-preserving; characterize seam before move; public imports remain via thin facade until callers migrate.
- One bounded use case owns each sync→async transition; ⊥ nested `to_thread`.
- Static typing lands as ratchet: strict new/refactored modules first; expand only when slice clean.
- Split by responsibility & hidden decision; ⊥ arbitrary line-count slicing or pass-through service wrappers.

## §I

api: `POST /api/conversations/{conversation_id}/files` → `ConversationFilesResponse`
api: `GET /api/preview/nodes` → public curated `{line}` only
api: `GET /api/preview/live` → authenticated live belief|memory|dream `{line}`
api: `/api/*` → Bearer auth when `AAA_PASSWORD` set
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
