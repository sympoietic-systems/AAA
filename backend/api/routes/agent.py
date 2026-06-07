from fastapi import APIRouter, Request

from backend.api.schemas import AgentInfo

router = APIRouter()


@router.get("/agent", response_model=AgentInfo)
async def get_agent(request: Request):
    state = request.app.state
    return AgentInfo(
        name=getattr(state, "agent_name", "symbia"),
    )
