from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.errors import ConflictError, NotFoundError


@dataclass(frozen=True)
class NoteRow:
    id: UUID
    title: str
    content: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class TagRow:
    id: UUID
    name: str
    created_at: datetime


async def _fetch_note(session: AsyncSession, note_id: UUID) -> NoteRow:
    res = await session.execute(
        text(
            """
            SELECT id, title, content, is_archived, created_at, updated_at
            FROM notes
            WHERE id = :id
            """
        ),
        {"id": str(note_id)},
    )
    row = res.mappings().first()
    if not row:
        raise NotFoundError(code="note_not_found", message="Note not found", details={"id": str(note_id)})
    return NoteRow(**row)


async def _fetch_note_tags(session: AsyncSession, note_id: UUID) -> list[TagRow]:
    res = await session.execute(
        text(
            """
            SELECT t.id, t.name, t.created_at
            FROM tags t
            INNER JOIN note_tags nt ON nt.tag_id = t.id
            WHERE nt.note_id = :note_id
            ORDER BY lower(t.name) ASC
            """
        ),
        {"note_id": str(note_id)},
    )
    return [TagRow(**r) for r in res.mappings().all()]


# PUBLIC_INTERFACE
async def create_note(session: AsyncSession, *, title: str, content: str, is_archived: bool) -> NoteRow:
    """Insert a note and return its row."""
    res = await session.execute(
        text(
            """
            INSERT INTO notes (title, content, is_archived)
            VALUES (:title, :content, :is_archived)
            RETURNING id, title, content, is_archived, created_at, updated_at
            """
        ),
        {"title": title, "content": content, "is_archived": is_archived},
    )
    row = res.mappings().one()
    return NoteRow(**row)


# PUBLIC_INTERFACE
async def update_note(session: AsyncSession, *, note_id: UUID, title: str | None, content: str | None, is_archived: bool | None) -> NoteRow:
    """Patch a note and return updated row."""
    # COALESCE keeps existing if parameter is null.
    res = await session.execute(
        text(
            """
            UPDATE notes
            SET
              title = COALESCE(:title, title),
              content = COALESCE(:content, content),
              is_archived = COALESCE(:is_archived, is_archived),
              updated_at = now()
            WHERE id = :id
            RETURNING id, title, content, is_archived, created_at, updated_at
            """
        ),
        {"id": str(note_id), "title": title, "content": content, "is_archived": is_archived},
    )
    row = res.mappings().first()
    if not row:
        raise NotFoundError(code="note_not_found", message="Note not found", details={"id": str(note_id)})
    return NoteRow(**row)


# PUBLIC_INTERFACE
async def delete_note(session: AsyncSession, *, note_id: UUID) -> None:
    """Delete a note."""
    res = await session.execute(
        text("DELETE FROM notes WHERE id = :id RETURNING id"),
        {"id": str(note_id)},
    )
    if res.first() is None:
        raise NotFoundError(code="note_not_found", message="Note not found", details={"id": str(note_id)})


# PUBLIC_INTERFACE
async def get_note_with_tags(session: AsyncSession, *, note_id: UUID) -> tuple[NoteRow, list[TagRow]]:
    """Fetch note and its tags."""
    note = await _fetch_note(session, note_id)
    tags = await _fetch_note_tags(session, note_id)
    return note, tags


# PUBLIC_INTERFACE
async def list_notes(
    session: AsyncSession,
    *,
    q: str | None,
    tag_id: UUID | None,
    include_archived: bool,
    limit: int,
    offset: int,
) -> tuple[list[NoteRow], dict[UUID, list[TagRow]], int]:
    """List notes with optional search and tag filters.

    Returns:
        (notes, tags_by_note_id, total)
    """
    where = ["1=1"]
    params: dict[str, object] = {"limit": limit, "offset": offset}

    if not include_archived:
        where.append("n.is_archived = false")

    if q:
        params["q"] = q
        where.append("(n.title ILIKE '%' || :q || '%' OR n.content ILIKE '%' || :q || '%')")

    if tag_id:
        params["tag_id"] = str(tag_id)
        where.append(
            """
            EXISTS (
              SELECT 1 FROM note_tags nt
              WHERE nt.note_id = n.id AND nt.tag_id = :tag_id
            )
            """
        )

    where_sql = " AND ".join(where)

    total_res = await session.execute(
        text(f"SELECT count(*)::int AS total FROM notes n WHERE {where_sql}"),
        params,
    )
    total = int(total_res.mappings().one()["total"])

    notes_res = await session.execute(
        text(
            f"""
            SELECT n.id, n.title, n.content, n.is_archived, n.created_at, n.updated_at
            FROM notes n
            WHERE {where_sql}
            ORDER BY n.updated_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    notes = [NoteRow(**r) for r in notes_res.mappings().all()]
    if not notes:
        return [], {}, total

    note_ids = [str(n.id) for n in notes]
    tags_res = await session.execute(
        text(
            """
            SELECT nt.note_id, t.id AS tag_id, t.name, t.created_at
            FROM note_tags nt
            INNER JOIN tags t ON t.id = nt.tag_id
            WHERE nt.note_id = ANY(:note_ids)
            ORDER BY lower(t.name) ASC
            """
        ),
        {"note_ids": note_ids},
    )

    tags_by_note: dict[UUID, list[TagRow]] = {}
    for r in tags_res.mappings().all():
        nid = UUID(str(r["note_id"]))
        tags_by_note.setdefault(nid, []).append(
            TagRow(id=UUID(str(r["tag_id"])), name=r["name"], created_at=r["created_at"])
        )
    return notes, tags_by_note, total


# PUBLIC_INTERFACE
async def ensure_tags_by_name(session: AsyncSession, *, names: list[str]) -> list[TagRow]:
    """Ensure tags with given names exist, returning their rows."""
    if not names:
        return []

    # Insert one by one to keep logic simple and leverage unique index on lower(name).
    tags: list[TagRow] = []
    for name in names:
        res = await session.execute(
            text(
                """
                INSERT INTO tags (name)
                VALUES (:name)
                ON CONFLICT (lower(name)) DO UPDATE SET name = EXCLUDED.name
                RETURNING id, name, created_at
                """
            ),
            {"name": name},
        )
        row = res.mappings().one()
        tags.append(TagRow(**row))
    return tags


# PUBLIC_INTERFACE
async def attach_tags(session: AsyncSession, *, note_id: UUID, tag_ids: list[UUID]) -> None:
    """Attach tags to a note (idempotent)."""
    for tag_id in tag_ids:
        try:
            await session.execute(
                text(
                    """
                    INSERT INTO note_tags (note_id, tag_id)
                    VALUES (:note_id, :tag_id)
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"note_id": str(note_id), "tag_id": str(tag_id)},
            )
        except IntegrityError as e:
            # FK failure (note/tag missing)
            raise ConflictError(
                code="tag_attach_conflict",
                message="Unable to attach tag to note",
                details={"note_id": str(note_id), "tag_id": str(tag_id)},
            ) from e


# PUBLIC_INTERFACE
async def replace_note_tags(session: AsyncSession, *, note_id: UUID, tag_ids: list[UUID]) -> None:
    """Replace all tags for a note with the given set."""
    await session.execute(
        text("DELETE FROM note_tags WHERE note_id = :note_id"),
        {"note_id": str(note_id)},
    )
    await attach_tags(session, note_id=note_id, tag_ids=tag_ids)
