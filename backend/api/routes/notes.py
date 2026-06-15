from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from backend.api.deps import get_app_state, get_note_repo
from backend.services.note import NoteService

from backend.api.schemas import NoteCreateRequest, NoteResponse, NoteUpdateRequest

router = APIRouter()


@router.post("/conversations/{conversation_id}/notes", response_model=NoteResponse)
async def create_note(
    conversation_id: str,
    req: NoteCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    state=Depends(get_app_state),
    note_repo=Depends(get_note_repo),
):
    if not note_repo:
        raise HTTPException(status_code=500, detail="Note repository not configured")

    note = NoteService.create(
        note_repo, conversation_id, req.message_id,
        req.selected_text, req.comment, req.visibility, req.start_offset,
    )
    if not note:
        raise HTTPException(status_code=500, detail="Failed to create note")

    if req.visibility == "shared":
        background_tasks.add_task(
            NoteService.metabolize_background,
            state=state, conversation_id=conversation_id,
            message_id=req.message_id, selected_text=req.selected_text,
            comment=req.comment, note_id=note["id"],
        )

    return NoteResponse(**note)


@router.get("/conversations/{conversation_id}/notes", response_model=list[NoteResponse])
async def get_notes(conversation_id: str, note_repo=Depends(get_note_repo)):
    if not note_repo:
        raise HTTPException(status_code=500, detail="Note repository not configured")
    notes = NoteService.list_by_conversation(note_repo, conversation_id)
    return [NoteResponse(**n) for n in notes]


@router.patch("/conversations/{conversation_id}/notes/{note_id}", response_model=NoteResponse)
async def update_note_route(
    conversation_id: str,
    note_id: str,
    req: NoteUpdateRequest,
    background_tasks: BackgroundTasks,
    state=Depends(get_app_state),
    note_repo=Depends(get_note_repo),
):
    if not note_repo:
        raise HTTPException(status_code=500, detail="Note repository not configured")

    existing = NoteService.get(note_repo, note_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")

    updated = NoteService.update(note_repo, note_id, comment=req.comment, visibility=req.visibility)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update note")

    was_shared = existing.get("visibility") == "shared"
    is_shared = updated.get("visibility") == "shared"
    if is_shared and (not was_shared or req.comment is not None):
        background_tasks.add_task(
            NoteService.metabolize_background,
            state=state, conversation_id=conversation_id,
            message_id=updated["message_id"], selected_text=updated["selected_text"],
            comment=updated["comment"], note_id=note_id,
        )

    return NoteResponse(**updated)


@router.delete("/conversations/{conversation_id}/notes/{note_id}")
async def delete_note(conversation_id: str, note_id: str, note_repo=Depends(get_note_repo)):
    if not note_repo:
        raise HTTPException(status_code=500, detail="Note repository not configured")
    NoteService.delete(note_repo, note_id)
    return {"status": "success"}
