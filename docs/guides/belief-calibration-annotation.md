# Belief calibration annotation workflow

Use the [real-pair packet](../../benchmarks/runs/beliefs/annotation_v1_20261003/packet.json). It contains 240 pairs: 48 tuning, 48 validation and 144 held out. Belief IDs do not cross partitions. Labels are absent intentionally. The packet is private workspace evidence; review before publishing it elsewhere.

## Annotate

For each `a.context` and `b.context`, supply:

```json
{
  "statement_sha256": "SHA256 of exact statement UTF-8 bytes",
  "scope": "named subject and conditions",
  "temporal_scope": "time interval or timeless scope, with justification",
  "provenance": "reviewer and source of context",
  "resolution": "resolved",
  "bindings": []
}
```

For each detected reference word, add a binding with zero-based `start`/`end` character offsets, `candidates` containing exactly one named antecedent, and `confidence` at least 0.9. Multiple plausible antecedents remain ambiguous: set resolution to `ambiguous` or `unresolved`. A grammatical nonreference may be explicitly marked `role: "nonreferential"` with empty candidates. Missing context must not be fabricated to make a pair classifiable.

Add independent annotation records:

```json
{
  "annotator_id": "reviewer-name",
  "method": "human",
  "independent": true,
  "label": "contradiction",
  "rationale": "Named same-scope claims cannot both hold"
}
```

Allowed labels: `contradiction`, `endorsement`, `orthogonal`, `abstain`. Contradiction requires the same referent, conditions and temporal scope. Preserve annotator disagreement; the evaluator treats disagreement as abstention. Do not consult the target judge while labeling held-out cases. For model-only dual annotation, record distinct `independence_group` values and the known case `author_model`; the author must be excluded. Unknown authorship requires human review.

## Freeze and compare

```powershell
python -m benchmarks.suites.belief_calibration --freeze annotated.json --output frozen.json
python -m benchmarks.suites.belief_calibration --dataset frozen.json --config backend/config.yaml --repeats 3 --output comparison.json
```

Freeze occurs before tuning or reading held-out outcomes. Outputs must be fresh. The evaluator compares an isolated unguarded baseline, context plus guards, and context plus staged assessment. Repeat trials do not increase the independent sample count. Inspect false contradictions, uncertainty intervals, abstention/watchlist rates and provider failures. Add negative/ambiguous coverage until uncertainty bounds meet the agreed tolerance; 240 exported pairs do not guarantee enough independently labeled examples in each class.

Production promotion remains a separate reviewed opt-in. No belief adoption or skill pruning is part of calibration.
