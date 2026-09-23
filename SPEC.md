# Backend Security & Refactoring

## §G

Harden backend network, upload, auth, persistence, logging, lifecycle boundaries; preserve valid API behavior & existing sediment.

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

## §T

id|status|task|cites
T1|x|add security test fixtures + passing characterization tests for URL, upload, auth, logging, backup seams|V1,V3,V4,V7,V10,V11
T2|x|add bounded outbound fetch component + regression tests; migrate research/web HTTP call sites|V1,V2,V14,V17,V21,I.domain
T3|x|stream uploads to safe cache + regression tests; enforce count/per-file/aggregate/image limits & atomic rejection|V3,V4,V5,V13,V15,V19,V20,I.api,I.domain
T4|x|bound digestion subprocess queue + regression tests; add timeout, cancellation, terminal states|V5,V6,V12,V15,I.domain
T5|.|centralize auth config + regression tests; remove pytest/query bypass; use authenticated export fetch; split curated public vs authenticated live preview|V7,V8,V9,V13,V17,I.api,I.env
T6|.|replace file copy backup with configured SQLite online backup + restore tests; integrity-check; lifecycle ownership|V10,V12,V15,I.domain
T7|.|redact formatted exceptions/access URLs + regression tests; normalize Glitch domain/API boundary|V11,V14,V16,V17,I.error
T8|.|clamp request schemas + regression tests; remove FastAPI coupling from services; tighten typed dependencies/offloading|V13,V15,V16,V17,I.api,I.error
T9|.|write ADR; run focused + full pytest, ruff check/format; clean ephemeral artifacts|V1,V2,V3,V4,V5,V6,V7,V8,V9,V10,V11,V12,V13,V14,V15,V16,V17,V18,V19,V20,V21

## §B

id|date|cause|fix
B1|2026-09-23|`backend.services.__init__` eager imports → `services.file` circular import|V22
