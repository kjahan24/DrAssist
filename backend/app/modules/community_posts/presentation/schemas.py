"""Pydantic v2 request/response schemas for the Community Posts module.

Schemas never expose a domain entity directly, and never accept
server-controlled fields (`id`, `author_id`, ...) from the client — see
`docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention).
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.community_posts.domain.enums import PostStatus, PostType, PostVisibility
from app.schemas.base import ORJSONModel

_SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class PostResponse(ORJSONModel):
    id: UUID
    community_id: UUID
    organization_id: UUID
    author_id: UUID
    slug: str
    title: str
    body: str
    excerpt: str
    post_type: PostType
    status: PostStatus
    visibility: PostVisibility
    is_anonymous: bool
    is_pinned: bool
    is_locked: bool
    is_featured: bool
    read_time_minutes: int
    view_count: int
    bookmark_count: int
    share_count: int
    created_at: datetime
    updated_at: datetime
    featured_image_document_id: UUID | None = None
    published_at: datetime | None = None
    updated_by: UUID | None = None


class PostSearchResponse(ORJSONModel):
    items: list[PostResponse]
    total: int


class PostFeedResponse(ORJSONModel):
    items: list[PostResponse]
    next_cursor: str | None = None


class CreatePostRequest(ORJSONModel):
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1)
    slug: str | None = Field(default=None, min_length=3, max_length=100, pattern=_SLUG_PATTERN)
    excerpt: str | None = Field(default=None, max_length=500)
    post_type: PostType = PostType.DISCUSSION
    visibility: PostVisibility = PostVisibility.PUBLIC
    is_anonymous: bool = False
    featured_image_document_id: UUID | None = None
    topic_ids: list[UUID] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class UpdatePostRequest(ORJSONModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    body: str | None = Field(default=None, min_length=1)
    excerpt: str | None = Field(default=None, max_length=500)
    regenerate_excerpt: bool = False
    post_type: PostType | None = None
    visibility: PostVisibility | None = None
    is_anonymous: bool | None = None
    featured_image_document_id: UUID | None = None
    clear_featured_image: bool = False


class SetPostPinnedRequest(ORJSONModel):
    pinned: bool


class SetPostLockedRequest(ORJSONModel):
    locked: bool


class SetPostFeaturedRequest(ORJSONModel):
    featured: bool


# --- Post topics ---------------------------------------------------------------------


class PostTopicResponse(ORJSONModel):
    id: UUID
    post_id: UUID
    topic_id: UUID


class AssignPostTopicRequest(ORJSONModel):
    topic_id: UUID


# --- Post tags -------------------------------------------------------------------------


class PostTagResponse(ORJSONModel):
    id: UUID
    post_id: UUID
    tag: str


class AssignPostTagRequest(ORJSONModel):
    tag: str = Field(min_length=1, max_length=50)


# --- Post attachments ---------------------------------------------------------------------


class PostAttachmentResponse(ORJSONModel):
    id: UUID
    post_id: UUID
    document_id: UUID


class AddPostAttachmentRequest(ORJSONModel):
    document_id: UUID
