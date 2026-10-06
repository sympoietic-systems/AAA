# Report 041: Provisional research labeling

Date: 2026-10-06. Task: T74, explicitly requested automation of source labeling. Operations: [labeling guide](../../guides/RESEARCH_LABELING.md). Remaining gates: [Research V2 progress](../../guides/RESEARCH_V2_PROGRESS.md).

The current packet has provisional labels for all 70 sources across seven queries. NVIDIA Nemotron produced 30 labels in three successful query calls. Codex completed the remaining 40 labels from the captured source text after NVIDIA failures. These annotator identities remain distinct. No human annotation, independent gold, underlying-page verification, or model promotion is claimed.

The automated command labels captured objective/query/title/URL/snippet input, validates complete ID coverage and typed labels, and writes per-query receipts. Checkpointed resume reuses only validated same-model/same-input annotations. A different model or changed input requires a fresh judgment. Invalid JSON, truncation, incomplete labels and HTTP failures preserve an explicit failure instead of fabricated labels. HTML review output escapes untrusted source content.

## Observed provider behavior

The initial seven-query NVIDIA run returned three valid provisional annotations, three HTTP failures, and one malformed JSON response. The checkpointed retry recorded HTTP 503 and malformed JSON. A second NVIDIA model timed out; a catalog-listed smaller model returned inference 404. The unsuccessful runs were stopped locally with completed checkpoints retained. Catalog membership did not establish a working inference route. The final private packet merges only valid annotations from the first run with clearly attributed Codex annotations; failed responses never supply labels.

Private packets, HTML views, and full run receipts remain under ignored `benchmarks/runs/research/`. The completed packet is `t69_provisional_labels_complete_20261006/packet.json`; its review is `review.html`. The durable summary below records dataset lineage without copying source text:

- Original dataset SHA-256: `7923acebf25f14f90bf040e45b301e4387366983fb61d9684e2bdd8c468b9955`.
- Labeled dataset SHA-256: `c8c9544ae3f8f7eacf7ec1c404133cebfdf0e7ef6821a2c91b9fba164a87a307`.
- Provisional labels: 70. Independent labels: zero. Monetary billing: unknown.

## Verification and limits

All 23 labeling/calibration tests passed. Focused Ruff lint and formatting passed. Tests cover unchanged-input resume without a new call, changed-input refresh, independent-gold rejection, exact source coverage, invalid confidence/quality/boolean/rationale rejection, truncation, safe HTTP failure checkpointing, unknown billing, and escaped review output. Every final query's labels were validated against its source IDs; the independent-label gate still rejects all seven cases.

The current annotations judge snippets rather than source documents. Model confidence is not calibrated accuracy. A false injection or contrary flag means the inspected text supplied no such evidence, not a verified absence across the whole page. Source families and repeated URLs still constrain independent sample counts. T69 remains open for independent labels, actual held-out comparison, and downstream support/coverage review. T74 automates preparation without weakening that contract.
