from fastapi import APIRouter, HTTPException, Request

from backend.api.schemas import TagCreateRequest

router = APIRouter()


@router.post("/conversations/{conversation_id}/tags")
async def add_conversation_tag(conversation_id: str, body: TagCreateRequest, request: Request):
    state = request.app.state
    conv_repo = getattr(state, "conversation_repo", None)
    if not conv_repo:
        raise HTTPException(status_code=404, detail="Conversations not available")
    conv = conv_repo.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv_repo.add_tag(conversation_id, body.tag.strip(), "semantic")
    return {"status": "success"}


@router.delete("/conversations/{conversation_id}/tags/{tag}")
async def remove_conversation_tag(conversation_id: str, tag: str, request: Request):
    state = request.app.state
    conv_repo = getattr(state, "conversation_repo", None)
    if not conv_repo:
        raise HTTPException(status_code=404, detail="Conversations not available")
    conv = conv_repo.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv_repo.remove_tag(conversation_id, tag)
    return {"status": "success"}


@router.get("/tags")
async def get_all_unique_tags(request: Request):
    state = request.app.state
    conv_repo = getattr(state, "conversation_repo", None)
    if not conv_repo:
        return {"tags": []}
    tags = conv_repo.get_all_unique_tags()
    return {"tags": tags}
