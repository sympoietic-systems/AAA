from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.deps import (
    get_agent_name,
    get_background_engine,
    get_conversation_use_cases,
    get_embedder,
    require_agent_flux,
)
from backend.api.schemas import (
    ChatResponse,
    CommitBranchRequest,
    CommitLinkRequest,
    ConversationInfo,
    ConversationListResponse,
    ConversationTreeResponse,
    ConversationUpdateRequest,
    SpectralSuggestion,
    TreeLink,
    TreeNode,
)
from backend.services.conversation import ConversationUseCases
from backend.utils.token_counter import estimate_tokens

router = APIRouter()


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    tag: str | None = Query(default=None, max_length=100),
    search: str | None = Query(default=None, max_length=500),
    limit: int | None = Query(default=None, ge=1, le=100),
    offset: int | None = Query(default=None, ge=0),
    conversations: ConversationUseCases = Depends(get_conversation_use_cases),
):
    safe_limit = limit
    safe_offset = offset if offset is not None else (0 if limit is not None else None)
    items, total_count = await conversations.list(tag=tag, search=search, limit=safe_limit, offset=safe_offset)
    response_items = [ConversationInfo(**item) for item in items]

    has_more = False
    if safe_limit is not None and safe_offset is not None:
        has_more = (safe_offset + safe_limit) < total_count

    return ConversationListResponse(conversations=response_items, total_count=total_count, has_more=has_more)


@router.get("/conversations/{conversation_id}", response_model=ConversationInfo)
async def get_conversation(
    conversation_id: str,
    conversations: ConversationUseCases = Depends(get_conversation_use_cases),
):
    try:
        return ConversationInfo(**(await conversations.get(conversation_id)))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc


@router.patch("/conversations/{conversation_id}", response_model=ConversationInfo)
async def update_conversation(
    conversation_id: str,
    body: ConversationUpdateRequest,
    conversations: ConversationUseCases = Depends(get_conversation_use_cases),
):
    try:
        return ConversationInfo(**(await conversations.update_title(conversation_id, body.title)))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc


@router.delete("/conversations/{conversation_id}", dependencies=[Depends(require_agent_flux)])
async def delete_conversation(
    conversation_id: str,
    conversations: ConversationUseCases = Depends(get_conversation_use_cases),
):
    try:
        await conversations.delete(conversation_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc
    return {"status": "deleted", "id": conversation_id}


@router.delete("/conversations/{conversation_id}/messages/{message_id}", dependencies=[Depends(require_agent_flux)])
async def delete_message(
    conversation_id: str,
    message_id: int,
    conversations: ConversationUseCases = Depends(get_conversation_use_cases),
):
    try:
        await conversations.delete_message(conversation_id, message_id)
    except LookupError as exc:
        detail = str(exc)
        raise HTTPException(status_code=404, detail=detail) from exc
    return {"status": "deleted", "id": message_id}


@router.post("/conversations/{conversation_id}/generate-human-summary", response_model=ConversationInfo)
async def generate_human_summary(
    conversation_id: str,
    conversations: ConversationUseCases = Depends(get_conversation_use_cases),
    background_engine=Depends(get_background_engine),
):
    try:
        return ConversationInfo(**(await conversations.generate_human_summary(conversation_id, background_engine)))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/conversations/{conversation_id}/generate-title", response_model=ConversationInfo)
async def generate_conversation_title(
    conversation_id: str,
    conversations: ConversationUseCases = Depends(get_conversation_use_cases),
    background_engine=Depends(get_background_engine),
):
    try:
        return ConversationInfo(**(await conversations.generate_title(conversation_id, background_engine)))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc


@router.post("/conversations/{conversation_id}/commit-branch", response_model=ChatResponse)
async def commit_branch(
    conversation_id: str,
    body: CommitBranchRequest,
    conversations: ConversationUseCases = Depends(get_conversation_use_cases),
    embedder=Depends(get_embedder),
    agent_id: str = Depends(get_agent_name),
):
    try:
        msg, embedding_generated = await conversations.commit_branch(
            conversation_id,
            speaker=body.speaker,
            content=body.content,
            parent_message_id=body.parent_message_id,
            agent_id=agent_id,
            embedder=embedder,
            content_tokens=estimate_tokens(body.content),
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc

    return ChatResponse(
        id=msg.id,
        timestamp=msg.timestamp,
        conversation_id=conversation_id,
        speaker=msg.speaker,
        content=msg.content,
        content_tokens=msg.content_tokens,
        embedding_generated=embedding_generated,
        parent_message_id=msg.parent_message_id,
    )


@router.get("/conversations/{conversation_id}/tree", response_model=ConversationTreeResponse)
async def get_conversation_tree(
    conversation_id: str,
    conversations: ConversationUseCases = Depends(get_conversation_use_cases),
):
    try:
        raw_msgs, raw_links = await conversations.tree(conversation_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc
    nodes = []
    for m in raw_msgs:
        trimmed_content = m.content[:120] + "..." if len(m.content) > 120 else m.content
        nodes.append(
            TreeNode(
                id=m.id,
                speaker=m.speaker,
                content=trimmed_content,
                parent_message_id=m.parent_message_id,
                timestamp=m.timestamp,
            )
        )

    links = []
    for link in raw_links:
        links.append(
            TreeLink(
                id=link.id,
                source_id=link.source_id,
                target_id=link.target_id,
                link_type=link.link_type,
                status=link.status,
                justification=link.justification,
            )
        )

    return ConversationTreeResponse(nodes=nodes, links=links)


@router.post("/conversations/{conversation_id}/links", response_model=TreeLink)
async def create_resonance_link(
    conversation_id: str,
    body: CommitLinkRequest,
    conversations: ConversationUseCases = Depends(get_conversation_use_cases),
):
    link = await conversations.create_link(
        source_id=body.source_id,
        target_id=body.target_id,
        link_type=body.link_type,
        status=body.status,
        justification=body.justification or "",
    )
    return TreeLink(
        id=link.id,
        source_id=link.source_id,
        target_id=link.target_id,
        link_type=link.link_type,
        status=link.status,
        justification=link.justification,
    )


@router.post("/conversations/{conversation_id}/links/{link_id}/confirm")
async def confirm_resonance_link(
    conversation_id: str,
    link_id: str,
    conversations: ConversationUseCases = Depends(get_conversation_use_cases),
):
    await conversations.confirm_link(link_id)
    return {"status": "success"}


@router.delete("/conversations/{conversation_id}/links/{link_id}")
async def delete_resonance_link(
    conversation_id: str,
    link_id: str,
    conversations: ConversationUseCases = Depends(get_conversation_use_cases),
):
    await conversations.delete_link(link_id)
    return {"status": "success"}


@router.get("/conversations/{conversation_id}/export")
async def export_conversation(
    conversation_id: str,
    conversations: ConversationUseCases = Depends(get_conversation_use_cases),
):
    """Export the full conversation as a Markdown document for LLM consumption.

    Includes tree structure, branches, cross-links, notes, memory nodes,
    and metadata — all with machine-parseable ID references.
    """
    from fastapi.responses import PlainTextResponse

    try:
        markdown, filename = await conversations.export(conversation_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc

    return PlainTextResponse(
        content=markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/conversations/{conversation_id}/messages/{message_id}/spectral-suggestions",
    response_model=list[SpectralSuggestion],
)
async def get_spectral_suggestions(
    conversation_id: str,
    message_id: int,
    threshold: float = 0.70,
    conversations: ConversationUseCases = Depends(get_conversation_use_cases),
):
    raw_suggestions = await conversations.spectral_suggestions(conversation_id, message_id, threshold)

    suggestions = []
    for s in raw_suggestions:
        suggestions.append(
            SpectralSuggestion(
                message_id=s["message_id"],
                speaker=s["speaker"],
                content=s["content"],
                similarity=s["similarity"],
                timestamp=s["timestamp"],
            )
        )
    return suggestions
