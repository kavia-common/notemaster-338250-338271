from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.db import get_db_session
from src.api.core.errors import AppError, ErrorResponse, http_error_from_app_error
from src.api.flows.notes_flow import (
    create_note_flow,
    delete_note_flow,
    get_note_flow,
    list_notes_flow,
    update_note_flow,
)
from src.api.schemas import NoteCreate, NoteListResponse, NoteOut, NoteUpdate, TagOut

router = APIRouter(prefix="/notes", tags=["notes"])


def _to_tag_out(t) -> TagOut:
    return TagOut(id=t.id, name=t.name, created_at=t.created_at)


def _to_note_out(n, tags) -> NoteOut:
    return NoteOut(
        id=n.id,
        title=n.title,
        content=n.content,
        is_archived=n.is_archived,
        created_at=n.created_at,
        updated_at=n.updated_at,
        tags=[_to_tag_out(t) for t in tags],
    )


@router.get(
    "",
    response_model=NoteListResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="List notes (with search and tag filters)",
    description="Returns notes ordered by most recently updated. Supports search query and tag filter.",
    operation_id="list_notes",
)
async def list_notes(
    q: str | None = Query(default=None, description="Search query (matches title/content)."),
    tag_id: UUID | None = Query(default=None, description="Filter by tag id."),
    include_archived: bool = Query(default=False, description="Include archived notes."),
    limit: int = Query(default=50, ge=1, le=200, description="Page size."),
    offset: int = Query(default=0, ge=0, description="Offset into result set."),
    session: AsyncSession = Depends(get_db_session),
):
    """List notes with optional search and tag filter."""
    try:
        notes, tags_by_note, total = await list_notes_flow(
            session,
            q=q,
            tag_id=tag_id,
            include_archived=include_archived,
            limit=limit,
            offset=offset,
        )
        return NoteListResponse(
            items=[_to_note_out(n, tags_by_note.get(n.id, [])) for n in notes],
            total=total,
            limit=limit,
            offset=offset,
        )
    except AppError as e:
        raise http_error_from_app_error(e)


@router.post(
    "",
    response_model=NoteOut,
    status_code=201,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Create a note",
    description="Creates a note and optionally attaches tags by id or name (creating missing tags by name).",
    operation_id="create_note",
)
async def create_note(payload: NoteCreate, session: AsyncSession = Depends(get_db_session)):
    """Create a note."""
    try:
        note, tags = await create_note_flow(
            session,
            title=payload.title,
            content=payload.content,
            is_archived=payload.is_archived,
            tag_ids=payload.tag_ids,
            tag_names=payload.tag_names,
        )
        await session.commit()
        return _to_note_out(note, tags)
    except AppError as e:
        await session.rollback()
        raise http_error_from_app_error(e)


@router.get(
    "/{note_id}",
    response_model=NoteOut,
    responses={404: {"model": ErrorResponse}},
    summary="Get a note",
    operation_id="get_note",
)
async def get_note(note_id: UUID, session: AsyncSession = Depends(get_db_session)):
    """Get a note by ID."""
    try:
        note, tags = await get_note_flow(session, note_id=note_id)
        return _to_note_out(note, tags)
    except AppError as e:
        raise http_error_from_app_error(e)


@router.patch(
    "/{note_id}",
    response_model=NoteOut,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Update a note",
    description="Partially updates a note. If tag_ids or tag_names is provided, tags are replaced.",
    operation_id="update_note",
)
async def update_note(note_id: UUID, payload: NoteUpdate, session: AsyncSession = Depends(get_db_session)):
    """Update a note."""
    try:
        note, tags = await update_note_flow(
            session,
            note_id=note_id,
            title=payload.title,
            content=payload.content,
            is_archived=payload.is_archived,
            tag_ids=payload.tag_ids,
            tag_names=payload.tag_names,
        )
        await session.commit()
        return _to_note_out(note, tags)
    except AppError as e:
        await session.rollback()
        raise http_error_from_app_error(e)


@router.delete(
    "/{note_id}",
    status_code=204,
    responses={404: {"model": ErrorResponse}},
    summary="Delete a note",
    operation_id="delete_note",
)
async def delete_note(note_id: UUID, session: AsyncSession = Depends(get_db_session)):
    """Delete a note."""
    try:
        await delete_note_flow(session, note_id=note_id)
        await session.commit()
        return None
    except AppError as e:
        await session.rollback()
        raise http_error_from_app_error(e)
