import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from .schemas import NoteCreateRequest, NoteResponse, NoteUpdateRequest

logger = logging.getLogger(__name__)

router = APIRouter()


async def metabolize_note_background(
    state,
    conversation_id: str,
    message_id: int,
    selected_text: str,
    comment: str,
    note_id: str,
):
    try:
        state.message_repo.increment_message_note_count(message_id, 1)
    except Exception as e:
        logger.error(f"Failed to increment message note count: {e}")

    belief_metabolism = getattr(state, "belief_metabolism", None)
    if belief_metabolism:
        await belief_metabolism.metabolize_note(
            conversation_id=conversation_id,
            message_id=message_id,
            selected_text=selected_text,
            comment=comment,
            note_id=note_id,
        )


@router.post("/conversations/{conversation_id}/notes", response_model=NoteResponse)
async def create_note(
    conversation_id: str,
    req: NoteCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    state = request.app.state
    note_repo = getattr(state, "note_repo", None)
    if not note_repo:
        raise HTTPException(status_code=500, detail="Note repository not configured")

    note_id = str(uuid.uuid4())
    note = note_repo.create_note(
        id=note_id,
        conversation_id=conversation_id,
        message_id=req.message_id,
        selected_text=req.selected_text,
        comment=req.comment,
        visibility=req.visibility,
        start_offset=req.start_offset,
    )
    if not note:
        raise HTTPException(status_code=500, detail="Failed to create note")

    if req.visibility == "shared":
        background_tasks.add_task(
            metabolize_note_background,
            state=state,
            conversation_id=conversation_id,
            message_id=req.message_id,
            selected_text=req.selected_text,
            comment=req.comment,
            note_id=note_id,
        )

    return NoteResponse(**note)


@router.get("/conversations/{conversation_id}/notes", response_model=list[NoteResponse])
async def get_notes(conversation_id: str, request: Request):
    state = request.app.state
    note_repo = getattr(state, "note_repo", None)
    if not note_repo:
        raise HTTPException(status_code=500, detail="Note repository not configured")

    notes = note_repo.get_notes_by_conversation(conversation_id)
    return [NoteResponse(**n) for n in notes]


@router.patch("/conversations/{conversation_id}/notes/{note_id}", response_model=NoteResponse)
async def update_note_route(
    conversation_id: str,
    note_id: str,
    req: NoteUpdateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    state = request.app.state
    note_repo = getattr(state, "note_repo", None)
    if not note_repo:
        raise HTTPException(status_code=500, detail="Note repository not configured")

    existing_note = note_repo.get_note(note_id)
    if not existing_note:
        raise HTTPException(status_code=404, detail="Note not found")

    updated = note_repo.update_note(note_id, comment=req.comment, visibility=req.visibility)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update note")

    was_shared = existing_note.get("visibility") == "shared"
    is_shared = updated.get("visibility") == "shared"

    if is_shared and (not was_shared or req.comment is not None):
        background_tasks.add_task(
            metabolize_note_background,
            state=state,
            conversation_id=conversation_id,
            message_id=updated["message_id"],
            selected_text=updated["selected_text"],
            comment=updated["comment"],
            note_id=note_id,
        )

    return NoteResponse(**updated)


@router.delete("/conversations/{conversation_id}/notes/{note_id}")
async def delete_note(conversation_id: str, note_id: str, request: Request):
    state = request.app.state
    note_repo = getattr(state, "note_repo", None)
    if not note_repo:
        raise HTTPException(status_code=500, detail="Note repository not configured")

    note_repo.delete_note(note_id)
    return {"status": "success"}
