import asyncio

from fastapi import APIRouter, Request

from backend.api.schemas import ConversationTokenInfo, TokenResponse

router = APIRouter()


def _conversation_token_rows(repo, conv_repo, conversation_id: str) -> list[ConversationTokenInfo]:
    totals = repo.get_token_totals(conversation_id=conversation_id or None)
    rows: list[ConversationTokenInfo] = []
    for total_row in totals:
        conv_id = total_row["conversation_id"]
        conversation = conv_repo.get(conv_id) if conv_repo else None
        total = total_row["user_tokens"] + total_row["agent_tokens"] + total_row["thinking_tokens"]
        rows.append(
            ConversationTokenInfo(
                conversation_id=conv_id,
                title=conversation.title if conversation else "",
                user_tokens=total_row["user_tokens"],
                agent_tokens=total_row["agent_tokens"],
                thinking_tokens=total_row["thinking_tokens"],
                total_tokens=total,
            )
        )
    return rows


@router.get("/tokens", response_model=TokenResponse)
async def get_tokens(conversation_id: str = "", request: Request = None):
    state = request.app.state
    repo = state.message_repo
    conv_repo = getattr(state, "conversation_repo", None)
    system_prompt_tokens = getattr(state, "system_prompt_tokens", 0)

    conversation_tokens = await asyncio.to_thread(_conversation_token_rows, repo, conv_repo, conversation_id)

    grand_total = system_prompt_tokens + sum(c.total_tokens for c in conversation_tokens)

    return TokenResponse(
        conversations=conversation_tokens,
        system_prompt_tokens=system_prompt_tokens,
        grand_total_tokens=grand_total,
    )
