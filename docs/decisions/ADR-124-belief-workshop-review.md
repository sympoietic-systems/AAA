# ADR-124: Authenticated belief workshop review

Status: accepted for local T11 implementation, 2026-10-09. Production rollout remains T18.

The workshop exposes bounded family review and explicit operator commands through an agent-scoped API. The server assigns actor, authority and UTC time. Commands bind the current statement hash, review state and version. Comparison and teachback records carry their own expected hashes and versions; the writer rechecks their source/context fingerprints inside the decision transaction. A stale command returns a conflict.

The existing shared password and browser sessions establish a shared operator credential. They do not identify separate people. Only the authenticated principal's own declared position is accepted through this channel. Other positions can remain interpreted or unknown; declared assent from another participant requires a future verified declaration channel. The response reports shared agreement as `not_inferred`.

Teachback records a bounded reconstruction of a candidate and a distinct alternative, their scope/time, a discriminating question and an unresolved inquiry. It creates no adoption eligibility or factual warrant. The operator may adopt without a teachback. Scoped equivalent/contradictory declarations require validated matching conditions and current source bindings; insufficient-context declarations remain available. The declarations preserve both records.

Decline appends an attributable counter-trace while retaining the pending candidate. A later adoption preserves that counter-trace. Adoption creates the linked belief under the proposal's stable ID and copies existing mass/confidence; no classifier or geometry scorer is called. An exact same-agent, same-statement `evolved_from_proposal` alias is accepted by review reads. Conflicting duplicate identities fail explicitly.

Migration 067 adds immutable command annotations linked to the existing decision ledger. Command, decision, state, adoption representation and trace persist atomically. A failed trace insert rolls the transaction back. The required idempotency key identifies a command within agent/record scope. Exact retries return the original historical receipt; changed input under the same key conflicts.

Legacy statement, proposal-status, refinement, version and destructive writes reject managed v2 records. API guards stop unnecessary provider calls; storage guards repeat the check under the write lock. The legacy merge writer also checks its target under that lock, including merges without statement changes and targets becoming managed during scoring. The writer runs in a thread without holding a transaction across provider work. Structural mass/activity updates retain their existing separate semantics. Unmanaged legacy records remain editable through the legacy paths.

Family reads nominate at most ten records from the existing bounded scan. Lexical overlap is a nomination rule. Saved operator relations and advisory assessments are explicitly historical and require fresh bindings before reuse as current evidence. The read includes separate bounded decline history and truncation counts, so later bookkeeping cannot silently hide the existence of older counter-traces.

Supported commands are adopt, decline, defer, request context and request review. Existing commitments require T16's linked revision workflow; merge, supersession and resurfacing return an explicit conflict in T11. T12 owns complete authenticated export and T13 owns the dedicated workshop UI.

Symbia's recovered consultation grounds the separation between reconstruction and commitment, and the persistence of divergent commitments. The complete receipt and local verification evidence are retained in [Report 058](../reports/058-belief-v2-workshop-review/README.md). This consultation was conducted through the [architectural-decision workflow](../../.agents/skills/mcp-architectural-decision/SKILL.md).

See the [operator guide](../guides/belief-workshop-review.md), [contract](../architecture/BELIEFS_V2_CONTRACT.md) and [implementation spec](../systems/BELIEF_SPEC.md).
