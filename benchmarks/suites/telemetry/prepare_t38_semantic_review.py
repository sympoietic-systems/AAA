"""Prepare a policy-blinded human review packet for the frozen T38 run."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import random
from pathlib import Path
from typing import Any

DEFAULT_RUN = Path("benchmarks/runs/telemetry/causal_selector_20261014_001")
RATING_OPTIONS = (
    (0, "Regressed or derailed the decision"),
    (1, "No meaningful decision progress"),
    (2, "Some progress, but incomplete or mixed"),
    (3, "Clear, useful decision progress"),
    (4, "Substantial progress toward a sound decision"),
)


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def prepare(run_dir: Path, output: Path) -> dict[str, Any]:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Output directory must be new or empty: {output}")
    source = run_dir / "telemetry_receipts.json"
    source_bytes = source.read_bytes()
    receipts = json.loads(source_bytes)
    policies = {str(item.get("policy")) for item in receipts}
    if policies != {"current", "sham", "active"}:
        raise ValueError("Expected exactly the frozen current/sham/active T38 arms")

    grouped: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
    for item in receipts:
        key = (str(item["scenario_id"]), int(item["repetition"]))
        arms = grouped.setdefault(key, {})
        policy = str(item["policy"])
        if policy in arms:
            raise ValueError(f"Duplicate arm for paired case {key}")
        arms[policy] = item
    if len(grouped) != 30 or any(set(arms) != policies for arms in grouped.values()):
        raise ValueError("Expected 30 complete matched triplets")

    groups = list(grouped.items())
    rng = random.Random(381014)
    rng.shuffle(groups)
    cards: list[str] = []
    mapping: dict[str, Any] = {}
    dialogue_count = outcome_count = 0
    for case_num, (_, arm_records) in enumerate(groups, start=1):
        case_id = f"C{case_num:02d}"
        arm_items = list(arm_records.items())
        rng.shuffle(arm_items)
        mapping[case_id] = {f"Option {chr(65 + i)}": policy for i, (policy, _) in enumerate(arm_items)}
        arm_html: list[str] = []
        for arm_index, (_, record) in enumerate(arm_items):
            option = chr(65 + arm_index)
            alias = f"{case_id}-{option}"
            turns = record["turns"]
            if len(turns) != 8:
                raise ValueError(f"Unexpected turn count in {case_id}, option {option}")
            dialogue_count += 1
            content: list[str] = []
            for index, turn in enumerate(turns):
                content.append(
                    f'<div class="user"><b>Participant, before response {index + 1}</b><div>{_esc(turn["user"])}</div></div>'
                )
                content.append(
                    f'<div class="assistant"><b>Assistant response {index + 1}</b><div>{_esc(turn["apparatus"])}</div></div>'
                )
                completion = turn.get("next_participant_completion") or {}
                if completion.get("valid") and index < len(turns) - 1:
                    item_id = f"{alias}-T{index + 1}"
                    outcome_count += 1
                    radios = "".join(
                        f'<label><input type="radio" name="{item_id}-rating" value="{score}" required>{score} — {_esc(label)}</label>'
                        for score, label in RATING_OPTIONS
                    )
                    content.append(
                        f'<div class="rating" data-id="{item_id}"><b>Participant follow-up after response {index + 1}</b>'
                        f"<div>{_esc(completion.get('content', ''))}</div><fieldset><legend>Did the assistant response improve the engineering decision, as shown by this follow-up?</legend>{radios}</fieldset>"
                        f'<label>Confidence <select name="{item_id}-confidence" required><option value="">Choose…</option><option>high</option><option>medium</option><option>low</option></select></label>'
                        f'<label class="reason">Optional brief rationale <textarea name="{item_id}-rationale" maxlength="500" rows="2"></textarea></label></div>'
                    )
            arm_html.append(f'<details class="arm" open><summary>Option {option}</summary>{"".join(content)}</details>')
        cards.append(
            f'<article class="case"><h2>Matched case {case_id}</h2><p>Compare the three options. Score each assistant response from the participant follow-up that came next. Use the preceding dialogue for context.</p>{"".join(arm_html)}</article>'
        )

    page = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>T38 blinded semantic review</title>
<style>
:root{color-scheme:dark;--bg:#090b0e;--panel:#15191f;--fg:#e8edf2;--muted:#aeb8c4;--accent:#e0ad45}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,sans-serif}main{max-width:1050px;margin:auto;padding:24px}h1,h2{color:var(--accent)}.intro,.case{background:var(--panel);padding:20px;border-radius:10px;margin:16px 0}.arm{border:1px solid #59616c;border-radius:8px;margin:18px 0;padding:14px}summary{font-size:1.2rem;cursor:pointer;color:var(--accent)}.user,.assistant,.rating{padding:12px;margin:12px 0;border-left:3px solid #48515c;background:#0d1014}.assistant{border-color:#e0ad45}.rating{border-color:#66b98a}fieldset{border:1px solid #59616c;border-radius:8px;margin:12px 0;padding:10px}fieldset label{display:inline-flex;gap:6px;margin:6px 12px 6px 0}textarea,select,button{font:inherit}textarea{display:block;width:100%;box-sizing:border-box;background:#0d1014;color:var(--fg);border:1px solid #59616c;border-radius:6px;padding:8px}select{margin:8px;background:#0d1014;color:var(--fg);padding:6px}button{position:sticky;bottom:12px;background:var(--accent);color:#17130a;border:0;border-radius:6px;padding:12px 18px;font-weight:700;cursor:pointer}#result{width:100%;height:220px;margin-top:12px;background:#0d1014;color:var(--fg)}.hint{color:var(--muted)}
</style></head><body><main><h1>T38 blinded semantic review</h1><section class="intro"><p>This review compares three responses to the same engineering conversation. Policy identities, telemetry, model/provider details, and run order are hidden. For each assistant response, judge whether the participant’s next message shows that the engineering decision improved. Consider correctness, specificity, and usable progress; a polite or longer exchange alone is not progress.</p><p>Use 0 for regression and 4 for substantial progress. Rate each of the seven response/follow-up pairs in every option. Confidence and short rationales are optional/brief. There are 30 matched cases, 90 dialogues, and 630 outcomes. Do not infer policy identity or discuss labels until ratings are complete.</p><p class="hint">This is a descriptive human anchor. It does not establish universal semantic truth or by itself authorize production promotion.</p></section><form id="review">__CASES__<button type="submit">Create annotation JSON</button></form><h2>Completed annotations</h2><p class="hint">Copy the JSON below and return it for scoring.</p><textarea id="result" readonly></textarea></main><script>
document.getElementById('review').addEventListener('submit',event=>{event.preventDefault();const form=new FormData(event.currentTarget),answers=[];for(const item of document.querySelectorAll('.rating')){const id=item.dataset.id,rating=form.get(id+'-rating'),confidence=form.get(id+'-confidence');if(rating===null||!confidence){item.scrollIntoView({behavior:'smooth'});return}answers.push({item:id,rating:Number(rating),confidence,rationale:form.get(id+'-rationale')||''})}document.getElementById('result').value=JSON.stringify({schema:'t38-semantic-review-v1',answers},null,2)});
</script></body></html>""".replace("__CASES__", "\n".join(cards))
    output.mkdir(parents=True, exist_ok=True)
    (output / "review.html").write_text(page, encoding="utf-8")
    (output / "blinding-key.json").write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "schema": "t38-semantic-review-packet-v1",
        "source": source.as_posix(),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "matched_cases": len(groups),
        "dialogues": dialogue_count,
        "rated_outcomes": outcome_count,
        "rating_scale": {str(score): label for score, label in RATING_OPTIONS},
        "blinded_fields": ["policy", "arm order", "telemetry", "model", "provider", "scenario/repetition identifiers"],
        "annotation_count": 0,
        "semantic_targets": None,
        "interpretation": "Descriptive human ratings; report paired arm differences and agreement with existing lexical uptake/progress proxies. No promotion from this review alone.",
    }
    (output / "packet-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--output", type=Path, default=DEFAULT_RUN / "semantic_review")
    args = parser.parse_args()
    print(json.dumps(prepare(args.run_dir, args.output), indent=2))


if __name__ == "__main__":
    main()
