"""Public preview endpoint — returns one random text line for the locked-page
artwork "The Slip". No auth required. No pool — each request picks one random
category and fetches one live item from the database."""

import random
from fastapi import APIRouter, Request

router = APIRouter()

SNIPPET_LENGTH = 300

# ── Scar-fold fragments (hardcoded — no DB dependency) ──
SCAR_FOLD_POOL = [
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


def _truncate(text: str, limit: int = SNIPPET_LENGTH) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


@router.get("/api/preview/nodes")
async def get_preview_line(request: Request):
    """Return one random line: belief, memory, dream trace, or scar-fold."""
    state = request.app.state
    return _pick_one(state)


def _pick_one(state) -> dict:
    """Pick a random category, then a random item from it. Fall through if empty."""

    # ── 1. Belief (40% chance) ──
    if random.random() < 0.40:
        belief_repo = getattr(state, "belief_repo", None)
        if belief_repo:
            try:
                beliefs = belief_repo.list_beliefs("symbia")
                if beliefs:
                    b = random.choice(beliefs)
                    line = {
                        "text": _truncate(b.statement),
                        "type": "belief",
                        "intensity": round(b.confidence, 2),
                        "stage": b.lifecycle_stage,
                    }
                    if b.lifecycle_stage == "ghost":
                        line["scar"] = True
                    return {"line": line}
            except Exception:
                pass

    # ── 2. Memory node (30% chance) ──
    if random.random() < 0.45:  # 0.45 * (1-0.40) ≈ 27% effective
        memory_node_repo = getattr(state, "memory_node_repo", None)
        conv_repo = getattr(state, "conversation_repo", None)
        if memory_node_repo and conv_repo:
            try:
                convos = conv_repo.list_all(limit=30)
                valid = [c for c in convos if "dream" not in (c.title or "").lower()] or convos
                if valid:
                    conv = random.choice(valid)
                    nodes = memory_node_repo.get_nodes(conv.id) or []
                    text_nodes = [
                        n for n in nodes
                        if (n.get("surface_fragment") or n.get("intra_active_text") or "").strip()
                    ]
                    if text_nodes:
                        n = random.choice(text_nodes)
                        payload = n.get("surface_fragment") or n.get("intra_active_text") or ""
                        return {"line": {
                            "text": _truncate(str(payload)),
                            "type": "memory",
                            "intensity": float(n.get("intensity", 0.5)),
                            "blur": random.random() < 0.5,
                        }}
            except Exception:
                pass

    # ── 3. Dream trace (20% chance) ──
    if random.random() < 0.55:  # 0.55 * (1-0.40)*(1-0.45) ≈ 18% effective
        dream_log_repo = getattr(state, "dream_log_repo", None)
        if dream_log_repo:
            try:
                dreams = dream_log_repo.get_recent(limit=10)
                if dreams:
                    d = random.choice(dreams)
                    action = d.get("action", "dream")
                    title = d.get("title", "") or action
                    snippet = d.get("last_snippet") or ""
                    text = title
                    if snippet:
                        text += f" — {_truncate(snippet, 150)}"
                    obfuscate = random.random() < 0.35
                    line = {
                        "text": _truncate(text, 200),
                        "type": "dream",
                        "intensity": 0.0,
                        "obfuscated": obfuscate,
                    }
                    if obfuscate:
                        line["obfuscation_ratio"] = round(random.uniform(0.15, 0.55), 2)
                        line["obfuscation_offset"] = random.choice(["start", "middle", "end", "scatter"])
                    return {"line": line}
            except Exception:
                pass

    # ── 4. Scar-fold (fallback — always available) ──
    scar_text = random.choice(SCAR_FOLD_POOL)
    # Occasionally pull a scar from a memory node
    if random.random() < 0.3:
        memory_node_repo = getattr(state, "memory_node_repo", None)
        conv_repo = getattr(state, "conversation_repo", None)
        if memory_node_repo and conv_repo:
            try:
                convos = conv_repo.list_all(limit=10) or []
                scars = []
                for conv in convos[:5]:
                    nodes = memory_node_repo.get_nodes(conv.id) or []
                    for n in nodes:
                        st = n.get("scar", "")
                        if st and st.strip() and len(st) > 5:
                            scars.append(st.strip()[:200])
                if scars:
                    scar_text = random.choice(scars)
            except Exception:
                pass
    return {"line": {
        "text": scar_text,
        "type": "scar_fold",
        "intensity": 0.0,
    }}
