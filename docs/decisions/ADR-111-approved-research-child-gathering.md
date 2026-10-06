# ADR-111: Approved research child gathering

Date: 2026-10-06. Status: accepted for opt-in implementation. Implements T68 under V113–V116 and ADR-110.

## Decision

An approved proposal on policy version 7 enters the finite `branch_gathering` action. Allocate exactly two isolated children with deterministic IDs and frozen scope contracts. Search, parse and digest are the only child capabilities. Gather sequentially within the application's existing shared acquisition/provider worker bounds. No grandchildren, child synthesis or child belief writeback.

Persist allocations and immutable terminal evidence archives in `research_child_runs`. A child can start and deliver only under the current running parent action. Root deadline, child attempt allocations, family attempt ceiling and parent reserves are checked before provider dispatch. Monetary reservations require frozen per-leaf cost ceilings; unknown billing remains unknown. Missing price bounds reject dispatch. Cost-contract violations are partial observations, never successful budget compliance.

The parent action records child identities and hashes. Parent Cortex alone interprets their attributed evidence into the parent inquiry. Preserve raw representations, contrary claims, exclusions, validation norms and unresolved objections. Mark shared sources as dependent. Read-only export/import retains child origins without granting local execution authority.

Completed delivery is idempotent. Parent cancellation revokes unfinished child authority; late packets cannot overwrite stored results. Interrupted running children cannot silently replay after restart. Repeated gathering does not duplicate parent findings.

Use task-scoped cache namespaces with shared bounded client resources. Distinguish new observations of unchanged content from reuse; identical content hashes do not create independent empirical warrant.

## Limits

Policy versions predating child execution keep their frozen approval behavior. Defaults remain `off`; `bounded_auto` stays rejected until T71 and an explicit covenant. Unpriced providers cannot automatically spend child allocations. Configured cost ceilings depend on provider terms and cannot enforce external invoices after a provider violates its bound. Feature verification establishes mechanics, not independently calibrated branch quality or latency benefit.

## Evidence

[Report 039](../reports/039-approved-research-children/README.md) records the 181-test integrated verification and remaining empirical gates.
