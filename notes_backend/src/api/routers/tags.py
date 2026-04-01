from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.db import get_db_session
from src.api.core.errors import AppError, ErrorResponse, http_error_from_app_error
from src.api.flows.tags_flow import (
    create_tag_flow,
    delete_tag_flow,
    get_tag_flow,
    list_tags_flow,
    update_tag_flow,
)
from src.api.schemas import TagCreate, TagListResponse, TagOut, TagUpdate

router = APIRouter(prefix="/tags", tags=["tags"])


def _to_tag_out(t) -> TagOut:
    return TagOut(id=t.id, name=t.name, created_at=t.created_at)


@router.get(
    "",
    response_model=TagListResponse,
    responses={400: {"model": ErrorResponse}},
    summary="List tags (with search)",
    operation_id="list_tags",
)
async def list_tags(
    q: str | None = Query(default=None, description="Search query (matches tag name)."),
    limit: int = Query(default=100, ge=1, le=200, description="Page size."),
    offset: int = Query(default=0, ge=0, description="Offset into result set."),
    session: AsyncSession = Depends(get_db_session),
):
    """List tags."""
    try:
        items, total = await list_tags_flow(session, q=q, limit=limit, offset=offset)
        return TagListResponse(items=[_to_tag_out(t) for t in items], total=total, limit=limit, offset=offset)
    except AppError as e:
        raise http_error_from_app_error(e)


@router.post(
    "",
    response_model=TagOut,
    status_code=201,
    responses={409: {"model": ErrorResponse}},
    summary="Create a tag",
    operation_id="create_tag",
)
async def create_tag(payload: TagCreate, session: AsyncSession = Depends(get_db_session)):
    """Create a tag."""
    try:
        tag = await create_tag_flow(session, name=payload.name)
        await session.commit()
        return _to_tag_out(tag)
    except AppError as e:
        await session.rollback()
        raise http_error_from_app_error(e)


@router.get(
    "/{tag_id}",
    response_model=TagOut,
    responses={404: {"model": ErrorResponse}},
    summary="Get a tag",
    operation_id="get_tag",
)
async def get_tag(tag_id: UUID, session: AsyncSession = Depends(get_db_session)):
    """Get a tag by ID."""
    try:
        tag = await get_tag_flow(session, tag_id=tag_id)
        return _to_tag_out(tag)
    except AppError as e:
        raise http_error_from_app_error(e)


@router.patch(
    "/{tag_id}",
    response_model=TagOut,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Update a tag",
    operation_id="update_tag",
)
async def update_tag(tag_id: UUID, payload: TagUpdate, session: AsyncSession = Depends(get_db_session)):
    """Rename a tag."""
    try:
        tag = await update_tag_flow(session, tag_id=tag_id, name=payload.name)
        await session.commit()
        return _to_tag_out(tag)
    except AppError as e:
        await session.rollback()
        raise http_error_from_app_error(e)


@router.delete(
    "/{tag_id}",
    status_code=204,
    responses={404: {"model": ErrorResponse}},
    summary="Delete a tag",
    operation_id="delete_tag",
)
async def delete_tag(tag_id: UUID, session: AsyncSession = Depends(get_db_session)):
    """Delete a tag."""
    try:
        await delete_tag_flow(session, tag_id=tag_id)
        await session.commit()
        return None
    except AppError as e:
        await session.rollback()
        raise http_error_from_app_error(e)
