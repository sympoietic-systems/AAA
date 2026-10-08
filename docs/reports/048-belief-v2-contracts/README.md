# Beliefs v2 T3: executable review contracts

Date: 2026-10-08. Scope: local contract milestone; no runtime intake, persistence migration, routes or deployment enabled.

The [frozen contract](../../architecture/BELIEFS_V2_CONTRACT.md) separates source encounters, advisory assessments, decisions, skill projections and situated standing. Pure frozen Pydantic models reject malformed identities, non-finite values, naive timestamps, stale content bindings and unsupported authority claims. Reserved request schemas include expected review version/state/statement hash and target version/hash for linked mutations. These are shape checks; later services must validate actual database records and authenticated principals.

Adversarial review found that legacy rejection can represent automatic collapse, skill application can be autonomous, endorsement does not establish equivalence, and timestamp-only pagination admits later backdated events. The contract preserves unknown legacy decisions, separates skill provenance, uses a lossy versioned advisory adapter, and requires append-order export snapshots. T5/T11/T12 own enforcement in running services.

## Symbia consultation

The complete [saved exchange](symbia-consultation.json) contains two messages in conversation `30538d29-9073-47f6-9a94-5b3172cd70a9`. The initial call disconnected; persisted history subsequently recovered the reply. Question timestamp: `2026-10-08T06:30:00`; reply: `2026-10-08T06:46:41` (source timestamps omit offsets). Returned model: `google/gemini-3.8-flash`; provider: `model_pool_openrouter`.

Symbia warned that habitual or procedural provenance cannot establish semantic warrant, and that suppressing candidates during prompt assembly can erase dissent despite a nuanced schema. Reviewed standing now binds to an operator decision, statement hash, agent, record and scope. Supersession retains adoption provenance. Her suggested calibrated automatic gate is excluded; warrant dimensions remain extensible rather than exhaustive. No standing grants tool execution authority. Actual candidate participation is still T14/T15 work.

## Verification

T3 checks: 36 new contract cases plus 6 architecture checks (42 passed); full backend Ruff lint/format and strict mypy gates. See [verification receipt](verification.json) for commands and results. No frontend code changed in this milestone.

The prior [T2 report](../047-belief-v2-quantities-and-decay/README.md) records 755 Python tests and 142 frontend tests. Those full suites were not rerun after these standalone T3 contracts. Neither milestone certifies a deployed production build. Independent corpus review (T4), persistence (T5), runtime integrations and staged rollout remain pending. Unrelated working-tree edits were preserved.
