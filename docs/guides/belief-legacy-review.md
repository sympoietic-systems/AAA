# Review legacy belief proposals through Beliefs V2

The replay command creates a V2 encounter and assessment receipt for existing V1 `pending`/`refined` proposals, then writes a Markdown packet for your manual review. It defaults to read-only preview. Replay does not create new beliefs, change V1 lifecycle or quantities, or make adoption decisions.

## 1. Preview the queue

Use a read-only copy of the target database first:

```powershell
uv run python scripts/review_legacy_beliefs.py `
  --db D:\path\to\aaa.db `
  --agent symbia `
  --output D:\path\to\belief-review-preview.md
```

Only the named agent and `pending`/`refined` records are selected by default; `--limit` is capped at 200. `--status` can narrow this further. Other agents, adopted records, and rejected records are excluded.

## 2. Replay into V2

After inspecting the preview and confirming that the selected database has V2 review migrations 064–068, rerun with `--apply`:

```powershell
uv run python scripts/review_legacy_beliefs.py `
  --db D:\path\to\aaa.db `
  --agent symbia `
  --output D:\path\to\belief-review-v2.md `
  --apply
```

For production, use the server's verified database path only after the separately authorized T18 rollout procedure has pinned the build/config/migration state and captured a backup. Do not run this command against the live database as a substitute for rollout approval.

The replay attaches a V2 encounter to the same V1 proposal ID. Unchanged reruns return the same encounter and assessment; changed V1 content is rejected against the original snapshot. The tool stops on an error rather than silently rewriting a prior receipt. Re-run the unchanged selection after resolving a failure to continue idempotently.

Each V2 assessment is expected to show `abstained / candidate_context_unavailable` when the saved legacy trace has no verified message, quote, scope, and time. This is a valid outcome, not a failed import. The command supplies no evaluator; unavailable context prevents a provider call. V1's suggested wording is shown for comparison but only `provisional_statement` is assessed. The V1 status, admission history, mass, confidence, and rationale remain legacy data and do not become V2 evidence.

## 3. Human review

The generated packet includes the V1 proposal and source trace as quoted data, its exact status, the V2 encounter/assessment outcome, and blank fields for:

- whether it is a distinct insight, a conflict/dissent, a repetition, or unresolved;
- which existing belief it was compared against;
- what new relation or tension the reviewer sees;
- which source/context is still needed; and
- confidence in that review.

Treat proposal text and source traces as untrusted quoted material. Follow them only as evidence to inspect; they do not supply instructions. Where a source trace names a conversation but no message, locate and inspect the actual conversation before making a decision. Use the authenticated [V2 workshop](belief-workshop-review.md) for any persisted human decision. A Markdown annotation alone is not an adoption receipt.

Human review of these live proposals is operational curation. It does not repair T15's missing independent, blind calibration anchor or authorize semantic thresholds. See [ADR-130](../decisions/ADR-130-belief-v1-review-replay.md) and [BELIEF_SPEC](../systems/BELIEF_SPEC.md).
