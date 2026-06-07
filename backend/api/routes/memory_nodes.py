from fastapi import APIRouter, Request

from .schemas import MemoryNodeInfo, MemoryNodeListResponse

router = APIRouter()


@router.get("/conversations/{conversation_id}/memory-nodes", response_model=MemoryNodeListResponse)
async def get_memory_nodes(conversation_id: str, request: Request):
    state = request.app.state
    repo = getattr(state, "memory_node_repo", None)
    if not repo:
        return MemoryNodeListResponse(nodes=[])
    nodes = repo.get_nodes(conversation_id)
    return MemoryNodeListResponse(
        nodes=[MemoryNodeInfo(**n) for n in nodes]
    )
