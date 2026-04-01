import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.repositories import notes_repo

logger = logging.getLogger("notes_flow")


# PUBLIC_INTERFACE
async def create_note_flow(
    session: AsyncSession,
    *,
    title: str,
    content: str,
    is_archived: bool,
    tag_ids: list[UUID],
    tag_names: list[str],
) -> tuple[notes_repo.NoteRow, list[notes_repo.TagRow]]:
    """Create a note and attach tags (creating missing tags by name).

    Contract:
    - Inputs: note fields + tag identifiers and/or tag names
    - Outputs: (note_row, tag_rows_attached)
    - Errors: AppError subclasses for expected domain/db issues
    """
    logger.info("create_note_flow start title_len=%s tag_ids=%s tag_names=%s", len(title or ""), len(tag_ids), len(tag_names))
    note = await notes_repo.create_note(session, title=title, content=content, is_archived=is_archived)

    ensured = await notes_repo.ensure_tags_by_name(session, names=tag_names)
    merged_ids = list(tag_ids) + [t.id for t in ensured]
    if merged_ids:
        await notes_repo.attach_tags(session, note_id=note.id, tag_ids=merged_ids)

    note, tags = await notes_repo.get_note_with_tags(session, note_id=note.id)
    logger.info("create_note_flow end note_id=%s tags=%s", note.id, len(tags))
    return note, tags


# PUBLIC_INTERFACE
async def update_note_flow(
    session: AsyncSession,
    *,
    note_id: UUID,
    title: str | None,
    content: str | None,
    is_archived: bool | None,
    tag_ids: list[UUID] | None,
    tag_names: list[str] | None,
) -> tuple[notes_repo.NoteRow, list[notes_repo.TagRow]]:
    """Update a note and optionally replace tags."""
    logger.info("update_note_flow start note_id=%s", note_id)

    note = await notes_repo.update_note(
        session, note_id=note_id, title=title, content=content, is_archived=is_archived
    )

    if tag_ids is not None or tag_names is not None:
        ensured = await notes_repo.ensure_tags_by_name(session, names=tag_names or [])
        merged_ids = list(tag_ids or []) + [t.id for t in ensured]
        await notes_repo.replace_note_tags(session, note_id=note.id, tag_ids=merged_ids)

    note, tags = await notes_repo.get_note_with_tags(session, note_id=note.id)
    logger.info("update_note_flow end note_id=%s tags=%s", note.id, len(tags))
    return note, tags


# PUBLIC_INTERFACE
async def delete_note_flow(session: AsyncSession, *, note_id: UUID) -> None:
    """Delete a note."""
    logger.info("delete_note_flow start note_id=%s", note_id)
    await notes_repo.delete_note(session, note_id=note_id)
    logger.info("delete_note_flow end note_id=%s", note_id)


# PUBLIC_INTERFACE
async def get_note_flow(session: AsyncSession, *, note_id: UUID) -> tuple[notes_repo.NoteRow, list[notes_repo.TagRow]]:
    """Get a single note with tags."""
    logger.info("get_note_flow start note_id=%s", note_id)
    note, tags = await notes_repo.get_note_with_tags(session, note_id=note_id)
    logger.info("get_note_flow end note_id=%s", note_id)
    return note, tags


# PUBLIC_INTERFACE
async def list_notes_flow(
    session: AsyncSession,
    *,
    q: str | None,
    tag_id: UUID | None,
    include_archived: bool,
    limit: int,
    offset: int,
) -> tuple[list[notes_repo.NoteRow], dict[UUID, list[notes_repo.TagRow]], int]:
    """List notes with filters."""
    logger.info("list_notes_flow start q=%s tag_id=%s include_archived=%s limit=%s offset=%s", bool(q), tag_id, include_archived, limit, offset)
    notes, tags_by_note, total = await notes_repo.list_notes(
        session,
        q=q,
        tag_id=tag_id,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )
    logger.info("list_notes_flow end count=%s total=%s", len(notes), total)
    return notes, tags_by_note, total
