import json
import logging

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request

from backend.api.deps import (
    agent_flux_enabled,
    require_agent_flux,
    get_app_state,
    get_agent_name,
    get_registry,
    get_pipeline_order,
    get_personality_state_repo,
    get_commitment_repo,
    get_belief_repo,
    get_expertise_repo,
    get_structural_scorer,
)
from backend.api.schemas import AgentInfo
from backend.utils.vector import parse_vector_16d, cosine_similarity

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/agent", response_model=AgentInfo)
async def get_agent(agent_name=Depends(get_agent_name)):
    return AgentInfo(
        name=agent_name,
        agent_flux=agent_flux_enabled(),
    )


@router.get("/agent/pipeline")
async def get_pipeline(registry=Depends(get_registry), pipeline_order=Depends(get_pipeline_order)):
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


def _find_basin_beliefs(commit_vector_json: str, belief_repo, min_similarity: float = 0.6) -> dict:
    """Find beliefs within a commitment's attractor basin."""
    commit_vec = parse_vector_16d(commit_vector_json)
    if commit_vec is None or belief_repo is None:
        return {"count": 0, "labels": []}

    try:
        active_beliefs = belief_repo.list_active_beliefs("symbia")
    except Exception:
        return {"count": 0, "labels": []}

    basin = []
    for b in active_beliefs:
        b_vec = parse_vector_16d(b.vector_16d)
        if b_vec is None:
            continue
        sim = cosine_similarity(commit_vec, b_vec)
        if sim > min_similarity:
            basin.append({
                "label": b.label,
                "statement": b.statement[:120],
                "confidence": b.confidence,
                "mass": b.ontological_mass,
                "stage": b.lifecycle_stage,
                "similarity": round(sim, 3),
            })

    basin.sort(key=lambda x: x["similarity"], reverse=True)
    return {
        "count": len(basin),
        "labels": [b["label"] for b in basin],
        "beliefs": basin[:10],
    }


@router.get("/agent/personality")
async def get_personality(
    personality_repo=Depends(get_personality_state_repo),
    commit_repo=Depends(get_commitment_repo),
    belief_repo=Depends(get_belief_repo),
    exp_repo=Depends(get_expertise_repo),
):
    """Return full dynamic personality state."""
    # ── Traits ──
    try:
        aspirational_traits = personality_repo.get_aspirational_traits() if personality_repo else {}
    except Exception:
        aspirational_traits = {}

    # ── Commitments ──
    commitments = {"active": [], "proto": [], "spectral": []}
    try:
        if commit_repo:
            for c in commit_repo.get_active():
                basin = _find_basin_beliefs(c.vector_16d, belief_repo)
                commitments["active"].append({
                    "id": c.id, "label": c.label, "statement": c.statement,
                    "lifecycle_stage": c.lifecycle_stage,
                    "confidence": c.confidence,
                    "ontological_mass": c.ontological_mass,
                    "vector_16d": parse_vector_16d(c.vector_16d),
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
                    "vector_16d": parse_vector_16d(c.vector_16d),
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
        if exp_repo:
            all_exp = exp_repo.get_all()
            for e in all_exp:
                entry = {
                    "id": e.id, "domain": e.domain,
                    "description": e.description or "",
                    "lifecycle_stage": e.lifecycle_stage,
                    "ontological_mass": e.ontological_mass,
                    "level_label": e.level_label,
                    "signal_count": e.signal_count,
                    "vector_16d": parse_vector_16d(e.vector_16d),
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


@router.put("/agent/personality/commitment/{commitment_id}", dependencies=[Depends(require_agent_flux)])
async def update_commitment(commitment_id: str, request: Request, commit_repo=Depends(get_commitment_repo)):
    """Edit a commitment (AAA_AGENT_FLUX only)."""
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


@router.put("/agent/personality/expertise/{expertise_id}", dependencies=[Depends(require_agent_flux)])
async def update_expertise(expertise_id: str, request: Request, exp_repo=Depends(get_expertise_repo)):
    """Edit an expertise domain (AAA_AGENT_FLUX only)."""
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


@router.put("/agent/personality/aspirational", dependencies=[Depends(require_agent_flux)])
async def update_aspirational_traits(request: Request, ps_repo=Depends(get_personality_state_repo)):
    """Update aspirational trait attractors (AAA_AGENT_FLUX only)."""
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


@router.put("/agent/personality/commitment/{commitment_id}/recalculate", dependencies=[Depends(require_agent_flux)])
async def recalculate_commitment_vector(
    commitment_id: str,
    commit_repo=Depends(get_commitment_repo),
    structural_scorer=Depends(get_structural_scorer),
):
    """Re-score the commitment's statement via the pipeline's structural scorer."""
    if not commit_repo or not structural_scorer:
        raise HTTPException(status_code=500, detail="Repository or scorer unavailable")

    node = commit_repo.get_by_id(commitment_id)
    if not node:
        raise HTTPException(status_code=404, detail="Commitment not found")

    new_vector = await structural_scorer._scorer.score_async(node.statement)
    node.vector_16d = json.dumps(new_vector.tolist())
    commit_repo.update(node)

    return {"status": "ok", "vector_16d": new_vector.tolist()}


@router.put("/agent/personality/expertise/{expertise_id}/recalculate", dependencies=[Depends(require_agent_flux)])
async def recalculate_expertise_vector(
    expertise_id: str,
    exp_repo=Depends(get_expertise_repo),
    structural_scorer=Depends(get_structural_scorer),
):
    """Re-score the expertise domain via the pipeline's structural scorer."""
    if not exp_repo or not structural_scorer:
        raise HTTPException(status_code=500, detail="Repository or scorer unavailable")

    node = exp_repo.get_by_id(expertise_id)
    if not node:
        raise HTTPException(status_code=404, detail="Expertise domain not found")

    new_vector = await structural_scorer._scorer.score_async(node.domain)
    node.vector_16d = json.dumps(new_vector.tolist())
    exp_repo.update(node)

    return {"status": "ok", "vector_16d": new_vector.tolist()}
