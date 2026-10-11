# Belief review export

T12 installs read-only backend exports. Production rollout remains T18; dedicated page/workshop/creases integration remains T13.

Use the existing authenticated session or bearer credential. Authentication must be configured. The namespace is `/api/beliefs/v2/agents/{agent_id}`; selecting an agent does not establish a participant declaration.

| GET path | Stored resource | Interval timestamp |
| --- | --- | --- |
| `/encounters` | Immutable encounters | `received_at` |
| `/assessments` | Completed native and attributable legacy admission receipts | `assessed_at` |
| `/decisions` | Immutable attributed review decisions | decision `timestamp` |
| `/events` | Native source-accounting events and legacy belief events | event `timestamp` |
| `/encounters/{id}` | One native encounter | original receipt |
| `/assessments/{id}` | One native assessment, including pending | original receipt |
| `/decisions/{id}` | One native decision | original receipt |

For each list request, supply `from` and `to` as aware ISO timestamps. The server normalizes offsets to UTC; `to` is exclusive. `limit` defaults to 25 and must be 1–50. Unknown or repeated query parameters are rejected. Example path:

```text
/api/beliefs/v2/agents/symbia/events?from=2026-10-01T00%3A00%3A00Z&to=2026-11-01T00%3A00%3A00Z&limit=25
```

Continue using `next_cursor` with the same agent, resource, normalized interval and limit. A cursor carries the first page's signed append snapshot. It survives process restarts with the same database and credential. Changing the credential or request bindings invalidates it. Snapshot metadata is ordering information, not evidence of truth.

Preserve each item's original `id`, namespaced `export_id`, timestamp and `reasoning_sources`. Namespacing distinguishes native and legacy IDs during ordering without rewriting original IDs. The five reasoning fields are always present:

1. `encounter`: the stored encounter or explicitly linked encounters/source trace.
2. `claim_or_tension`: stored statement/hash/scope/trigger as available.
3. `comparison`: stored comparison snapshots and relation observations.
4. `consequence_or_challenge`: the recorded consequence and challenge.
5. `decision_or_uncertainty`: evaluator uncertainty or attributed operator decision/dissent.

`source_accounting` carries T10 immutable observations, including recorded recurrence, internal activity, declared ancestry grouping and verified-independent-group count. Missing observations remain null; observation completeness never establishes independent warrant.

Null fields appear in `unknown_reasoning_fields`; no missing legacy reasoning is invented. A decision's comparison projection includes at most ten linked assessment receipts and sets `comparison_truncated` if necessary. Follow the original `assessment_ids` through individual reads for further detail. Operator declarations remain distinct from legacy advisory decisions. Every export reports `tool_authority=none`; these routes do not evaluate, adopt, reclassify or recalculate beliefs.

`interval_complete=true` appears only after cursor exhaustion with zero undated rows. Read it together with `coverage=stored_dated_rows_at_snapshot` and `assessment_coverage=completed_receipts_only`. Keep every preceding page; the last page alone is not the full interval. Missing/unparseable legacy dates cause `undated_rows>0` and incomplete coverage even if no cursor remains. No export can establish the completeness of unrecorded history or the independence of a source.

Legacy `impact_score` and deprecated `delta_confidence` carry generic impact. `confidence_delta` is the measured confidence delta, and `delta_mass` is the measured mass delta; unknown values stay null. Native source-accounting events use `encounter_observation` and cannot contribute independent warrant. Redacted responses set `content_redacted=true`; storage and recorded hashes remain intact, so a redacted display cannot be used as the original hash input.

On 400, correct the interval or restart with a fresh cursor. On 404, check the selected agent and native record ID. On 409, restart the export: mutable legacy history or the database snapshot changed. Legacy generation invalidation is conservative across agents. On 503, reduce the page size for stored-payload/projection budgets; exceptionally large timestamp-normalization scans may need a follow-up indexed-read improvement. A failed request never yields a complete-interval claim.

Migration 068 creates only completion references and export metadata. It labels existing completed receipt references `existing_receipt` and later completions `forward_completion`; it does not populate missing reasoning or manufacture historical events. It does not enable v2 intake or adoption flags.

See [ADR-125](../decisions/ADR-125-belief-review-export.md), the [frozen contract](../architecture/BELIEFS_V2_CONTRACT.md) and [Report 059](../reports/059-belief-v2-export/README.md).
