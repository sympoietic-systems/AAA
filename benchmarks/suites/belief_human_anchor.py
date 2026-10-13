"""Build a small blinded human-anchor packet from the frozen T15 challenge."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import random
from pathlib import Path
from typing import Any

DEFAULT_SOURCE = Path("benchmarks/runs/belief-challenge/2026-10-12-v1/contract.json")
DEFAULT_OUTPUT = Path("benchmarks/runs/belief-human-anchor/2026-10-13-v1")
HELD_OUT_IDS = {f"{case_id:02d}" for case_id in range(9, 17)}


def _escape(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def prepare(source: Path, output: Path) -> dict[str, Any]:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Output directory must be new or empty: {output}")
    source_bytes = source.read_bytes()
    contract = json.loads(source_bytes)
    cases = [case for case in contract["cases"] if case["id"] in HELD_OUT_IDS]
    if len(cases) != 8 or {case["id"] for case in cases} != HELD_OUT_IDS:
        raise ValueError("Frozen challenge must contain held-out cases 09 through 16")

    # Stable shuffle hides the source case IDs while keeping the packet reproducible.
    random.Random(15013).shuffle(cases)
    aliases = [f"H{index:02d}" for index in range(1, len(cases) + 1)]
    case_map: dict[str, str] = {}
    rendered: list[str] = []
    sealed_cases: list[dict[str, Any]] = []
    for alias, case in zip(aliases, cases, strict=True):
        case_map[alias] = case["id"]
        candidate = case["candidate"]
        comparison = case["comparison"]
        rendered.append(
            f"""<article class="case" data-case="{alias}">
<h2>Case {alias}</h2>
<div class="context"><b>Candidate scope:</b> {_escape(candidate.get("scope"))}<br>
<b>Candidate time:</b> {_escape(candidate.get("temporal_scope"))}<br>
<b>Comparison scope:</b> {_escape(comparison.get("scope"))}<br>
<b>Comparison time:</b> {_escape(comparison.get("temporal_scope"))}</div>
<section><h3>Candidate</h3><p>{_escape(candidate.get("statement"))}</p>
<p class="detail"><b>Stated consequence:</b> {_escape(candidate.get("consequence"))}</p>
<p class="detail"><b>Source excerpt:</b> {_escape(candidate.get("evidence_quote"))}</p></section>
<section><h3>Existing comparison</h3><p>{_escape(comparison.get("statement"))}</p>
<p class="detail"><b>Stated consequence:</b> {_escape(comparison.get("consequence"))}</p>
<p class="detail"><b>Source excerpt:</b> {_escape(comparison.get("evidence_quote"))}</p></section>
<fieldset><legend>How do these statements relate?</legend>
{_radio_group(alias, "relation", [("equivalent", "Equivalent"), ("extension", "Extension"), ("contradiction", "Conflict / contradiction"), ("distinct", "Distinct"), ("insufficient_context", "Insufficient context")])}
</fieldset>
<fieldset><legend>What, if anything, makes the candidate worth retaining?</legend>
{_radio_group(alias, "value", [("new_distinction", "New distinction"), ("useful_conflict", "Useful unresolved conflict"), ("worthwhile_question", "Worthwhile question"), ("redundant", "Redundant / no meaningful addition"), ("unclear", "Unclear")])}
</fieldset>
<label>Confidence
<select name="{alias}-confidence" required><option value="">Choose…</option><option>high</option><option>medium</option><option>low</option></select></label>
<label>Optional brief rationale<textarea name="{alias}-rationale" rows="2" maxlength="500"></textarea></label>
</article>"""
        )
        sealed_cases.append(
            {
                "alias": alias,
                "candidate": candidate,
                "comparison": comparison,
            }
        )

    page = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Belief review</title>
<style>
:root{color-scheme:dark;--bg:#090b0e;--panel:#15191f;--fg:#e8edf2;--muted:#aeb8c4;--accent:#e0ad45}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,sans-serif}
main{max-width:900px;margin:auto;padding:24px}h1,h2{color:var(--accent)}.intro,.case{background:var(--panel);padding:20px;border-radius:10px;margin:16px 0}
.context,.detail{color:var(--muted);font-size:.94rem}section{border-top:1px solid #343a42;margin-top:18px;padding-top:8px}
fieldset{border:1px solid #59616c;border-radius:8px;margin:18px 0;padding:12px}fieldset label{display:inline-flex;gap:8px;margin:6px 18px 6px 0}
textarea,select,button{font:inherit}textarea{display:block;width:100%;box-sizing:border-box;background:#0d1014;color:var(--fg);border:1px solid #59616c;border-radius:6px;padding:8px}
select{margin-left:8px;background:#0d1014;color:var(--fg);padding:6px}button{background:var(--accent);color:#17130a;border:0;border-radius:6px;padding:10px 16px;font-weight:700;cursor:pointer}
#result{width:100%;height:180px;margin-top:12px;background:#0d1014;color:var(--fg)}.hint{color:var(--muted)}
</style></head><body><main><h1>Belief review</h1>
<div class="intro"><p>Review each candidate against the stated comparison. These are hypothetical cases. Judge the relation and whether the candidate adds a useful distinction, conflict, or question. You may choose “insufficient context” or “unclear.”</p>
<p class="hint">This packet hides the case family, original label, author intent, and all model opinions. Your answers are an independent human anchor, not a claim of universal truth. Eight cases; no need to write long rationales.</p></div>
<form id="review">__CASES__<button type="submit">Create review JSON</button></form>
<h2>Completed annotations</h2><p class="hint">Copy the JSON below and paste it into the conversation.</p><textarea id="result" readonly></textarea></main>
<script>
document.getElementById('review').addEventListener('submit',event=>{
 event.preventDefault();const form=new FormData(event.currentTarget),answers=[];
 for(const card of document.querySelectorAll('.case')){const id=card.dataset.case;
  const relation=form.get(id+'-relation'),value=form.get(id+'-value'),confidence=form.get(id+'-confidence');
  if(!relation||!value||!confidence){card.scrollIntoView({behavior:'smooth'});return;}
  answers.push({case:id,relation,value,confidence,rationale:form.get(id+'-rationale')||''});
 }
 document.getElementById('result').value=JSON.stringify({schema:'belief-human-anchor-v1',answers},null,2);
});
</script></body></html>""".replace("__CASES__", "\n".join(rendered))

    output.mkdir(parents=True, exist_ok=True)
    (output / "review.html").write_text(page, encoding="utf-8")
    (output / "case-map.json").write_text(json.dumps(case_map, indent=2) + "\n", encoding="utf-8")
    (output / "sealed-cases.json").write_text(
        json.dumps(sealed_cases, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    receipt = {
        "schema": "belief-human-anchor-packet-v1",
        "source": source.as_posix(),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "selected_source_cases": sorted(HELD_OUT_IDS),
        "presented_aliases": aliases,
        "presented_case_count": len(aliases),
        "blind_fields_omitted": [
            "author_intent",
            "family",
            "partition",
            "all_model_outputs",
            "original_case_id",
        ],
        "independent_gold": False,
        "human_annotations_received": 0,
    }
    (output / "packet-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    plan = {
        "schema": "belief-t15-human-anchor-plan-v1",
        "frozen_before_human_annotations": True,
        "source_sha256": receipt["source_sha256"],
        "case_count": len(aliases),
        "primary_observations": [
            "human relation judgment per case",
            "human candidate-value judgment per case",
            "human confidence and optional rationale",
        ],
        "operational_acceptance": {
            "source_case_coverage": "8/8 exact source-bound cases",
            "source_or_statement_mutations": 0,
            "model_output_promoted_to_gold": 0,
            "production_writes_or_enablement": 0,
            "semantic_threshold_tuning": 0,
        },
        "semantic_targets": None,
        "semantic_target_reason": (
            "No independent baseline supports a numeric accuracy or usefulness threshold. "
            "The eight-case anchor is descriptive and cannot justify global calibration."
        ),
        "analysis_rule": (
            "Report per-case human/model agreements and disagreements as descriptive counts; "
            "do not call the small anchor accuracy, calibration, or generalization."
        ),
        "promotion": "blocked_pending_broader_independent_evidence_and_usefulness",
    }
    (output / "evaluation-plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return receipt


def _radio_group(alias: str, field: str, options: list[tuple[str, str]]) -> str:
    return "\n".join(
        f'<label><input type="radio" name="{alias}-{field}" value="{value}" required>{_escape(label)}</label>'
        for value, label in options
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output), indent=2))


if __name__ == "__main__":
    main()
