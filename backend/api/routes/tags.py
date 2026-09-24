import asyncio

from fastapi import APIRouter, Depends, Request

from backend.api.deps import get_conversation_repo, require_conversation
from backend.api.schemas import TagCreateRequest

router = APIRouter()


def _add_tag(conv_repo, conversation_id: str, tag: str) -> None:
    require_conversation(conv_repo, conversation_id)
    conv_repo.add_tag(conversation_id, tag, "semantic")


def _remove_tag(conv_repo, conversation_id: str, tag: str) -> None:
    require_conversation(conv_repo, conversation_id)
    conv_repo.remove_tag(conversation_id, tag)


@router.post("/conversations/{conversation_id}/tags")
async def add_conversation_tag(
    conversation_id: str,
    body: TagCreateRequest,
    conv_repo=Depends(get_conversation_repo),
):
    await asyncio.to_thread(_add_tag, conv_repo, conversation_id, body.tag.strip())
    return {"status": "success"}


@router.delete("/conversations/{conversation_id}/tags/{tag}")
async def remove_conversation_tag(
    conversation_id: str,
    tag: str,
    conv_repo=Depends(get_conversation_repo),
):
    await asyncio.to_thread(_remove_tag, conv_repo, conversation_id, tag)
    return {"status": "success"}


@router.get("/tags")
async def get_all_unique_tags(request: Request, conv_repo=Depends(get_conversation_repo)):
    if not conv_repo:
        return {"tags": []}
    tags = await asyncio.to_thread(conv_repo.get_all_unique_tags)
    return {"tags": tags}
