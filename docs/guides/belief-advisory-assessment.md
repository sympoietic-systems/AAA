# Advisory belief assessment

[BELIEF_SPEC](../systems/BELIEF_SPEC.md) owns T9 status; [ADR-122](../decisions/ADR-122-advisory-belief-assessment.md) records its boundaries.

`belief_review.assessment.enabled` independently defaults false. The 0.85 confidence floor is provisional, not calibrated. Capacity wait defaults two seconds (maximum five), outer call timeout ten (maximum thirty), active queue 128 per agent (maximum 1024). Two existing evaluator slots are shared with legacy admission per process; deployment must account for process count.

Enabled explicit chat/dream intake invokes the use case. Trusted internal callers can supply exact typed scoped context to `assess_encounter` for other owned encounters. Missing context abstains. Supplied scope does not establish upstream independence or factual support, and preserves the original encounter. No autonomous worker or public assessment endpoint is installed.

Inspect candidate admission history and match assessment IDs to received/assessed traces. They retain context, comparison snapshots, raw/adapted relations, separate grounding dimensions, consequence/challenge, model availability and exclusions. Earlier receipts and original context remain historical. Conflict with uncertain usefulness remains reviewable; no assessment changes adoption or legacy quantities.

Same-attempt retry reuses its pending/completed/failed outcome without a provider replay. Changed input rejects stale replay. Explicit reassessment uses a new attempt ID and links its predecessor. Timeout, exhaustion, outage, malformed output, cancellation and changed bindings remain visible. Hard interruption uses T5 checkpoint recovery; pending is not replay authorization. Requested model and nullable provider-reported model remain separate.

Offline mocked gates prove application boundaries, not semantic accuracy. Independent calibration remains T15; authorized rollout/rollback T18. [Report 056](../reports/056-belief-v2-advisory-assessment/README.md) owns verification receipts.

T10's separate [source-accounting ledger](belief-source-accounting.md) records newly registered encounters. Running or repeating an assessment cannot increment its source activity, recurrence or independent-support credit. Source observations and advisory warrant dimensions remain separate in receipt projection.
