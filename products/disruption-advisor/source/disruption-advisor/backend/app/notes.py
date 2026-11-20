"""Notes API under /api/v1/notes. Example feature: replace with the product's own routers.

Authentication is a product decision (see docs/architecture/adr/0004-authentication.md); add the dependency here.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.db import SessionDep
from app.models import Note
from app.schemas import NoteCreate, NotePage, NoteRead

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("")
def list_notes(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> NotePage:
    query = select(Note).order_by(Note.created_at.desc(), Note.id.desc()).limit(limit).offset(offset)
    items = [NoteRead.model_validate(note) for note in session.scalars(query)]
    return NotePage(items=items, limit=limit, offset=offset)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteCreate, session: SessionDep) -> NoteRead:
    note = Note(title=payload.title, body=payload.body)
    session.add(note)
    session.commit()
    session.refresh(note)
    return NoteRead.model_validate(note)


@router.get("/{note_id}")
def get_note(note_id: int, session: SessionDep) -> NoteRead:
    note = session.get(Note, note_id)
    if note is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found")
    return NoteRead.model_validate(note)
