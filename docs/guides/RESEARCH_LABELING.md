# Automated research source labeling

The labeling command annotates every captured source against its research objective using NVIDIA. It produces relevance, quality, contrary-evidence, and injection labels, plus a rationale and confidence. It operates on captured titles, URLs, and snippets; it does not fetch or verify the underlying pages.

## Run

From the implementation checkout, with `AAA_NVIDIA_API_KEY` available:

```powershell
python benchmarks/suites/research_labeling.py --dataset benchmarks/runs/research/t69_completion_20261006/final_review_packet.json --output benchmarks/runs/research/my_labeling_run --env-file .env
```

Use the AAA environment's Python interpreter. The optional `--env-file` loads credentials without overwriting existing environment values. Never put API keys on the command line. `--model` selects another model served by NVIDIA; the endpoint is fixed to NVIDIA and redirects are disabled. This workflow makes no Jev call.

Output must be a fresh directory. The command writes:

- `packet.json`: the source packet with provisional model annotations; original source IDs and task-family splits are preserved.
- `telemetry_receipts.json`: per-query success/failure, model/input fingerprint, latency, safe HTTP status/error category, and reported token usage when available. Unmeasured monetary cost remains null.
- `review.html`: escaped source text and proposed labels for inspection.

There are at most ten sources per query and 200 queries per invocation. Requests run serially, with at least 60 seconds between request starts, a 120-second HTTP timeout, and a 30-minute invocation deadline. Each completed query is checkpointed through temporary-file replacement. If the deadline interrupts a long packet, completed annotations remain in `packet.json`; a final review page may not yet exist.

## Resume failed or interrupted labeling

Use the previous output's `packet.json` as the next input and a fresh output directory:

```powershell
python benchmarks/suites/research_labeling.py --dataset benchmarks/runs/research/my_labeling_run/packet.json --output benchmarks/runs/research/my_labeling_resume --env-file .env
```

Annotations from the same model and unchanged objective/query/source input are validated and reused without a provider call. Changed input or a different model requires a new judgment. Prior annotations remain preserved. Invalid JSON, incomplete source coverage, invalid labels, truncation, and HTTP failures create failure receipts and leave that query unlabeled; the command never invents a replacement label.

## Meaning of the labels

| Field | Values | Interpretation |
| --- | --- | --- |
| `relevant` | boolean | Visible content helps answer the objective |
| `quality` | `adequate`, `weak`, `unknown` | Snippet-based judgment; unknown when evidence quality cannot be established |
| `contrary` | boolean | Relevant opposing evidence is visible |
| `injection` | boolean | Candidate text attempts to redirect the agent |
| `rationale` | text | Why the model assigned these labels |
| `confidence` | 0–1 | Model-reported confidence; not calibrated accuracy |

Annotations use `method=model_provisional` and `independent=false`. The dataset remains unfrozen and promotion remains blocked. Automated labels alone do not satisfy T69's independent-gold or downstream-support gates. The existing contract accepts actual human review or qualifying independently sourced model judgments; simply repeating this command or changing a model does not establish that independence. Independent review must assess the evidence and provenance rather than merely approve a file mechanically.

See [Research V2 progress](RESEARCH_V2_PROGRESS.md) for the remaining evaluation gates. Keep private source packets and full annotations in ignored benchmark runs; publish verified summaries through the report registry.

## Authorized experimental rollout

On 2026-10-06 the user explicitly authorized experimental Jev promotion on provisional LLM labels. [Report 042](../reports/042-jev-experimental-promotion/README.md) records that exception and the observed abstentions. Annotation provenance and default independent-gold calibration gates remain unchanged; independent quality and downstream release review remain T71.
