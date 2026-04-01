import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.repositories import tags_repo

logger = logging.getLogger("tags_flow")


# PUBLIC_INTERFACE
async def create_tag_flow(session: AsyncSession, *, name: str) -> tags_repo.TagRow:
    """Create a tag."""
    logger.info("create_tag_flow start name_len=%s", len(name or ""))
    tag = await tags_repo.create_tag(session, name=name)
    logger.info("create_tag_flow end tag_id=%s", tag.id)
    return tag


# PUBLIC_INTERFACE
async def update_tag_flow(session: AsyncSession, *, tag_id: UUID, name: str) -> tags_repo.TagRow:
    """Update a tag."""
    logger.info("update_tag_flow start tag_id=%s", tag_id)
    tag = await tags_repo.update_tag(session, tag_id=tag_id, name=name)
    logger.info("update_tag_flow end tag_id=%s", tag.id)
    return tag


# PUBLIC_INTERFACE
async def delete_tag_flow(session: AsyncSession, *, tag_id: UUID) -> None:
    """Delete a tag."""
    logger.info("delete_tag_flow start tag_id=%s", tag_id)
    await tags_repo.delete_tag(session, tag_id=tag_id)
    logger.info("delete_tag_flow end tag_id=%s", tag_id)


# PUBLIC_INTERFACE
async def get_tag_flow(session: AsyncSession, *, tag_id: UUID) -> tags_repo.TagRow:
    """Get a tag."""
    logger.info("get_tag_flow start tag_id=%s", tag_id)
    tag = await tags_repo.get_tag(session, tag_id=tag_id)
    logger.info("get_tag_flow end tag_id=%s", tag.id)
    return tag


# PUBLIC_INTERFACE
async def list_tags_flow(session: AsyncSession, *, q: str | None, limit: int, offset: int) -> tuple[list[tags_repo.TagRow], int]:
    """List tags."""
    logger.info("list_tags_flow start q=%s limit=%s offset=%s", bool(q), limit, offset)
    items, total = await tags_repo.list_tags(session, q=q, limit=limit, offset=offset)
    logger.info("list_tags_flow end count=%s total=%s", len(items), total)
    return items, total
