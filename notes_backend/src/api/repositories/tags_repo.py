from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.errors import ConflictError, NotFoundError


@dataclass(frozen=True)
class TagRow:
    id: UUID
    name: str
    created_at: datetime


# PUBLIC_INTERFACE
async def create_tag(session: AsyncSession, *, name: str) -> TagRow:
    """Create a tag.

    Raises:
        ConflictError: if tag name already exists (case-insensitive).
    """
    try:
        res = await session.execute(
            text(
                """
                INSERT INTO tags (name)
                VALUES (:name)
                RETURNING id, name, created_at
                """
            ),
            {"name": name},
        )
        row = res.mappings().one()
        return TagRow(**row)
    except IntegrityError as e:
        raise ConflictError(
            code="tag_name_conflict",
            message="Tag name already exists",
            details={"name": name},
        ) from e


# PUBLIC_INTERFACE
async def update_tag(session: AsyncSession, *, tag_id: UUID, name: str) -> TagRow:
    """Rename a tag."""
    try:
        res = await session.execute(
            text(
                """
                UPDATE tags
                SET name = :name
                WHERE id = :id
                RETURNING id, name, created_at
                """
            ),
            {"id": str(tag_id), "name": name},
        )
        row = res.mappings().first()
        if not row:
            raise NotFoundError(code="tag_not_found", message="Tag not found", details={"id": str(tag_id)})
        return TagRow(**row)
    except IntegrityError as e:
        raise ConflictError(
            code="tag_name_conflict",
            message="Tag name already exists",
            details={"name": name},
        ) from e


# PUBLIC_INTERFACE
async def delete_tag(session: AsyncSession, *, tag_id: UUID) -> None:
    """Delete a tag."""
    res = await session.execute(
        text("DELETE FROM tags WHERE id = :id RETURNING id"),
        {"id": str(tag_id)},
    )
    if res.first() is None:
        raise NotFoundError(code="tag_not_found", message="Tag not found", details={"id": str(tag_id)})


# PUBLIC_INTERFACE
async def get_tag(session: AsyncSession, *, tag_id: UUID) -> TagRow:
    """Fetch a tag by id."""
    res = await session.execute(
        text("SELECT id, name, created_at FROM tags WHERE id = :id"),
        {"id": str(tag_id)},
    )
    row = res.mappings().first()
    if not row:
        raise NotFoundError(code="tag_not_found", message="Tag not found", details={"id": str(tag_id)})
    return TagRow(**row)


# PUBLIC_INTERFACE
async def list_tags(session: AsyncSession, *, q: str | None, limit: int, offset: int) -> tuple[list[TagRow], int]:
    """List tags with optional search query."""
    params: dict[str, object] = {"limit": limit, "offset": offset}
    where = "1=1"
    if q:
        params["q"] = q
        where = "lower(name) LIKE '%' || lower(:q) || '%'"

    total_res = await session.execute(
        text(f"SELECT count(*)::int AS total FROM tags WHERE {where}"),
        params,
    )
    total = int(total_res.mappings().one()["total"])

    res = await session.execute(
        text(
            f"""
            SELECT id, name, created_at
            FROM tags
            WHERE {where}
            ORDER BY lower(name) ASC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    items = [TagRow(**r) for r in res.mappings().all()]
    return items, total
