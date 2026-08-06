"""Pydantic v2 request/response schemas for the Medical Topics module.

Schemas never expose a domain entity directly, and never accept
server-controlled fields (`id`, `created_by`, ...) from the client — see
`docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention).
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.medical_topics.domain.enums import TopicStatus, TopicVisibility
from app.schemas.base import ORJSONModel

_SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"


class TopicResponse(ORJSONModel):
    id: UUID
    slug: str
    name: str
    status: TopicStatus
    visibility: TopicVisibility
    created_at: datetime
    updated_at: datetime
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    parent_id: UUID | None = None
    specialty_id: UUID | None = None
    is_featured: bool = False
    trending_score: float = 0.0
    popularity_score: float = 0.0
    created_by: UUID | None = None


class TopicSearchResponse(ORJSONModel):
    items: list[TopicResponse]
    total: int


class CreateTopicRequest(ORJSONModel):
    slug: str = Field(min_length=3, max_length=64, pattern=_SLUG_PATTERN)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    icon: str | None = Field(default=None, max_length=200)
    color: str | None = Field(default=None, pattern=_COLOR_PATTERN)
    parent_id: UUID | None = None
    specialty_id: UUID | None = None
    visibility: TopicVisibility = TopicVisibility.PUBLIC


class UpdateTopicRequest(ORJSONModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    clear_description: bool = False
    icon: str | None = Field(default=None, max_length=200)
    clear_icon: bool = False
    color: str | None = Field(default=None, pattern=_COLOR_PATTERN)
    clear_color: bool = False
    status: TopicStatus | None = None
    visibility: TopicVisibility | None = None
    parent_id: UUID | None = None
    clear_parent: bool = False
    specialty_id: UUID | None = None
    clear_specialty: bool = False


# --- Followers ---------------------------------------------------------------------


class TopicFollowerResponse(ORJSONModel):
    id: UUID
    topic_id: UUID
    user_id: UUID
    followed_at: datetime


# --- Specialties ---------------------------------------------------------------------


class TopicSpecialtyResponse(ORJSONModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    description: str | None = None


class CreateTopicSpecialtyRequest(ORJSONModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=3, max_length=64, pattern=_SLUG_PATTERN)
    description: str | None = Field(default=None, max_length=2000)


# --- Aliases / synonyms -----------------------------------------------------------------


class TopicAliasResponse(ORJSONModel):
    id: UUID
    topic_id: UUID
    alias: str


class CreateTopicAliasRequest(ORJSONModel):
    alias: str = Field(min_length=1, max_length=200)


# --- Relations ---------------------------------------------------------------------------


class TopicRelationResponse(ORJSONModel):
    id: UUID
    topic_id: UUID
    related_topic_id: UUID
    relation_type: str


class CreateTopicRelationRequest(ORJSONModel):
    related_topic_id: UUID
    relation_type: str = "related"


# --- Featured toggle ---------------------------------------------------------------------


class SetTopicFeaturedRequest(ORJSONModel):
    featured: bool
