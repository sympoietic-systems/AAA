import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from backend.api.schemas import (
    ConversationInfo,
    ConversationListResponse,
    ConversationUpdateRequest,
    CommitBranchRequest,
    ConversationTreeResponse,
    TreeNode,
    TreeLink,
    ChatResponse,
    CommitLinkRequest,
    SpectralSuggestion,
)
from backend.services.conversation import ConversationService
from backend.services.title import TitleService
from backend.utils.token_counter import estimate_tokens
from backend.metabolisation.consolidation import generate_human_summary_text

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    request: Request,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
):
    state = request.app.state
    conv_repo = getattr(state, "conversation_repo", None)
    checkpoint_repo = getattr(state, "checkpoint_repo", None)
    if not conv_repo:
        return ConversationListResponse(conversations=[], total_count=0, has_more=False)
    
    if limit is not None and offset is None:
        offset = 0

    convos = conv_repo.list_all(tag=tag, search=search, limit=limit, offset=offset)
    total_count = conv_repo.count_all(tag=tag, search=search)

    res_convos = []
    for c in convos:
        info = ConversationService.build_conversation_info(conv_repo, checkpoint_repo, c)
        res_convos.append(ConversationInfo(**info))

    has_more = False
    if limit is not None and offset is not None:
        has_more = (offset + limit) < total_count

    return ConversationListResponse(
        conversations=res_convos,
        total_count=total_count,
        has_more=has_more
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationInfo)
async def get_conversation(conversation_id: str, request: Request):
    state = request.app.state
    conv_repo = getattr(state, "conversation_repo", None)
    checkpoint_repo = getattr(state, "checkpoint_repo", None)
    if not conv_repo:
        raise HTTPException(status_code=404, detail="Conversations not available")
    conv = conv_repo.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    info = ConversationService.build_conversation_info(conv_repo, checkpoint_repo, conv)
    return ConversationInfo(**info)


@router.patch("/conversations/{conversation_id}", response_model=ConversationInfo)
async def update_conversation(
    conversation_id: str, body: ConversationUpdateRequest, request: Request
):
    state = request.app.state
    conv_repo = getattr(state, "conversation_repo", None)
    checkpoint_repo = getattr(state, "checkpoint_repo", None)
    if not conv_repo:
        raise HTTPException(status_code=404, detail="Conversations not available")
    conv = conv_repo.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv_repo.update_title(conversation_id, body.title)
    conv = conv_repo.get(conversation_id)
    info = ConversationService.build_conversation_info(conv_repo, checkpoint_repo, conv)
    return ConversationInfo(**info)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, request: Request):
    import os
    if not os.environ.get("AAA_AGENT_FLUX", "false").lower() in ("true", "1", "yes"):
        raise HTTPException(status_code=403, detail="Conversation deletion is disabled (AAA_AGENT_FLUX is false)")

    state = request.app.state
    conv_repo = getattr(state, "conversation_repo", None)
    if not conv_repo:
        raise HTTPException(status_code=404, detail="Conversations not available")
    conv = conv_repo.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv_repo.delete(conversation_id)
    return {"status": "deleted", "id": conversation_id}


@router.delete("/conversations/{conversation_id}/messages/{message_id}")
async def delete_message(conversation_id: str, message_id: int, request: Request):
    import os
    if not os.environ.get("AAA_AGENT_FLUX", "false").lower() in ("true", "1", "yes"):
        raise HTTPException(status_code=403, detail="Message deletion is disabled (AAA_AGENT_FLUX is false)")

    state = request.app.state
    msg_repo = state.message_repo
    conv_repo = getattr(state, "conversation_repo", None)

    if conv_repo:
        conv = conv_repo.get(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

    msg = msg_repo.get_by_id(message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg.conversation_id != conversation_id:
        raise HTTPException(status_code=404, detail="Message not found in this conversation")

    msg_repo.delete_message(message_id)
    conv_repo.touch(conversation_id)
    return {"status": "deleted", "id": message_id}


@router.post("/conversations/{conversation_id}/generate-human-summary", response_model=ConversationInfo)
async def generate_human_summary(conversation_id: str, request: Request):
    state = request.app.state
    conv_repo = getattr(state, "conversation_repo", None)
    checkpoint_repo = getattr(state, "checkpoint_repo", None)
    if not conv_repo:
        raise HTTPException(status_code=404, detail="Conversations not available")
    conv = conv_repo.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    background_engine = getattr(state, "background_engine", None)
    if not background_engine:
        raise HTTPException(status_code=503, detail="Background engine not available")

    msg_repo = state.message_repo
    # Get all messages on the main ancestor path (full conversation context)
    last_msgs = msg_repo.get_recent(limit=1, conversation_id=conversation_id)
    if not last_msgs:
        raise HTTPException(status_code=404, detail="No messages in conversation")

    leaf_message_id = last_msgs[0].id
    ancestor_msgs = msg_repo.get_ancestor_path(leaf_message_id)
    ancestor_ids = [m.id for m in ancestor_msgs if m.id is not None]

    # Generate human summary using shared function
    human_summary = await generate_human_summary_text(background_engine, ancestor_msgs)

    if not human_summary:
        raise HTTPException(status_code=500, detail="Failed to generate human summary")

    # Update or create checkpoint with the new human summary
    if checkpoint_repo:
        checkpoint = checkpoint_repo.get_latest_checkpoint_for_path(conversation_id, ancestor_ids)
        if checkpoint and checkpoint.get("id"):
            checkpoint_repo.update_human_summary(checkpoint["id"], human_summary)
        else:
            total_count = len(ancestor_msgs)
            checkpoint_repo.save(
                conversation_id, total_count, "",
                human_summary=human_summary, message_id=leaf_message_id,
            )

    info = ConversationService.build_conversation_info(conv_repo, checkpoint_repo, conv)
    return ConversationInfo(**info)


@router.post("/conversations/{conversation_id}/generate-title", response_model=ConversationInfo)
async def generate_conversation_title(conversation_id: str, request: Request):
    state = request.app.state
    conv_repo = getattr(state, "conversation_repo", None)
    checkpoint_repo = getattr(state, "checkpoint_repo", None)
    if not conv_repo:
        raise HTTPException(status_code=404, detail="Conversations not available")
    conv = conv_repo.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    background_engine = getattr(state, "background_engine", None)
    if not background_engine:
        raise HTTPException(status_code=503, detail="Background engine not available")

    title = await TitleService.generate_from_conversation(
        background_engine, request.app.state.message_repo, conversation_id
    )
    conv_repo.update_title(conversation_id, title)
    conv = conv_repo.get(conversation_id)
    info = ConversationService.build_conversation_info(conv_repo, checkpoint_repo, conv)
    return ConversationInfo(**info)


@router.post("/conversations/{conversation_id}/commit-branch", response_model=ChatResponse)
async def commit_branch(conversation_id: str, body: CommitBranchRequest, request: Request):
    state = request.app.state
    repo = state.message_repo
    conv_repo = getattr(state, "conversation_repo", None)
    
    if conv_repo:
        conv = conv_repo.get(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conv_repo.touch(conversation_id)

    embedding = b""
    embedding_model = "unknown"
    embedding_dim = 0
    
    embedder = getattr(state, "embedder", None)
    if embedder and embedder.service.is_loaded:
        try:
            emb = await embedder.service.encode_async(body.content)
            embedding = embedder.service.serialize(emb)
            embedding_model = embedder.service.model_name
            embedding_dim = embedder.service.dim
        except Exception:
            logger.warning("Failed to embed committed branch message")
            
    msg = repo.insert(
        speaker=body.speaker,
        content=body.content,
        embedding=embedding,
        embedding_model=embedding_model,
        embedding_dim=embedding_dim,
        agent_id=getattr(state, "agent_name", "symbia"),
        conversation_id=conversation_id,
        content_tokens=estimate_tokens(body.content),
        parent_message_id=body.parent_message_id,
    )
    
    return ChatResponse(
        id=msg.id,
        timestamp=msg.timestamp,
        conversation_id=conversation_id,
        speaker=msg.speaker,
        content=msg.content,
        content_tokens=msg.content_tokens,
        embedding_generated=bool(embedding),
        parent_message_id=msg.parent_message_id,
    )


@router.get("/conversations/{conversation_id}/tree", response_model=ConversationTreeResponse)
async def get_conversation_tree(conversation_id: str, request: Request):
    state = request.app.state
    repo = state.message_repo
    conv_repo = getattr(state, "conversation_repo", None)
    
    if conv_repo:
        conv = conv_repo.get(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

    raw_msgs = repo.get_messages_by_conversation(conversation_id)
    nodes = []
    for m in raw_msgs:
        trimmed_content = m.content[:120] + "..." if len(m.content) > 120 else m.content
        nodes.append(TreeNode(
            id=m.id,
            speaker=m.speaker,
            content=trimmed_content,
            parent_message_id=m.parent_message_id,
            timestamp=m.timestamp,
        ))
        
    raw_links = repo.get_message_links(conversation_id)
    links = []
    for l in raw_links:
        links.append(TreeLink(
            id=l.id,
            source_id=l.source_id,
            target_id=l.target_id,
            link_type=l.link_type,
            status=l.status,
            justification=l.justification,
        ))
        
    return ConversationTreeResponse(nodes=nodes, links=links)


@router.post("/conversations/{conversation_id}/links", response_model=TreeLink)
async def create_resonance_link(conversation_id: str, body: CommitLinkRequest, request: Request):
    state = request.app.state
    repo = state.message_repo
    
    link = repo.add_message_link(
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
async def confirm_resonance_link(conversation_id: str, link_id: str, request: Request):
    state = request.app.state
    repo = state.message_repo
    repo.confirm_message_link(link_id)
    return {"status": "success"}


@router.delete("/conversations/{conversation_id}/links/{link_id}")
async def delete_resonance_link(conversation_id: str, link_id: str, request: Request):
    state = request.app.state
    repo = state.message_repo
    repo.delete_message_link(link_id)
    return {"status": "success"}


@router.get("/conversations/{conversation_id}/messages/{message_id}/spectral-suggestions", response_model=list[SpectralSuggestion])
async def get_spectral_suggestions(conversation_id: str, message_id: int, request: Request, threshold: float = 0.70):
    state = request.app.state
    repo = state.message_repo
    
    # Get ancestor path for this message
    path_msgs = repo.get_ancestor_path(message_id)
    ancestor_ids = [m.id for m in path_msgs]
    
    raw_suggestions = repo.get_parallel_messages_by_similarity(
        conversation_id=conversation_id,
        message_id=message_id,
        ancestor_ids=ancestor_ids,
        threshold=threshold,
        limit=5
    )
    
    suggestions = []
    for s in raw_suggestions:
        suggestions.append(SpectralSuggestion(
            message_id=s["message_id"],
            speaker=s["speaker"],
            content=s["content"],
            similarity=s["similarity"],
            timestamp=s["timestamp"],
        ))
    return suggestions
