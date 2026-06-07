from fastapi import APIRouter, Request

from backend.api.schemas import ConversationTokenInfo, TokenResponse

router = APIRouter()


@router.get("/tokens", response_model=TokenResponse)
async def get_tokens(conversation_id: str = "", request: Request = None):
    state = request.app.state
    repo = state.message_repo
    conv_repo = getattr(state, "conversation_repo", None)
    system_prompt_tokens = getattr(state, "system_prompt_tokens", 0)

    totals = repo.get_token_totals(
        conversation_id=conversation_id if conversation_id else None
    )

    conversation_tokens: list[ConversationTokenInfo] = []
    for t in totals:
        conv_id = t["conversation_id"]
        title = ""
        if conv_repo:
            conv = conv_repo.get(conv_id)
            if conv:
                title = conv.title
        total = t["user_tokens"] + t["agent_tokens"] + t["thinking_tokens"]
        conversation_tokens.append(ConversationTokenInfo(
            conversation_id=conv_id,
            title=title,
            user_tokens=t["user_tokens"],
            agent_tokens=t["agent_tokens"],
            thinking_tokens=t["thinking_tokens"],
            total_tokens=total,
        ))

    grand_total = system_prompt_tokens + sum(c.total_tokens for c in conversation_tokens)

    return TokenResponse(
        conversations=conversation_tokens,
        system_prompt_tokens=system_prompt_tokens,
        grand_total_tokens=grand_total,
    )
