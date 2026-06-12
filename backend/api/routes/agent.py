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
