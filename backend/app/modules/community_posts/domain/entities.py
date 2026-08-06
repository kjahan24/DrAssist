"""Community Posts module aggregate roots: CommunityPost,
CommunityPostTopic, CommunityPostTag, CommunityPostAttachment.

Each is its own aggregate — every reference to another aggregate,
including cross-module ones (`community_id` -> Community,
`author_id`/`updated_by` -> User, `topic_id` -> MedicalTopic,
`document_id` -> MedicalDocument), is by ID only, never by object
reference — the same rule every prior module's own entities already
follow. Cross-module ID references are validated by the application
layer via that peer module's own public query port (`CommunityQueryPort`/
`TopicQueryPort`/`DocumentQueryPort`), never by importing across
`domain/` packages.

`CommunityPost.organization_id` is stored directly (denormalized from
the parent `Community` at creation time by `CreatePostService`), not
resolved via a `community_id` join on every query — the same "tenant id
stored directly on the tenant-scoped row" shape `Community.organization_id`
itself already establishes, required here so multi-tenant scoping doesn't
need a cross-module join on this module's own hot query paths.

`CommunityPostTopic`/`CommunityPostTag`/`CommunityPostAttachment` all
enforce no soft-delete: an assignment is either present or absent, never
edited — the same "hard delete, no historical value" shape
`app.modules.community.domain.repositories.CommunityRuleRepository`/
`app.modules.medical_topics.domain.repositories
.MedicalTopicRelationRepository` already establish for their own child
aggregates.

`view_count`/`bookmark_count`/`share_count` are declared fields only —
this task's own APPLICATION section names no "record a view/bookmark/
share" use case, so nothing in this module increments them yet; they
exist so the column/response shape is ready for a future engagement-
tracking module to populate (see `events.py`'s own docstring). No entity
method is added to mutate them, matching the "don't build for a
hypothetical future requirement" rule — a future module adds that
method itself when it actually needs one.
"""

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.modules.community_posts.domain.enums import PostStatus, PostType, PostVisibility
from app.modules.community_posts.domain.events import (
    CommunityPostArchived,
    CommunityPostAttachmentAdded,
    CommunityPostCreated,
    CommunityPostFeaturedChanged,
    CommunityPostLockedChanged,
    CommunityPostPinnedChanged,
    CommunityPostPublished,
    CommunityPostTagAssigned,
    CommunityPostTopicAssigned,
    CommunityPostUpdated,
)
from app.modules.community_posts.domain.exceptions import (
    PostAlreadyArchivedError,
    PostAlreadyPublishedError,
    PostBodyRequiredError,
    PostTagRequiredError,
    PostTagTooLongError,
)
from app.modules.community_posts.domain.value_objects import (
    PostExcerpt,
    PostId,
    PostSlug,
    PostTitle,
)
from app.shared.domain.entity import AggregateRoot

_WORDS_PER_MINUTE = 200
_TAG_MAX_LENGTH = 50


def _compute_read_time_minutes(body: str) -> int:
    word_count = len(body.split())
    return max(math.ceil(word_count / _WORDS_PER_MINUTE), 1)


@dataclass(kw_only=True, eq=False)
class CommunityPost(AggregateRoot):
    community_id: UUID
    organization_id: UUID
    author_id: UUID
    slug: PostSlug
    title: PostTitle
    body: str
    excerpt: PostExcerpt
    post_type: PostType = PostType.DISCUSSION
    status: PostStatus = PostStatus.DRAFT
    visibility: PostVisibility = PostVisibility.PUBLIC
    is_anonymous: bool = False
    is_pinned: bool = False
    is_locked: bool = False
    is_featured: bool = False
    featured_image_document_id: UUID | None = None
    read_time_minutes: int = 1
    view_count: int = 0
    bookmark_count: int = 0
    share_count: int = 0
    published_at: datetime | None = None
    updated_by: UUID | None = None

    @classmethod
    def create(
        cls,
        *,
        community_id: UUID,
        organization_id: UUID,
        author_id: UUID,
        title: PostTitle,
        body: str,
        slug: PostSlug | None = None,
        excerpt: PostExcerpt | None = None,
        post_type: PostType = PostType.DISCUSSION,
        visibility: PostVisibility = PostVisibility.PUBLIC,
        is_anonymous: bool = False,
        featured_image_document_id: UUID | None = None,
    ) -> "CommunityPost":
        if not body.strip():
            raise PostBodyRequiredError()

        post = cls(
            community_id=community_id,
            organization_id=organization_id,
            author_id=author_id,
            slug=slug if slug is not None else PostSlug.from_title(str(title)),
            title=title,
            body=body,
            excerpt=excerpt if excerpt is not None else PostExcerpt.from_body(body),
            post_type=post_type,
            visibility=visibility,
            is_anonymous=is_anonymous,
            featured_image_document_id=featured_image_document_id,
            read_time_minutes=_compute_read_time_minutes(body),
            updated_by=author_id,
        )
        post.record_event(
            CommunityPostCreated(
                post_id=post.id,
                community_id=community_id,
                author_id=author_id,
                slug=str(post.slug),
                title=str(title),
            )
        )
        return post

    def update_content(
        self,
        *,
        title: PostTitle | None = None,
        body: str | None = None,
        excerpt: PostExcerpt | None = None,
        regenerate_excerpt: bool = False,
        post_type: PostType | None = None,
        visibility: PostVisibility | None = None,
        is_anonymous: bool | None = None,
        featured_image_document_id: UUID | None = None,
        clear_featured_image: bool = False,
        updated_by: UUID | None = None,
    ) -> None:
        """`regenerate_excerpt=True` re-derives `excerpt` from the (new)
        `body` — otherwise, editing `body` deliberately leaves an
        existing, possibly hand-written `excerpt` untouched, the same
        "editing the source doesn't silently overwrite a curated
        summary" behavior real CMS/blogging platforms already give
        editors. `clear_featured_image=True` is the same clearing-
        sentinel shape `Community.update_profile`/`MedicalTopic
        .update_profile` already establish for their own optional
        reference fields."""
        if title is not None:
            self.title = title
        if body is not None:
            if not body.strip():
                raise PostBodyRequiredError()
            self.body = body
            self.read_time_minutes = _compute_read_time_minutes(body)
        if excerpt is not None:
            self.excerpt = excerpt
        elif regenerate_excerpt:
            self.excerpt = PostExcerpt.from_body(self.body)
        if post_type is not None:
            self.post_type = post_type
        if visibility is not None:
            self.visibility = visibility
        if is_anonymous is not None:
            self.is_anonymous = is_anonymous
        if clear_featured_image:
            self.featured_image_document_id = None
        elif featured_image_document_id is not None:
            self.featured_image_document_id = featured_image_document_id
        if updated_by is not None:
            self.updated_by = updated_by

        self.touch()
        self.record_event(CommunityPostUpdated(post_id=self.id))

    def publish(self) -> None:
        if self.status is PostStatus.PUBLISHED:
            raise PostAlreadyPublishedError(self.id)
        self.status = PostStatus.PUBLISHED
        self.published_at = datetime.now(UTC)
        self.touch()
        self.record_event(CommunityPostPublished(post_id=self.id, community_id=self.community_id))

    def archive(self) -> None:
        if self.status is PostStatus.ARCHIVED:
            raise PostAlreadyArchivedError(self.id)
        self.status = PostStatus.ARCHIVED
        self.touch()
        self.record_event(CommunityPostArchived(post_id=self.id))

    def set_pinned(self, value: bool) -> None:
        """Community-moderator-only action (see `PinPostService`'s own
        docstring) — pinning is scoped to how a post sorts within its
        *own* community's feed (`BrowseCommunityFeedService`'s own
        "sticky" ordering), not a global flag."""
        if self.is_pinned is value:
            return
        self.is_pinned = value
        self.touch()
        self.record_event(CommunityPostPinnedChanged(post_id=self.id, is_pinned=value))

    def set_locked(self, value: bool) -> None:
        """Community-moderator-only action — a locked post is closed to
        future Comments/Answers modules, a flag this module only stores
        and toggles (no comment system exists yet to actually enforce
        against)."""
        if self.is_locked is value:
            return
        self.is_locked = value
        self.touch()
        self.record_event(CommunityPostLockedChanged(post_id=self.id, is_locked=value))

    def set_featured(self, value: bool) -> None:
        """Platform/community-level curation flag — the same
        `set_featured` shape `Community`/`MedicalTopic` already
        establish for themselves."""
        if self.is_featured is value:
            return
        self.is_featured = value
        self.touch()
        self.record_event(CommunityPostFeaturedChanged(post_id=self.id, is_featured=value))


@dataclass(kw_only=True, eq=False)
class CommunityPostTopic(AggregateRoot):
    post_id: PostId
    topic_id: UUID

    @classmethod
    def create(cls, *, post_id: PostId, topic_id: UUID) -> "CommunityPostTopic":
        assignment = cls(post_id=post_id, topic_id=topic_id)
        assignment.record_event(
            CommunityPostTopicAssigned(
                post_topic_id=assignment.id, post_id=post_id.value, topic_id=topic_id
            )
        )
        return assignment


@dataclass(kw_only=True, eq=False)
class CommunityPostTag(AggregateRoot):
    post_id: PostId
    tag: str

    @classmethod
    def create(cls, *, post_id: PostId, tag: str) -> "CommunityPostTag":
        normalized = tag.strip().lower()
        if not normalized:
            raise PostTagRequiredError()
        if len(normalized) > _TAG_MAX_LENGTH:
            raise PostTagTooLongError(_TAG_MAX_LENGTH)

        assignment = cls(post_id=post_id, tag=normalized)
        assignment.record_event(
            CommunityPostTagAssigned(
                post_tag_id=assignment.id, post_id=post_id.value, tag=normalized
            )
        )
        return assignment


@dataclass(kw_only=True, eq=False)
class CommunityPostAttachment(AggregateRoot):
    post_id: PostId
    document_id: UUID

    @classmethod
    def create(cls, *, post_id: PostId, document_id: UUID) -> "CommunityPostAttachment":
        attachment = cls(post_id=post_id, document_id=document_id)
        attachment.record_event(
            CommunityPostAttachmentAdded(
                attachment_id=attachment.id, post_id=post_id.value, document_id=document_id
            )
        )
        return attachment
