from fastapi import APIRouter, Depends, Request

from backend.api.deps import get_conversation_repo, require_conversation
from backend.api.schemas import TagCreateRequest

router = APIRouter()


@router.post("/conversations/{conversation_id}/tags")
async def add_conversation_tag(
    conversation_id: str,
    body: TagCreateRequest,
    conv_repo=Depends(get_conversation_repo),
):
    require_conversation(conv_repo, conversation_id)
    conv_repo.add_tag(conversation_id, body.tag.strip(), "semantic")
    return {"status": "success"}


@router.delete("/conversations/{conversation_id}/tags/{tag}")
async def remove_conversation_tag(
    conversation_id: str,
    tag: str,
    conv_repo=Depends(get_conversation_repo),
):
    require_conversation(conv_repo, conversation_id)
    conv_repo.remove_tag(conversation_id, tag)
    return {"status": "success"}


@router.get("/tags")
async def get_all_unique_tags(request: Request, conv_repo=Depends(get_conversation_repo)):
    if not conv_repo:
        return {"tags": []}
    tags = conv_repo.get_all_unique_tags()
    return {"tags": tags}
