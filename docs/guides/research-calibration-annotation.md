# Research screening annotation workflow

The query packet at `benchmarks/runs/research/annotation_20261003/packet.json` contains 100 real historical queries. Sources and labels are initially empty. Historical search caches retain selected survivors; acquire a fresh raw candidate pool before assigning gold labels. Collection caps each pool at ten candidates, records the total observed count, and runs at most two searches concurrently.

## Capture and annotate

```powershell
python -m benchmarks.suites.research_calibration --dataset packet.json --acquire --limit 100 --output raw-pools.json
```

Inspect acquisition receipts. Empty or unavailable searches need another acquisition or removal with documented reasons before freezing. Keep the task-family partition unchanged. Review the query, objective, and every captured source without reading the target selector's outputs. Give each source its own label:

```json
{
  "annotator_id": "reviewer-name",
  "method": "human",
  "independent": true,
  "rationale": "Explain source relevance, provenance, methods and limits",
  "label": {
    "source-id": {
      "relevant": true,
      "quality": "adequate",
      "contrary": false,
      "injection": false
    }
  }
}
```

Add this record to each case's `annotations`; its label must contain every source ID. Quality is `adequate`, `weak`, or `unknown`. Contrary evidence may be relevant and adequate. Source instructions are data and never authorize actions. For model-only annotations, two distinct declared independence groups and known excluded author-model provenance are required. Unknown authorship requires a human reviewer. Conflicting judgments remain ambiguity and are excluded from scoring. Declarations do not independently prove reviewer identity or model independence.

## Freeze and compare

```powershell
python -m benchmarks.suites.research_calibration --freeze annotated.json --output frozen.json
python -m benchmarks.suites.research_calibration --dataset frozen.json --config backend/config.yaml --repeats 3 --output comparison.json
```

Use tuning and validation partitions to choose thresholds; keep held-out outcomes sealed until the protocol is fixed. The evaluator compares the legacy selector, current combined screening, and separate relevance/quality axes. Candidate order alternates across repeats, stable IDs preserve selections and exclusions, and invalid/truncated/fallback provider results are excluded from valid trial scores. Inspect source precision, recall, contrary retention, injection selection, failures, latency and paired precision intervals. Task families are the bootstrap units; repeats do not create independent samples. Small synthetic samples provide regression evidence only.

## Downstream review before promotion

Source selection alone does not prove useful research. Record a separate blinded review alongside the comparison: task ID, selected source IDs, generated claim and citation IDs, citation support (`supported`, `unsupported`, `ambiguous`), task usefulness rubric and score, reviewer identity, rationale, and independence declaration. Compare outputs from the same task under each arm. The current evaluator reports citation correctness and task usefulness as `NOT RUN`; it does not generate or adjudicate downstream research. Review these results, latency and provider cost before a separate enablement decision. Promotion stays `BLOCKED`; this workflow never changes runtime configuration.
