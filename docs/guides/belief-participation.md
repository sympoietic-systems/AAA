# Belief participation in chat and dreams

T14 installs bounded selection and framing locally. Production enablement remains T18; T15 owns the participation replay and budget acceptance. Keep the default configuration:

```yaml
belief_review:
  participation:
    enabled: false
    slots: 0
```

After evaluated opt-in, `enabled: true` permits zero, one or two exploratory slots. Other types, larger budgets, unknown fields and a nonzero disabled budget fail validation. These controls are independent of origin-intake and assessment flags. Disabling participation returns its budget to zero; receipts, candidates and dissent remain stored. Configuration alone supplies no evaluation or rollout authorization.

The normal window preserves its mass anchors, structural stress, afferent salience and resonance slots. Existing dormant-node recall stays bounded to two items from four historical nominations. Review state is separate from lifecycle, mass and legacy confidence. `legacy_unreviewed`, provisional, stale/unverified adoption and situated commitment remain visible. A situated commitment identifies an actual current operator receipt; it gives no factual verification or tool authority.

Exploratory slots nominate friction and a resonant counterpoint. A candidate or dormant record can orient a question, comparison or scoped inquiry. Decline does not erase the record or its attributed counter-trace. The projection includes the most recent recorded decline and marks bounded history; older counter-traces remain available in the workshop. Proposal-only declined records cannot enter the always-on spectral path. Selection itself does not change confidence, mass, review state or source accounting.

Read the stored message's `activation_provenance.selection_receipts` to inspect final prompt participation. Each receipt includes record ID, statement hash, review standing, scope/time, challenges, dissent, intended use, reason, policy and selection UTC time. Current decision IDs and retained counter-trace attribution are preserved when available. Scan/history truncation are explicit. Missing historical receipts remain unknown. The trace's `prompt_sha256` binds the assembled prompt; selection receipts describe context insertion and imply no causal influence on the response.

Chat and dream writers use the same existing message ledger. A selected spectral item suppressed by prompt deduplication has `injected: false` and no selection receipt. Final assembly occurs after any afferent reseating. Dream hotspot context separately carries standing into prompt generation; final assembly records the window used for the response. Provider/generation failures that prevent message storage may have no persisted activation trace. Shared research formatting receives scoped framing, but T14 adds no separate research selection store or receipt viewer.

The scan retains at most 100 active, 64 pending, 32 deferred and four historical nominations. Overflow probes mark truncation. Three-second SQLite reads can return a resource-exhausted Glitch; they do not fall back to unlabelled managed content. These limits establish finite work, not semantic calibration or guaranteed production latency. Source XML is quoted and escaped, and selected material cannot supply skill-routing mass priors or execution authority.

Nomination scans use stable ID order for deterministic replay. Under sustained overflow, relevant records beyond the scan can remain omitted; their histories remain in storage and the workshop. T15 must evaluate this coverage limit before accepting or changing budgets. Prompt statements retain the existing bounded preview length, while receipt hashes identify the complete stored statement.

See [ADR-127](../decisions/ADR-127-belief-participation-selection.md), [BELIEF_SPEC](../systems/BELIEF_SPEC.md) and [Report 061](../reports/061-belief-v2-participation/README.md).

The [T15 evaluation guide](belief-v2-evaluation.md) describes the provisional audit and synthetic exploratory replay. Its current findings do not close semantic acceptance or authorize a nonzero production budget.
