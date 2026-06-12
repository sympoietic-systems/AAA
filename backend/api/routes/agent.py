from fastapi import APIRouter, Request

from backend.api.schemas import AgentInfo

router = APIRouter()


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
