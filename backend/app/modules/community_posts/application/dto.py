"""Data Transfer Objects for the Community Posts module's application
layer.

Distinct from both domain entities (never leave the module) and API
schemas (`presentation/schemas.py`, the Pydantic v2 validation boundary).
Use-case input/output DTOs are plain, immutable dataclasses — the same
shape every prior module's `application/dto.py` already establishes;
`CommunityPostSummaryDTO` is also re-exported from `public/dto.py` for
other modules to depend on.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.community_posts.domain.enums import PostStatus, PostType, PostVisibility

# --- CreatePost ----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreatePostInput:
    community_id: UUID
    author_id: UUID
    title: str
    body: str
    slug: str | None = None
    excerpt: str | None = None
    post_type: PostType = PostType.DISCUSSION
    visibility: PostVisibility = PostVisibility.PUBLIC
    is_anonymous: bool = False
    featured_image_document_id: UUID | None = None
    topic_ids: tuple[UUID, ...] = ()
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CreatePostOutput:
    post_id: UUID
    community_id: UUID
    slug: str
    title: str
    status: PostStatus


# --- UpdatePost ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UpdatePostInput:
    post_id: UUID
    acting_user_id: UUID
    title: str | None = None
    body: str | None = None
    excerpt: str | None = None
    regenerate_excerpt: bool = False
    post_type: PostType | None = None
    visibility: PostVisibility | None = None
    is_anonymous: bool | None = None
    featured_image_document_id: UUID | None = None
    clear_featured_image: bool = False


@dataclass(frozen=True, slots=True)
class UpdatePostOutput:
    post_id: UUID
    title: str
    status: PostStatus
    visibility: PostVisibility


# --- DeletePost / PublishPost / ArchivePost --------------------------------------


@dataclass(frozen=True, slots=True)
class DeletePostInput:
    post_id: UUID
    acting_user_id: UUID


@dataclass(frozen=True, slots=True)
class PublishPostInput:
    post_id: UUID
    acting_user_id: UUID


@dataclass(frozen=True, slots=True)
class ArchivePostInput:
    post_id: UUID
    acting_user_id: UUID


# --- PinPost / LockPost / FeaturePost (moderator-only toggles) -------------------


@dataclass(frozen=True, slots=True)
class SetPostPinnedInput:
    post_id: UUID
    acting_user_id: UUID
    pinned: bool


@dataclass(frozen=True, slots=True)
class SetPostLockedInput:
    post_id: UUID
    acting_user_id: UUID
    locked: bool


@dataclass(frozen=True, slots=True)
class SetPostFeaturedInput:
    post_id: UUID
    acting_user_id: UUID
    featured: bool


# --- Cross-cutting read models (also re-exported via public/dto.py) --------------


@dataclass(frozen=True, slots=True)
class CommunityPostSummaryDTO:
    post_id: UUID
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

    @property
    def id(self) -> UUID:
        """Alias for `post_id` — see `AppointmentSummaryDTO.id`'s own
        docstring in `app.modules.appointment.application.dto` for the
        full reasoning (identical situation in every module)."""
        return self.post_id


# --- ListPosts / SearchPosts (offset-paged, full-filter) -------------------------


@dataclass(frozen=True, slots=True)
class ListPostsInput:
    organization_id: UUID
    community_id: UUID | None = None
    topic_id: UUID | None = None
    author_id: UUID | None = None
    post_type: tuple[PostType, ...] | None = None
    status: tuple[PostStatus, ...] | None = None
    visibility: tuple[PostVisibility, ...] | None = None
    pinned_only: bool = False
    featured_only: bool = False
    created_from: datetime | None = None
    created_to: datetime | None = None
    query: str | None = None
    include_deleted: bool = False
    sort_by: str = "created_at"
    sort_order: str = "desc"
    offset: int = 0
    limit: int = 20


@dataclass(frozen=True, slots=True)
class ListPostsOutput:
    items: tuple[CommunityPostSummaryDTO, ...]
    total: int


@dataclass(frozen=True, slots=True)
class SearchPostsInput:
    organization_id: UUID
    query: str
    community_id: UUID | None = None
    topic_id: UUID | None = None
    author_id: UUID | None = None
    post_type: tuple[PostType, ...] | None = None
    status: tuple[PostStatus, ...] | None = None
    visibility: tuple[PostVisibility, ...] | None = None
    pinned_only: bool = False
    featured_only: bool = False
    created_from: datetime | None = None
    created_to: datetime | None = None
    offset: int = 0
    limit: int = 20


@dataclass(frozen=True, slots=True)
class SearchPostsOutput:
    items: tuple[CommunityPostSummaryDTO, ...]
    total: int


# --- Browse*Feed (cursor-paged) ---------------------------------------------------


@dataclass(frozen=True, slots=True)
class BrowseCommunityFeedInput:
    community_id: UUID
    cursor: str | None = None
    limit: int = 20


@dataclass(frozen=True, slots=True)
class BrowseTopicFeedInput:
    organization_id: UUID
    topic_id: UUID
    cursor: str | None = None
    limit: int = 20


@dataclass(frozen=True, slots=True)
class BrowseAuthorPostsInput:
    organization_id: UUID
    author_id: UUID
    cursor: str | None = None
    limit: int = 20


@dataclass(frozen=True, slots=True)
class PostFeedOutput:
    items: tuple[CommunityPostSummaryDTO, ...]
    next_cursor: str | None = None


# --- Post topics -------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PostTopicSummaryDTO:
    post_topic_id: UUID
    post_id: UUID
    topic_id: UUID

    @property
    def id(self) -> UUID:
        return self.post_topic_id


@dataclass(frozen=True, slots=True)
class AssignPostTopicInput:
    post_id: UUID
    acting_user_id: UUID
    topic_id: UUID


@dataclass(frozen=True, slots=True)
class UnassignPostTopicInput:
    post_id: UUID
    acting_user_id: UUID
    post_topic_id: UUID


# --- Post tags -----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PostTagSummaryDTO:
    post_tag_id: UUID
    post_id: UUID
    tag: str

    @property
    def id(self) -> UUID:
        return self.post_tag_id


@dataclass(frozen=True, slots=True)
class AssignPostTagInput:
    post_id: UUID
    acting_user_id: UUID
    tag: str


@dataclass(frozen=True, slots=True)
class UnassignPostTagInput:
    post_id: UUID
    acting_user_id: UUID
    post_tag_id: UUID


# --- Post attachments -------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PostAttachmentSummaryDTO:
    attachment_id: UUID
    post_id: UUID
    document_id: UUID

    @property
    def id(self) -> UUID:
        return self.attachment_id


@dataclass(frozen=True, slots=True)
class AddPostAttachmentInput:
    post_id: UUID
    acting_user_id: UUID
    document_id: UUID


@dataclass(frozen=True, slots=True)
class RemovePostAttachmentInput:
    post_id: UUID
    acting_user_id: UUID
    attachment_id: UUID
