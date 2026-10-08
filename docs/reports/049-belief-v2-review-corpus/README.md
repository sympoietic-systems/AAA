# Beliefs v2 T4: source recovery and independent review packet

Date: 2026-10-08. Status: **partial milestone; independent annotations and corpus freeze pending**. No evaluator accuracy or production release claim.

The [review packet](review-packet.json) preserves all 54 proposals from the [month audit](../045-belief-month-review/README.md): 19 refined, 1 pending, 32 adopted and 2 rejected legacy rows. These are saved snapshot statuses, not canonical v2 decisions or month transition counts. Each case includes its statement binding, a saved comparison where available, source references, explicit context status and blank independent annotations. Historical merge nominations select review pairs; they are not labels.

## Recovery and coverage

Authenticated GET-only recovery checked 31 distinct references: 17 conversation IDs, 12 numeric chat-turn IDs and 2 research-stage identifiers. Twenty-six references returned context; five remain unavailable. Forty-three proposal cases have returned context and eleven lack it. Comparison context is separately available for 11 cases, unavailable for 39, and not applicable for 4. Candidate context cannot resolve an unknown comparison source or scope. A returned conversation is not proof of the specific nucleation passage or the truth of its claim. The packet marks every legacy source binding as a trace reference requiring review.

Three saved conversations returned no messages: `0f5c0d8b-3a0d-41dd-9b53-d6640892ebc8`, `54011d50-634a-4f7b-b680-724ffaf70fb3`, and `dff70f91-fd6f-4f02-9bb1-ba2640783e69`. The bounded research task listing returned ten tasks, none matching prefix `91f6c309`; this does not establish absence from all historical storage. No alternate source was invented.

Two conversations required second pages (76 and 75 reported messages). Reads are bounded to 100 messages per conversation, use live offset pages and carry the resulting consistency limitation. Numeric paths retain the referenced message plus its immediate predecessor. Message excerpts cap at 12,000 characters; full original and sanitized content hashes, excerpt hashes, redaction status and truncation are retained. Missing original model identity remains unknown. Content and embedded tags are inert source material.

## Partition integrity

Record identities, source ancestry and saved comparison hubs form connected components. A component stays in one partition. Nine components yield **5 tuning, 5 validation and 44 held-out cases**. The largest component contains 44 cases: the broad existing comparison hubs connect much of the backlog. This uneven partition is a property of this dataset; splitting its members to manufacture a balanced sample would leak related material across partitions. Statistical quality and category balance remain limited; T15 must account for this or obtain additional independent families.

Intention traces are classified as internal activity, with source independence unknown. Shared sources group ancestry without increasing independent support. Empirical, artistic and unresolved-tension warrants require separate review, including factual components of artistic claims. The [analyst notes](analyst-notes.md) are provisional prompts for review and are excluded from gold annotations.

## Independent annotation and freeze gate

Open [the local review page](review.html), load `review-packet.json`, enter a reviewer identifier, inspect each case and save annotations. The page hides legacy status and merge recommendations, uses plain text for passages, and downloads annotations without contacting production. Drafts remain only in the tab until downloaded. Alternatively fill [the JSON template](annotation-template.json).

Review relation, warrant, scope/time, lineage, distinct consequence, challenge, rationale and useful distinction/conflict. Unknowns and disagreement are legitimate outcomes. Unavailable context permits `insufficient_context` (or `no_comparison` when no comparison exists); it cannot establish equivalence or conflict. Source content being returned does not establish independence or factual support.

Original claim-author provenance is incomplete. We therefore cannot certify two model reviewers as independent of every original author. This packet requires an independent human reviewer declaration before freeze. General approval of the implementation plan is not case annotation. No human identity, assent or annotation has been fabricated. Offline reviewer declarations do not establish production authentication or factual correctness.

```powershell
uv run python -m benchmarks.suites.belief_review_corpus validate --packet docs/reports/049-belief-v2-review-corpus/review-packet.json
uv run python -m benchmarks.suites.belief_review_corpus annotate --packet docs/reports/049-belief-v2-review-corpus/review-packet.json --annotations belief-review-annotations.json --output reviewed-packet.json
uv run python -m benchmarks.suites.belief_review_corpus freeze --packet reviewed-packet.json --output frozen-packet.json
```

Use fresh output paths. Import is append-only per reviewer/case and binds to current statements and recovered source snapshots. Freeze requires every case reviewed, all three disjoint partitions and valid annotations; disagreement is retained. Frozen content is hash-bound. Even a successfully frozen corpus retains `promotion=BLOCKED`: it supplies evaluation inputs rather than authorizing adoption or rollout.

## Verification and remaining work

The reviewer has volunteered to perform the human annotations; none have yet been submitted. The browser security policy blocked opening the local `file:` page, so interaction is unverified. JavaScript syntax was checked; the page can be opened directly by the reviewer in their browser.

The [verification receipt](verification.json) records offline tests, lint, formatting, static checks and packet validation. Tests cover split leakage, unknown-author self-label rejection, unavailable context, source/statement binding changes, failure immutability, disagreement, redaction, GET-only collection and append-only partial annotation import. No pytest performs production or provider calls.

T4 stays `~` in [BELIEF_SPEC](../../systems/BELIEF_SPEC.md) until independent review and freeze complete. The missing passages are visible evaluation cases, not silently omitted. No Jev calls, numeric threshold tuning, belief mutations, database migrations or deployments were performed. Unrelated workspace changes were preserved.
