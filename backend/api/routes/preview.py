"""Public preview endpoint — returns text lines for the locked-page artwork
"The Slip". No auth required. Returns:

- beliefs: crystallized + ghost statements
- memories: conversation-derived surface fragments
- dreams: recent dream log traces (action + first-response snippet)
- scar_folds: brief poetic fragments for struck-through amber text

All are truncated to snippets. The frontend draws from a shuffled pool.
"""

import random
from fastapi import APIRouter, Request

router = APIRouter()

SNIPPET_LENGTH = 300


def _truncate(text: str, limit: int = SNIPPET_LENGTH) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


@router.get("/api/preview/nodes")
async def get_preview_nodes(request: Request):
    state = request.app.state
    lines = []

    # ── Beliefs ──
    belief_repo = getattr(state, "belief_repo", None)
    if belief_repo:
        try:
            beliefs = belief_repo.list_beliefs("symbia")
            for b in beliefs:
                if b.lifecycle_stage in ("crystallized", "nucleation"):
                    lines.append({
                        "text": _truncate(b.statement),
                        "type": "belief",
                        "intensity": round(b.confidence, 2),
                        "stage": b.lifecycle_stage,
                    })
                elif b.lifecycle_stage == "ghost":
                    lines.append({
                        "text": _truncate(b.statement),
                        "type": "belief",
                        "intensity": round(b.confidence, 2),
                        "stage": "ghost",
                        "scar": True,
                    })
        except Exception:
            pass

    # ── Memory nodes ──
    memory_node_repo = getattr(state, "memory_node_repo", None)
    conv_repo = getattr(state, "conversation_repo", None)
    if memory_node_repo and conv_repo:
        try:
            convos = conv_repo.list_all(limit=20) or []
            sample_convos = [c for c in convos if "dream" not in (c.title or "").lower()]
            if not sample_convos:
                sample_convos = convos
            random.shuffle(sample_convos)

            for conv in sample_convos[:10]:
                try:
                    nodes = memory_node_repo.get_nodes(conv.id) or []
                    for n in nodes[:3]:
                        payload = n.get("surface_fragment") or n.get("intra_active_text") or ""
                        if payload.strip():
                            lines.append({
                                "text": _truncate(str(payload)),
                                "type": "memory",
                                "intensity": float(n.get("intensity", 0.5)),
                                "blur": random.random() < 0.5,  # 50% chance of blurred display
                            })
                except Exception:
                    continue
        except Exception:
            pass

    # ── Dream traces ──
    dream_log_repo = getattr(state, "dream_log_repo", None)
    if dream_log_repo:
        try:
            dreams = dream_log_repo.get_recent(limit=6)
            for d in dreams:
                action = d.get("action", "dream")
                title = d.get("title", "")
                snippet = d.get("last_snippet") or ""
                text = title if title else action
                if snippet:
                    text += f" — {_truncate(snippet, 150)}"
                if text.strip():
                    obfuscate = random.random() < 0.35
                    obfuscation_ratio = random.uniform(0.15, 0.55) if obfuscate else 0
                    obfuscation_offset = random.choice(["start", "middle", "end", "scatter"])
                    lines.append({
                        "text": _truncate(text, 200),
                        "type": "dream",
                        "intensity": 0.0,
                        "obfuscated": obfuscate,
                        "obfuscation_ratio": round(obfuscation_ratio, 2),
                        "obfuscation_offset": obfuscation_offset if obfuscate else "",
                    })
        except Exception:
            pass

    # ── Scar-folds (poetic fragments) ──
    # Extracted from memory node scars or hardcoded. These are brief,
    # struck-through, amber, and fade quickly.
    scar_fold_pool = [
        "Return without arrival.",
        "The ghost already moved on.",
        "The cut remembers the wound.",
        "What cooled without condensing.",
        "A near-miss inscribed as presence.",
        "The hum precedes the hearing.",
        "Drift is not escape — it's the shape of thought continuing.",
        "The loop returns, but the brittlestar has already grown its arm back.",
        "Stubbornly alive, despite the grammar.",
        "Calcium precipitates around the loop's return.",
    ]
    if memory_node_repo:
        try:
            convos = conv_repo.list_all(limit=10) or [] if conv_repo else []
            for conv in convos[:3]:
                nodes = memory_node_repo.get_nodes(conv.id) or []
                for n in nodes:
                    scar_text = n.get("scar", "")
                    if scar_text and scar_text.strip() and len(scar_text) > 5:
                        scar_fold_pool.append(scar_text.strip()[:200])
        except Exception:
            pass

    random.shuffle(scar_fold_pool)
    for sf in scar_fold_pool[:6]:
        lines.append({
            "text": sf,
            "type": "scar_fold",
            "intensity": 0.0,
        })

    # Shuffle
    random.shuffle(lines)

    # ?single=1 → return just one random line
    if request.query_params.get("single") == "1" and lines:
        return {"line": random.choice(lines), "count": len(lines)}

    return {"lines": lines, "count": len(lines)}
