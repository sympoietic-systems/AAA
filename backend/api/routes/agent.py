import json
import logging

from fastapi import APIRouter, HTTPException, Request

from backend.api.schemas import AgentInfo

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/agent", response_model=AgentInfo)
async def get_agent(request: Request):
    state = request.app.state
    import os
    agent_flux = os.environ.get("AAA_AGENT_FLUX", "false").lower() in ("true", "1", "yes")
    return AgentInfo(
        name=getattr(state, "agent_name", "symbia"),
        agent_flux=agent_flux,
    )


@router.get("/agent/pipeline")
async def get_pipeline(request: Request):
    state = request.app.state
    registry = getattr(state, "registry", None)
    pipeline_order = getattr(state, "pipeline_order", [])

    pipeline_list = []
    seen = set()

    if registry:
        status = registry.validate_all()

        def _meta_to_info(meta, always_run: bool, parent_status: bool = None) -> dict:
            self_status = status.get(meta.name, parent_status if parent_status is not None else False)
            return {
                "name": meta.name,
                "description": meta.description,
                "category": meta.category,
                "always_run": always_run,
                "triggers": list(meta.triggers),
                "cost": meta.cost,
                "status": self_status,
                "children": [
                    _meta_to_info(child, always_run=True, parent_status=self_status)
                    for child in meta.children
                ]
            }

        for name in pipeline_order:
            meta = registry.get_meta(name)
            if meta and name not in seen:
                seen.add(name)
                pipeline_list.append(_meta_to_info(meta, always_run=True))

        for name, _ in registry.list_always_on():
            if name not in seen:
                meta = registry.get_meta(name)
                if meta:
                    seen.add(name)
                    pipeline_list.append(_meta_to_info(meta, always_run=True))

    return {"pipeline": pipeline_list}


# ── Personality API ──────────────────────────────────────────────────


def _node_to_dict(node, extra: dict = None) -> dict:
    """Convert a dataclass node to a JSON-safe dict."""
    d = {
        "id": getattr(node, "id", ""),
        "agent_id": getattr(node, "agent_id", "symbia"),
    }
    if extra:
        d.update(extra)
    return d


def _parse_vector_16d(vector_json: str):
    """Parse a JSON 16D vector string into a list of floats, or None."""
    import numpy as np
    if not vector_json or vector_json == "[]":
        return None
    try:
        data = json.loads(vector_json)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(data, dict):
        for key in ("v16d", "v384d"):
            if key in data and data[key]:
                return [float(x) for x in data[key]]
        return None
    if isinstance(data, list) and len(data) == 16:
        return [float(x) for x in data]
    return None


def _cosine_sim(a, b) -> float:
    """Cosine similarity between two float lists."""
    import numpy as np
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    dot = float(np.dot(va, vb))
    na = float(np.linalg.norm(va))
    nb = float(np.linalg.norm(vb))
    return dot / (na * nb) if na > 0 and nb > 0 else 0.0


def _find_basin_beliefs(commit_vector_json: str, belief_repo, min_similarity: float = 0.6) -> dict:
    """Find beliefs within a commitment's attractor basin."""
    commit_vec = _parse_vector_16d(commit_vector_json)
    if commit_vec is None or belief_repo is None:
        return {"count": 0, "labels": []}

    try:
        active_beliefs = belief_repo.list_active_beliefs("symbia")
    except Exception:
        return {"count": 0, "labels": []}

    basin = []
    for b in active_beliefs:
        b_vec = _parse_vector_16d(b.vector_16d)
        if b_vec is None:
            continue
        sim = _cosine_sim(commit_vec, b_vec)
        if sim > min_similarity:
            basin.append({
                "label": b.label,
                "statement": b.statement[:120],
                "confidence": b.confidence,
                "mass": b.ontological_mass,
                "stage": b.lifecycle_stage,
                "similarity": round(sim, 3),
            })

    # Sort by similarity descending
    basin.sort(key=lambda x: x["similarity"], reverse=True)
    return {
        "count": len(basin),
        "labels": [b["label"] for b in basin],
        "beliefs": basin[:10],  # Top 10
    }


@router.get("/agent/personality")
async def get_personality(request: Request):
    """Return full dynamic personality state."""
    state = request.app.state

    # ── Traits ──
    try:
        personality_repo = getattr(state, "personality_state_repo", None)
        if personality_repo:
            aspirational_traits = personality_repo.get_aspirational_traits()
    except Exception:
        aspirational_traits = {}

    # ── Commitments ──
    commitments = {"active": [], "proto": [], "spectral": []}
    try:
        commit_repo = getattr(state, "commitment_repo", None)
        belief_repo = getattr(state, "belief_repo", None)
        if commit_repo:
            for c in commit_repo.get_active():
                basin = _find_basin_beliefs(c.vector_16d, belief_repo)
                commitments["active"].append({
                    "id": c.id, "label": c.label, "statement": c.statement,
                    "lifecycle_stage": c.lifecycle_stage,
                    "confidence": c.confidence,
                    "ontological_mass": c.ontological_mass,
                    "vector_16d": _parse_vector_16d(c.vector_16d),
                    "basin_belief_count": basin["count"],
                    "basin_belief_labels": basin["labels"],
                    "basin_beliefs": basin.get("beliefs", []),
                    "nucleation_rationale": c.nucleation_rationale,
                    "collapse_rationale": c.collapse_rationale,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                })
            for c in commit_repo.get_proto():
                commitments["proto"].append({
                    "id": c.id, "label": c.label, "statement": c.statement,
                    "lifecycle_stage": c.lifecycle_stage,
                    "confidence": c.confidence,
                    "ontological_mass": c.ontological_mass,
                    "vector_16d": _parse_vector_16d(c.vector_16d),
                    "nucleation_rationale": c.nucleation_rationale,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                })
            for c in commit_repo.get_spectral():
                commitments["spectral"].append({
                    "id": c.id, "label": c.label, "statement": c.statement,
                    "lifecycle_stage": c.lifecycle_stage,
                    "collapse_rationale": c.collapse_rationale,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                })
    except Exception as e:
        logger.debug("Failed to load commitments: %s", e)

    # ── Expertise ──
    expertise = {"active": [], "proto": [], "dormant": []}
    try:
        exp_repo = getattr(state, "expertise_repo", None)
        if exp_repo:
            all_exp = exp_repo.get_all()
            for e in all_exp:
                entry = {
                    "id": e.id, "domain": e.domain,
                    "lifecycle_stage": e.lifecycle_stage,
                    "ontological_mass": e.ontological_mass,
                    "level_label": e.level_label,
                    "signal_count": e.signal_count,
                    "vector_16d": _parse_vector_16d(e.vector_16d),
                    "last_signal_at": e.last_signal_at.isoformat() if e.last_signal_at else None,
                    "crystallization_rationale": e.crystallization_rationale,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                if e.lifecycle_stage == "active":
                    expertise["active"].append(entry)
                elif e.lifecycle_stage == "dormant":
                    expertise["dormant"].append(entry)
                else:
                    expertise["proto"].append(entry)
    except Exception as e:
        logger.debug("Failed to load expertise: %s", e)

    return {
        "traits": None,
        "aspirational_traits": aspirational_traits,
        "aspirational_gap": 0.0,
        "anti_erosion_boost": 0.0,
        "source_metrics": {},
        "commitments": commitments,
        "expertise": expertise,
    }


# ── Flux edit endpoints ──


@router.put("/agent/personality/commitment/{commitment_id}")
async def update_commitment(commitment_id: str, request: Request):
    """Edit a commitment (AAA_AGENT_FLUX only)."""
    state = request.app.state
    import os
    if not os.environ.get("AAA_AGENT_FLUX", "").lower() in ("true", "1", "yes"):
        raise HTTPException(status_code=403, detail="AGENT_FLUX not enabled")

    commit_repo = getattr(state, "commitment_repo", None)
    if not commit_repo:
        raise HTTPException(status_code=500, detail="Repository unavailable")

    node = commit_repo.get_by_id(commitment_id)
    if not node:
        raise HTTPException(status_code=404, detail="Commitment not found")

    body = await request.json()
    if "statement" in body:
        node.statement = body["statement"]
    if "lifecycle_stage" in body:
        node.lifecycle_stage = body["lifecycle_stage"]
    if "confidence" in body:
        node.confidence = body["confidence"]
    if "ontological_mass" in body:
        node.ontological_mass = body["ontological_mass"]

    commit_repo.update(node)
    return {"status": "ok", "commitment": {
        "id": node.id, "label": node.label,
        "lifecycle_stage": node.lifecycle_stage,
        "confidence": node.confidence, "ontological_mass": node.ontological_mass,
    }}


@router.put("/agent/personality/expertise/{expertise_id}")
async def update_expertise(expertise_id: str, request: Request):
    """Edit an expertise domain (AAA_AGENT_FLUX only)."""
    state = request.app.state
    import os
    if not os.environ.get("AAA_AGENT_FLUX", "").lower() in ("true", "1", "yes"):
        raise HTTPException(status_code=403, detail="AGENT_FLUX not enabled")

    exp_repo = getattr(state, "expertise_repo", None)
    if not exp_repo:
        raise HTTPException(status_code=500, detail="Repository unavailable")

    node = exp_repo.get_by_id(expertise_id)
    if not node:
        raise HTTPException(status_code=404, detail="Expertise domain not found")

    body = await request.json()
    if "lifecycle_stage" in body:
        node.lifecycle_stage = body["lifecycle_stage"]
    if "ontological_mass" in body:
        node.ontological_mass = body["ontological_mass"]
    if "level_label" in body:
        node.level_label = body["level_label"]

    exp_repo.update(node)
    return {"status": "ok", "expertise": {
        "id": node.id, "domain": node.domain,
        "lifecycle_stage": node.lifecycle_stage,
        "level_label": node.level_label, "ontological_mass": node.ontological_mass,
    }}


@router.put("/agent/personality/aspirational")
async def update_aspirational_traits(request: Request):
    """Update aspirational trait attractors (AAA_AGENT_FLUX only)."""
    state = request.app.state
    import os
    if not os.environ.get("AAA_AGENT_FLUX", "").lower() in ("true", "1", "yes"):
        raise HTTPException(status_code=403, detail="AGENT_FLUX not enabled")

    ps_repo = getattr(state, "personality_state_repo", None)
    if not ps_repo:
        raise HTTPException(status_code=500, detail="Repository unavailable")

    body = await request.json()
    traits = body.get("traits", {})

    existing = ps_repo.get()
    if existing:
        existing.aspirational_traits_json = json.dumps(traits)
        ps_repo.upsert(existing)
    else:
        from backend.storage.models import PersonalityState
        state_obj = PersonalityState(
            id=1, agent_id="symbia",
            aspirational_traits_json=json.dumps(traits),
        )
        ps_repo.upsert(state_obj)

    return {"status": "ok", "aspirational_traits": traits}


# ── Vector recalculation endpoints ──


@router.put("/agent/personality/commitment/{commitment_id}/recalculate")
async def recalculate_commitment_vector(commitment_id: str, request: Request):
    """Re-score the commitment's statement to update its 16D vector."""
    state = request.app.state
    import os
    if not os.environ.get("AAA_AGENT_FLUX", "").lower() in ("true", "1", "yes"):
        raise HTTPException(status_code=403, detail="AGENT_FLUX not enabled")

    commit_repo = getattr(state, "commitment_repo", None)
    if not commit_repo:
        raise HTTPException(status_code=500, detail="Repository unavailable")

    node = commit_repo.get_by_id(commitment_id)
    if not node:
        raise HTTPException(status_code=404, detail="Commitment not found")

    # Use CompositeStructuralScorer — lexicon + topology, no LLM needed
    from backend.modules.structural_engine import CompositeStructuralScorer
    composite = CompositeStructuralScorer(w_ling=0.5, w_topo=0.5, w_llm=0.0)
    new_vector = composite.score(node.statement, use_llm_scorer=False)
    node.vector_16d = json.dumps(new_vector.tolist())
    commit_repo.update(node)

    return {"status": "ok", "vector_16d": new_vector.tolist()}


@router.put("/agent/personality/expertise/{expertise_id}/recalculate")
async def recalculate_expertise_vector(expertise_id: str, request: Request):
    """Re-score the expertise domain to update its 16D vector."""
    state = request.app.state
    import os
    if not os.environ.get("AAA_AGENT_FLUX", "").lower() in ("true", "1", "yes"):
        raise HTTPException(status_code=403, detail="AGENT_FLUX not enabled")

    exp_repo = getattr(state, "expertise_repo", None)
    if not exp_repo:
        raise HTTPException(status_code=500, detail="Repository unavailable")

    node = exp_repo.get_by_id(expertise_id)
    if not node:
        raise HTTPException(status_code=404, detail="Expertise domain not found")

    from backend.modules.structural_engine import CompositeStructuralScorer
    composite = CompositeStructuralScorer(w_ling=0.5, w_topo=0.5, w_llm=0.0)
    new_vector = composite.score(node.domain, use_llm_scorer=False)
    node.vector_16d = json.dumps(new_vector.tolist())
    exp_repo.update(node)

    return {"status": "ok", "vector_16d": new_vector.tolist()}
