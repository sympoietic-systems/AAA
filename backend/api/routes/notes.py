from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request

from backend.api.deps import get_app_state, get_note_repo
from backend.api.schemas import NoteCreateRequest, NoteResponse, NoteUpdateRequest
from backend.services.note import NoteService

router = APIRouter()


def _resolve_create_params(req: NoteCreateRequest, conversation_id: str | None = None):
    asset_type = req.asset_type
    asset_id = req.asset_id
    message_id = req.message_id

    if conversation_id:
        asset_type = "conversation_message"
        asset_id = str(req.message_id or req.asset_id)

    if not asset_id:
        raise HTTPException(status_code=400, detail="asset_id is required")

    return asset_type, asset_id, message_id


def _create_note(note_repo, asset_type: str, asset_id: str, conversation_id: str | None, req: NoteCreateRequest):
    return NoteService.create(
        note_repo,
        asset_type=asset_type,
        asset_id=asset_id,
        conversation_id=conversation_id,
        selected_text=req.selected_text,
        comment=req.comment,
        visibility=req.visibility,
        start_offset=req.start_offset,
    )


def _schedule_metabolism(
    background_tasks: BackgroundTasks, state, note: dict, conversation_id: str | None, message_id: int | None
):
    if (
        note.get("visibility") == "shared"
        and note.get("asset_type") == "conversation_message"
        and conversation_id
        and message_id is not None
    ):
        background_tasks.add_task(
            NoteService.metabolize_background,
            state=state,
            conversation_id=conversation_id,
            message_id=message_id,
            selected_text=note.get("selected_text", ""),
            comment=note.get("comment", ""),
            note_id=note["id"],
        )


@router.post("/notes", response_model=NoteResponse)
async def create_note(
    req: NoteCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    state=Depends(get_app_state),
    note_repo=Depends(get_note_repo),
):
    if not note_repo:
        raise HTTPException(status_code=503, detail="Note repository not configured")

    asset_type, asset_id, message_id = _resolve_create_params(req)
    note = _create_note(note_repo, asset_type, asset_id, req.conversation_id, req)
    if not note:
        raise HTTPException(status_code=500, detail="Failed to create note")

    _schedule_metabolism(background_tasks, state, note, req.conversation_id, message_id)
    return NoteResponse(**note)


@router.get("/notes", response_model=list[NoteResponse])
async def get_notes(
    asset_type: str | None = Query(None),
    asset_id: str | None = Query(None),
    conversation_id: str | None = Query(None),
    note_repo=Depends(get_note_repo),
):
    if not note_repo:
        raise HTTPException(status_code=503, detail="Note repository not configured")

    if conversation_id:
        notes = NoteService.list_by_conversation(note_repo, conversation_id)
    elif asset_type and asset_id:
        notes = NoteService.list_by_asset(note_repo, asset_type, asset_id)
    else:
        raise HTTPException(status_code=400, detail="Provide asset_type+asset_id or conversation_id")

    return [NoteResponse(**n) for n in notes]


@router.patch("/notes/{note_id}", response_model=NoteResponse)
async def update_note_route(
    note_id: str,
    req: NoteUpdateRequest,
    background_tasks: BackgroundTasks,
    state=Depends(get_app_state),
    note_repo=Depends(get_note_repo),
):
    if not note_repo:
        raise HTTPException(status_code=503, detail="Note repository not configured")

    existing = NoteService.get(note_repo, note_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")

    updated = NoteService.update(note_repo, note_id, comment=req.comment, visibility=req.visibility)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update note")

    is_shared = updated.get("visibility") == "shared"
    if is_shared and existing.get("asset_type") == "conversation_message":
        conv_id = existing.get("conversation_id", "")
        try:
            msg_id = int(existing.get("asset_id", "0"))
        except (ValueError, TypeError):
            msg_id = 0
        if conv_id and msg_id:
            _schedule_metabolism(background_tasks, state, updated, conv_id, msg_id)

    return NoteResponse(**updated)


@router.delete("/notes/{note_id}")
async def delete_note(note_id: str, note_repo=Depends(get_note_repo)):
    if not note_repo:
        raise HTTPException(status_code=503, detail="Note repository not configured")
    NoteService.delete(note_repo, note_id)
    return {"status": "success"}


@router.post("/conversations/{conversation_id}/notes", response_model=NoteResponse)
async def create_conversation_note(
    conversation_id: str,
    req: NoteCreateRequest,
    background_tasks: BackgroundTasks,
    state=Depends(get_app_state),
    note_repo=Depends(get_note_repo),
):
    if not note_repo:
        raise HTTPException(status_code=503, detail="Note repository not configured")

    asset_type, asset_id, message_id = _resolve_create_params(req, conversation_id)
    note = _create_note(note_repo, asset_type, asset_id, conversation_id, req)
    if not note:
        raise HTTPException(status_code=500, detail="Failed to create note")

    _schedule_metabolism(background_tasks, state, note, conversation_id, message_id)
    return NoteResponse(**note)


@router.get("/conversations/{conversation_id}/notes", response_model=list[NoteResponse])
async def get_conversation_notes(conversation_id: str, note_repo=Depends(get_note_repo)):
    if not note_repo:
        raise HTTPException(status_code=503, detail="Note repository not configured")
    notes = NoteService.list_by_conversation(note_repo, conversation_id)
    return [NoteResponse(**n) for n in notes]


@router.patch("/conversations/{conversation_id}/notes/{note_id}", response_model=NoteResponse)
async def update_conversation_note(
    conversation_id: str,
    note_id: str,
    req: NoteUpdateRequest,
    background_tasks: BackgroundTasks,
    state=Depends(get_app_state),
    note_repo=Depends(get_note_repo),
):
    if not note_repo:
        raise HTTPException(status_code=503, detail="Note repository not configured")

    existing = NoteService.get(note_repo, note_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")

    updated = NoteService.update(note_repo, note_id, comment=req.comment, visibility=req.visibility)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update note")

    is_shared = updated.get("visibility") == "shared"
    if is_shared:
        try:
            msg_id = int(updated.get("asset_id", "0"))
        except (ValueError, TypeError):
            msg_id = 0
        if msg_id:
            _schedule_metabolism(background_tasks, state, updated, conversation_id, msg_id)

    return NoteResponse(**updated)


@router.delete("/conversations/{conversation_id}/notes/{note_id}")
async def delete_conversation_note(conversation_id: str, note_id: str, note_repo=Depends(get_note_repo)):
    if not note_repo:
        raise HTTPException(status_code=503, detail="Note repository not configured")
    NoteService.delete(note_repo, note_id)
    return {"status": "success"}
