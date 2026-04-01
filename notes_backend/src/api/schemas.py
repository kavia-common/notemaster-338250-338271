from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TagOut(BaseModel):
    """Tag representation."""

    id: UUID = Field(..., description="Tag ID (UUID).")
    name: str = Field(..., description="Tag name (unique case-insensitively).")
    created_at: datetime = Field(..., description="Creation time (UTC).")


class TagCreate(BaseModel):
    """Create a tag."""

    name: str = Field(..., min_length=1, max_length=64, description="Tag name.")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        return v.strip()


class TagUpdate(BaseModel):
    """Update a tag."""

    name: str = Field(..., min_length=1, max_length=64, description="New tag name.")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        return v.strip()


class NoteBase(BaseModel):
    """Core editable fields of a note."""

    title: str = Field("", max_length=200, description="Note title.")
    content: str = Field("", description="Note content (markdown supported).")
    is_archived: bool = Field(False, description="Whether note is archived.")


class NoteCreate(NoteBase):
    """Create a note with optional tags."""

    tag_ids: list[UUID] = Field(default_factory=list, description="Tags to attach.")
    tag_names: list[str] = Field(
        default_factory=list,
        description="Tags by name to attach (created if missing).",
    )

    @field_validator("tag_names")
    @classmethod
    def normalize_tag_names(cls, v: list[str]) -> list[str]:
        return [name.strip() for name in v if name.strip()]


class NoteUpdate(BaseModel):
    """Patch fields on a note."""

    title: str | None = Field(default=None, max_length=200, description="Note title.")
    content: str | None = Field(default=None, description="Note content.")
    is_archived: bool | None = Field(
        default=None, description="Whether note is archived."
    )
    tag_ids: list[UUID] | None = Field(
        default=None, description="Replace tags with these IDs."
    )
    tag_names: list[str] | None = Field(
        default=None,
        description="Replace tags with these names (created if missing).",
    )

    @field_validator("tag_names")
    @classmethod
    def normalize_tag_names(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        return [name.strip() for name in v if name.strip()]


class NoteOut(NoteBase):
    """Full note representation including tags."""

    id: UUID = Field(..., description="Note ID (UUID).")
    created_at: datetime = Field(..., description="Creation time (UTC).")
    updated_at: datetime = Field(..., description="Last update time (UTC).")
    tags: list[TagOut] = Field(default_factory=list, description="Attached tags.")


class NoteListResponse(BaseModel):
    """Paginated note listing response."""

    items: list[NoteOut] = Field(..., description="Notes.")
    total: int = Field(..., ge=0, description="Total notes matching the filter.")
    limit: int = Field(..., ge=1, le=200, description="Page size.")
    offset: int = Field(..., ge=0, description="Offset into result set.")


class TagListResponse(BaseModel):
    """Paginated tag listing response."""

    items: list[TagOut] = Field(..., description="Tags.")
    total: int = Field(..., ge=0, description="Total tags.")
    limit: int = Field(..., ge=1, le=200, description="Page size.")
    offset: int = Field(..., ge=0, description="Offset into result set.")
