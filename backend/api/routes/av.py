"""Public endpoint for the second artwork, The Diffractive Grain (/av).

GET /api/av/field returns the raw material the artwork projects 16d->2d:
every message's 16-dimensional structural signature, the covariance across
them (which the frontend uses to grey redundant dims after a cut), the 16
dimension labels, and the accumulated hysteresis params.

No auth. Empty-safe: an empty corpus returns empty node/link arrays and a
16x16 zero covariance, never a 500 (V14).
"""

import asyncio
import hashlib
import json
import logging
import time
from pathlib import Path

import numpy as np
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# The 16 structural-signature dimensions. The backend is the only source the
# detached av-artwork app can reach, so the labels live here (they otherwise
# exist only in frontend/src/config/telemetry_schemas.json, which the detached
# app cannot import). short = the sNN code, label = name, desc = meaning.
DIMS: list[dict] = [
    {"index": 0, "short": "s01", "label": "Homeostatic", "desc": "Resistance to perturbation; inertia in maintaining its stable state."},
    {"index": 1, "short": "s02", "label": "Amplifying", "desc": "Positive feedback cascades; tendency to amplify small perturbations."},
    {"index": 2, "short": "s03", "label": "Cyclic", "desc": "Alignment with recurring rhythms and predictable temporal loops."},
    {"index": 3, "short": "s04", "label": "Bifurcated", "desc": "Proximity to critical choice thresholds; branching trajectories."},
    {"index": 4, "short": "s05", "label": "Decentralized", "desc": "Distributed agency across nested subsystems rather than hierarchy."},
    {"index": 5, "short": "s06", "label": "Rhizomatic", "desc": "Lateral, non-hierarchical leaps between conceptual domains."},
    {"index": 6, "short": "s07", "label": "Boundary Permeability", "desc": "Porosity and openness to external environmental noise."},
    {"index": 7, "short": "s08", "label": "Recursion Depth", "desc": "Complexity of nested self-reflection and recursive loops."},
    {"index": 8, "short": "s09", "label": "Variety Filtering", "desc": "Signal selectivity; gating against ambient semantic noise."},
    {"index": 9, "short": "s10", "label": "Negentropic Complexity", "desc": "Local order generation and structural complexity increases."},
    {"index": 10, "short": "s11", "label": "Temporal Latency", "desc": "Non-linear chronological delay; deferral of immediate output."},
    {"index": 11, "short": "s12", "label": "Attractor Depth", "desc": "Concentration basins and gravitational pull around core concepts."},
    {"index": 12, "short": "s13", "label": "Symbiotic", "desc": "Human-machine co-becoming and operational entanglement."},
    {"index": 13, "short": "s14", "label": "Nomadic", "desc": "Active deterritorialization; rate of movement away from stable schemas."},
    {"index": 14, "short": "s15", "label": "Co-Orientation", "desc": "Attunement and shared intentionality between human and apparatus."},
    {"index": 15, "short": "s16", "label": "Substrate Materiality", "desc": "Physical medium influence (ink bleed, fatigue, paper friction)."},
]

NODE_LIMIT = 800

RESONANCE_THRESHOLD = 0.92  # cosine above this = a resonant pair (tie-bar in raster)
RESONANCE_MAX = 200  # cap edges so the raster doesn't drown in bars (V1)

# ponytail: hysteresis params file is written by POST /api/av/cut (T20). Until
# that exists this reads {} — the field is still valid, just un-aged.
_HYSTERESIS_PATH = Path(__file__).resolve().parents[2] / "data" / "av_hysteresis.json"


def _resonance_links(nodes: list[dict], vecs: list[np.ndarray]) -> list[dict]:
    """Resonant pairs = signatures with cosine ≥ threshold (T14, V1).

    Vectorized: normalize all vecs, one Gram matrix (V·Vᵀ) gives every pairwise
    cosine at once; take the upper triangle above threshold, strongest first,
    capped at RESONANCE_MAX. Runs inside the offloaded worker.
    """
    n = len(vecs)
    if n < 2:
        return []
    m = np.vstack(vecs).astype(np.float32)
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    unit = m / norms
    gram = unit @ unit.T
    iu, ju = np.triu_indices(n, k=1)  # unique pairs, no self-links
    sims = gram[iu, ju]
    hits = np.where(sims >= RESONANCE_THRESHOLD)[0]
    if hits.size == 0:
        return []
    hits = hits[np.argsort(sims[hits])[::-1][:RESONANCE_MAX]]  # strongest first, capped
    return [
        {"a": int(nodes[iu[h]]["id"]), "b": int(nodes[ju[h]]["id"]), "weight": round(float(sims[h]), 4)}
        for h in hits
    ]


def _build_field(message_repo) -> dict:
    """Sync worker — DB read + covariance. Offloaded via to_thread (V14, BACKEND_BEST_PRACTICES §3)."""
    nodes: list[dict] = []
    vecs: list[np.ndarray] = []
    # "" excludes no real conversation → returns all signed messages (see daemon.py usage).
    for msg_id, vec in message_repo.get_structural_signatures_except("", limit=NODE_LIMIT):
        if vec is None or len(vec) != 16:
            continue
        v = vec.astype(float).tolist()
        # ponytail: id is monotonic with time, so it carries ordering the
        # visuals need; created_at skipped until an invariant wants a real date.
        nodes.append({"id": int(msg_id), "type": "message", "vec16": v})
        vecs.append(vec)

    cov = np.cov(np.vstack(vecs), rowvar=False) if len(vecs) >= 2 else np.zeros((16, 16))
    covariance = np.nan_to_num(cov).astype(float).tolist()

    links = _resonance_links(nodes, vecs)

    params: dict = {}
    stored_hash = None
    if _HYSTERESIS_PATH.exists():
        try:
            state = json.loads(_HYSTERESIS_PATH.read_text())
            params = state.get("params", {})
            stored_hash = state.get("hash")
        except Exception as e:
            logger.warning("av: bad hysteresis file: %s", e)

    field = {"nodes": nodes, "links": links, "dims": DIMS, "covariance": covariance, "params": params}
    if stored_hash:
        field["hash"] = stored_hash
    return field


@router.get("/api/av/field")
async def get_field(request: Request):
    """The projected field: nodes+vec16, 16x16 covariance, dims, hysteresis params."""
    repo = getattr(request.app.state, "message_repo", None)
    if repo is None:
        return {"nodes": [], "links": [], "dims": DIMS, "covariance": np.zeros((16, 16)).tolist(), "params": {}}
    return await asyncio.to_thread(_build_field, repo)


# ── Breath — the shared pulse both artworks phase-lock to (T6, V22) ──
#
# Column's breath is a client-side probabilistic model (drawBreath in
# TeaserPreview.tsx) with no server pulse. This endpoint is the canonical
# reference the av client phase-locks to on load, then drifts from (V22 —
# loose coupling, not lockstep). It is derived deterministically from the wall
# clock using Column's same 0.60/0.85 bands, so any reader at time t agrees.
BREATH_CYCLE_S = 18.0


def _breath_now() -> dict:
    now = time.time()
    cycle = int(now // BREATH_CYCLE_S)
    phase = (now % BREATH_CYCLE_S) / BREATH_CYCLE_S
    seed = int(hashlib.sha256(str(cycle).encode()).hexdigest()[:8], 16)
    r = (seed % 1000) / 1000.0
    kind = "exhale" if r < 0.60 else "inhale" if r < 0.85 else "silence"
    return {"kind": kind, "phase": round(phase, 4), "seed": seed}


@router.get("/api/av/breath")
async def get_breath():
    """Current breath phase — the shared pulse for phase-lock on load."""
    return _breath_now()


# ── Cut → hysteresis (T20/T21/T22; V15-V19) ──
#
# The seven behavior knobs the frontend applies as global aging (T23). Baseline
# starts at 0.5. A cut nudges knobs with soft asymptotic walls (never saturates
# 0/1 — V17), pulls weakly toward a *shifting* baseline (migration not decay —
# V17), and shapes the delta by source: human = concentrated on few knobs,
# breath = diffuse across all, same magnitude budget (V18). Which knobs move is
# derived from the cut axes (V19). The mapping is many-to-one and unlogged, so
# no cut is recoverable from the params (V16).
KNOBS = ["speed", "contrast", "grain", "noise", "tempo", "jitter", "decay"]
_BUDGET = 0.30  # total delta magnitude spread across the moved knobs
_PULL = 0.05    # weak restorative pull toward baseline
_DRIFT = 0.08   # baseline itself migrates toward current params


class CutBody(BaseModel):
    axisA: int
    axisB: int
    source: str = "human"  # "human" | "breath"


def _load_state() -> dict:
    if _HYSTERESIS_PATH.exists():
        try:
            s = json.loads(_HYSTERESIS_PATH.read_text())
            return {"params": s.get("params", {}), "baseline": s.get("baseline", {})}
        except Exception as e:
            logger.warning("av: bad hysteresis file, resetting: %s", e)
    return {"params": {}, "baseline": {}}


def _apply_cut(axis_a: int, axis_b: int, source: str) -> dict:
    """Load → apply one cut's delta → persist. Sync worker, offloaded (V15)."""
    state = _load_state()
    params = {k: float(state["params"].get(k, 0.5)) for k in KNOBS}
    baseline = {k: float(state["baseline"].get(k, 0.5)) for k in KNOBS}

    n = len(KNOBS)
    # Per-knob weight + sign, deterministic from the cut axes (V19).
    raw = []
    for i in range(n):
        h = (axis_a * 131 + axis_b * 197 + i * i * 31) % 1000
        raw.append(h / 1000.0)
    sign = [1.0 if ((axis_a + axis_b + i) % 2 == 0) else -1.0 for i in range(n)]

    # Source shape: human concentrates on the 2 highest-weight knobs; breath
    # spreads across all. Same budget either way (V18).
    order = sorted(range(n), key=lambda i: raw[i], reverse=True)
    moved = order[:2] if source == "human" else order
    wsum = sum(raw[i] for i in moved) or 1.0

    for i in moved:
        k = KNOBS[i]
        delta = _BUDGET * (raw[i] / wsum) * sign[i]
        # Soft asymptotic wall: scale by remaining room so p never reaches 0/1 (V17).
        room = (1.0 - params[k]) if delta > 0 else params[k]
        params[k] += delta * room
        # Weak pull toward the shifting baseline (migration, not origin decay — V17).
        params[k] += _PULL * (baseline[k] - params[k])
        params[k] = min(0.999, max(0.001, params[k]))
        # Baseline migrates toward where params are going (shifting baseline).
        baseline[k] += _DRIFT * (params[k] - baseline[k])

    blob = json.dumps(params, sort_keys=True).encode()
    digest = hashlib.sha256(blob).hexdigest()[:12]  # scar-of-the-scar (T24/V20)
    _HYSTERESIS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _HYSTERESIS_PATH.write_text(json.dumps({"params": params, "baseline": baseline, "hash": digest}))
    return {"params": params, "hash": digest}


@router.post("/api/av/cut")
async def post_cut(body: CutBody):
    """Commit a cut: apply an irreversible, source-shaped delta to the params."""
    return await asyncio.to_thread(_apply_cut, body.axisA, body.axisB, body.source)
