# Research V2 Specification

Status: partially implemented; T62–T69 and explicitly requested T73–T74 complete; T69 experimental promotion authorized on provisional LLM labels; T70–T72 release gates open. Not a completed release.
Owner: Research V2 task sequence in root [SPEC.md](../../SPEC.md).
Rationale and evidence: [RESEARCH_V2_PROPOSAL.md](RESEARCH_V2_PROPOSAL.md).
Implementation snapshot and operating references: [RESEARCH_V2_PROGRESS.md](../guides/RESEARCH_V2_PROGRESS.md).

## §G Goal

Deliver evidence-grounded research with adaptive but auditable action order, reliable extraction, bounded resource use, optional subresearch, and verifiable synthesis. Preserve useful current interfaces and make uncertainty, disagreement, delay and partial work visible.

## §C Constraints

- Existing research task and dispatch behavior remains compatible when new options are omitted.
- `max_breadth` remains query breadth; it does not mean child-research count.
- Cortex owns objective, action selection, branch cuts and final synthesis. Jev advises/ranks/abstains; it cannot author evidence, silently remove a line, spend budget, or commit beliefs.
- Scheduler selects only registered actions. Deterministic validation enforces prerequisites, artifact versions, remaining budget, deadlines, fanout and task state before execution.
- Reflection may inspect initial framing. A second consecutive pass requires an afferent trace that makes current categories or retrieval coordinates fail, and must change the inquiry cut. Internal reflection adds no empirical warrant.
- Initial consecutive-reflection cap: 2 passes total. First pass is framing; second requires an explicit contradiction, category failure or consequential exclusion. Zero cut change exits reflection.
- Subresearch MVP policies: `off|propose`; default `off`. `bounded_auto` stays disabled until independent branch calibration passes T71 and each task carries an explicit bounded covenant.
- Branch only after initial afferent contact reveals genuinely incommensurable retrieval vocabularies or validation norms. Complexity, facet count, or expected speedup alone does not justify a cut.
- Child gathering is isolated. Child outputs preserve raw evidence and conflict; only parent Cortex synthesizes. Do not branch coupled relational questions whose meaning depends on interaction among facets.
- Child work shares one parent budget and deadline. MVP cap: 2 children; no grandchildren. Reserve capacity for parent verification and synthesis before approving any child spend.
- A declined or expired proposal starts no child and consumes no child budget; parent continues as one research line.
- Parser routes operate within existing SSRF, TLS, byte, time and worker-concurrency boundaries. External page content is untrusted evidence, never executable instruction.
- Provider attempts and total wait are bounded. Truncated output cannot satisfy a complete-result contract. Preserve available partial evidence and report degraded/partial state when recovery budget is exhausted.

## §I Interfaces

### Dispatch

Extend `POST /api/research/dispatch` payload with optional `subresearch_policy: off|propose`. Omitted value = `off`. Keep current `{task_id,status}` response shape. Persist selected policy with task so resume/restart cannot change it silently. Do not enable `bounded_auto` in MVP.

Add durable task state `waiting_for_branch_approval`. Proposal includes branch question, rationale, evidence for incommensurability, distinct evidence/validation plan, overlap, risk and shared-budget allocation. Approval may edit scopes within parent objective and budget. Decline/expiry resumes parent without child spend.

### Research action receipt

`ResearchActionReceipt` fields: `action_id`, `task_id`, registered `kind`, `intent`, `input_version`, `dependency_ids`, `rationale`, `budget_reserved`, `deadline`, `status`, `output_refs`, `started_at`, `completed_at`. Persist before execution and on terminal transition. IDs make retries/resume idempotent.

### Evidence packet

`EvidencePacket` fields: source ID/version, raw span locator, claim IDs, support/contradiction links, extraction method/quality, excluded evidence and reason, unavailable evidence and reason, unresolved gaps. Child returns may add interpretation, but must label it separately from source evidence.

### Provider attempt receipt

Record task/action/request IDs, provider/model, start/end, attempt number, outcome/status, finish reason, truncation, cancellation, and bounded error category. Never put credentials or unsanitized private content in the receipt.

## §V Invariants

V1: Every scheduled action ∈ registered capability set; prerequisite, input-version, budget and deadline checks pass before execution.
V2: Action input/dependency/output receipts persist across restart; retry with same action ID cannot commit duplicate output.
V3: One initial framing reflection allowed; each additional consecutive pass needs afferent rupture + changed cut; max consecutive passes = 2 until evaluation changes cap.
V4: Internal reflection weight = 0; interpretations retain provenance; contradictions cannot be smoothed into unsupported consensus.
V5: Zero cut delta forces available evidence action, focused clarification, or explicit partial stop; ⊥ unbounded reflection loop.
V6: Branch proposal occurs only after afferent incommensurability is recorded; latency/facet count alone ⊥ warrant.
V7: MVP policy ∈ `off|propose`; child execution requires approval. `bounded_auto` requires T71 calibration + explicit task covenant.
V8: Child count ≤2, no grandchildren, one hard shared budget/deadline; synthesis reserve cannot be spent on children.
V9: Child packet preserves source/version/span, claim-support relations, extraction quality, exclusions, unavailable evidence, disagreement and gaps.
V10: Parent Cortex alone merges packets; conflicting claims remain visible with provenance and are not majority-voted away.
V11: Decline/expiry/failure/cancel returns parent to a valid state; unstarted/failed child spend and outputs remain explicit.
V12: Every provider attempt has correlated receipt; retry count and overall wait bounded by configured task deadline.
V13: `finish_reason=length`/truncated output is partial/degraded, never complete; recovery uses remaining budget or returns partial.
V14: Late result is accepted only for current action/version; stale or regenerated output cannot overwrite committed state or appear as an unrelated duplicate child.
V15: Completion ∈ `complete|partial|failed|cancelled`; `complete` requires report support/coverage contract. UI distinguishes queued/running, approval wait, degraded/partial and terminal status.
V16: Parsing preserves source identity, version and resolvable spans; OCR/layout uncertainty remains attached to derived claims.
V17: Jev screening requires calibrated abstention and inspectable exclusions; no activation or promotion from synthetic fixtures alone.

## §T Delivery Contract

Task IDs and ordering remain owned by root SPEC.md. Detailed exit gates:

| ID | Slice | Exit gate |
|---|---|---|
| T62 | Baseline and receipts | Restart/replay preserves action IDs, versions, dependencies, budget, and terminal state; metrics expose stage/provider attempt latency and time to first useful result. |
| T63 | Provider reliability | Simulated timeout, failover, truncation, cancellation and late completion terminate within budget; partial output is visible; no stale overwrite/duplicate commit. |
| T64 | Evidence substrate | Source/version/span links resolve after restart/export; exclusions, contradictory evidence and parser quality survive into claims. |
| T65 | Acquisition efficiency | Same frozen source pool; bounded concurrency, rate limits, reusable clients/cache and deadlines; improved latency without coverage regression. |
| T66 | Adaptive routing | Legal action paths pass prerequisites; repeated reflection obeys V3–V5; `pure_reflection` input/output mapping and restart/rerun dependencies work. |
| T67 | Proposal UX | `off` unchanged; `propose` waits durably; approve/edit/decline/expiry tested; no child spend before approval. |
| T68 | Child execution and merge | ≤2 isolated children; source spans and conflicts preserved; parent Cortex owns synthesis; restart/cancel/failure paths tested. |
| T69 | Jev selection | User-authorized experimental promotion on provisional LLM labels, 2026-10-06; held-out comparison complete; uncertainty uses standard-selector fallback. Independent quality and downstream release review remain T71. See [Report 042](../reports/042-jev-experimental-promotion/README.md). |
| T70 | Specialist parsing | Docling/OCR/specialist candidates evaluated on frozen corpus; adopt only measured accuracy/latency/resource/license fit; preserve locators. |
| T71 | Release evaluation | Compare v1, evidence/retrieval, Jev, reflection and proposal branches; include outages, late/truncated results and restarts; publish quality, latency and cost evidence. |
| T72 | Bounded automatic branching | Enable only after T71 branch calibration; explicit covenant, ≤2 children, shared budget/deadline and synthesis reserve enforced. |
| T73 | Optional standard-first Docling fallback | Default-off environment switch; isolated bounded CPU worker; standard extraction first; preserve both representations and unknown quality; cancellation/hash/cache regression checks. See [ADR-112](../decisions/ADR-112-standard-first-docling-fallback.md) and [usage guide](../guides/DOCLING.md). T70 remains open. |
| T74 | Automated provisional source labeling | NVIDIA command validates exact source coverage, checkpoints/resumes, preserves model/input provenance and failure receipts; automated labels do not bypass independent-gold gates. See [labeling guide](../guides/RESEARCH_LABELING.md). |

## §B Initial findings and remaining gaps

- T66 corrected the `pure_reflection` envelope mapping and persists finite routing decisions, patch TTL, and reroute count. Unsupported insert/remove patches fail explicitly; they are not implemented capabilities. See [Report 037](../reports/037-research-finite-actions/README.md).
- T62–T66 add durable action/dependency/version boundaries and finite prerequisites. They do not authorize arbitrary model-authored replanning; legacy phase behavior remains available under frozen policy.
- Current production log excerpt showed truncation, upstream 503s, timeouts and delayed sibling outputs. It lacks conversation-level correlation; treat as reliability fixture, not a calibrated latency baseline.
- T69 experimental activation uses the explicit user exception above; T70–T71 still require independent labels/review and integrated release evidence. T73's native-text routing tests do not establish semantic parser accuracy or scanned-PDF OCR correctness.

## Non-goals

- ⊥ activate Jev source selection before held-out calibration.
- ⊥ automatic child creation in MVP.
- ⊥ arbitrary model-authored phases, recursive child trees, or branch-for-speed policy.
- ⊥ replace every parser before a frozen comparative corpus demonstrates need.
- ⊥ call reflective prose independent evidence or resolve productive contradiction merely to complete a report.
