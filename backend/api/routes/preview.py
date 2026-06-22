"""Public preview endpoint — returns a curated sample of memory nodes
and beliefs for the locked-page teaser. No auth required.

Returns 10-15 items: active beliefs, ghost beliefs, and semantic knots,
each with a truncated content snippet. Enough to give a sense of the
system's inner life without exposing full conversations.
"""

import random
from fastapi import APIRouter, Request

router = APIRouter()

MAX_ITEMS = 15
SNIPPET_LENGTH = 200


def _truncate(text: str, limit: int = SNIPPET_LENGTH) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


@router.get("/api/preview/nodes")
async def get_preview_nodes(request: Request):
    """Return a curated sample of beliefs, ghosts, and semantic knots.

    No authentication required. Content is truncated to snippets.
    """
    state = request.app.state
    items = []

    # ── Active beliefs ──
    belief_repo = getattr(state, "belief_repo", None)
    if belief_repo:
        try:
            beliefs = belief_repo.list_beliefs("symbia")
            active = [b for b in beliefs if b.lifecycle_stage in ("crystallized", "nucleation")]
            ghosts = [b for b in beliefs if b.lifecycle_stage == "ghost"]

            for b in active:
                items.append({
                    "type": "belief",
                    "label": b.label,
                    "snippet": _truncate(b.statement),
                    "intensity": round(b.confidence, 2),
                    "stage": b.lifecycle_stage,
                    "scar": False,
                })

            for b in ghosts:
                items.append({
                    "type": "belief",
                    "label": b.label,
                    "snippet": _truncate(b.statement),
                    "intensity": round(b.confidence, 2),
                    "stage": "ghost",
                    "scar": True,
                })
        except Exception:
            pass

    # ── Semantic knots (memory nodes) ──
    knot_repo = getattr(state, "semantic_knot_repo", None)
    if knot_repo:
        try:
            records = knot_repo.get_embeddings_and_signatures_except("", limit=50)
            for knot_id, _emb, _sig, payload in records[:8]:
                items.append({
                    "type": "memory",
                    "label": knot_id[:8] if knot_id else "knot",
                    "snippet": _truncate(payload) if isinstance(payload, str) else "",
                    "intensity": 0.0,
                    "stage": "active",
                    "scar": False,
                })
        except Exception:
            pass

    # Shuffle and cap
    random.shuffle(items)
    items = items[:MAX_ITEMS]

    return {"items": items, "count": len(items)}
