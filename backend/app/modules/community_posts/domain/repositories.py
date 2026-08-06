"""Repository interfaces — one per aggregate root, expressed in domain
vocabulary only (no session, no SQL). Concrete implementations live in
`app.modules.community_posts.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

`CommunityPostRepository` exposes two distinct read paths, matching this
task's own split between the SEARCH section (full-filter, offset-paged,
total-count-aware) and the "Cursor pagination" REPOSITORIES bullet
(forward-only, keyset-paged, no total count):

- `search()` backs `ListPostsService`/`SearchPostsService` — the
  management/full-filter view, offset/limit paged, the same shape every
  other module's own `search()` already uses.
- `browse_feed()` backs `BrowseCommunityFeedService`/`BrowseTopicFeedService`/
  `BrowseAuthorPostsService` — the high-traffic, infinite-scroll feed
  views. Keyset ("cursor") pagination on `(published_at, id)` rather than
  `OFFSET`/`LIMIT`: stable under concurrent inserts (a new post landing on
  page 1 while a caller pages through doesn't shift already-fetched rows
  out from under them, unlike `OFFSET`, which counts rows from the start
  every time) and avoids `OFFSET`'s well-known O(n) cost on a large,
  fast-growing feed table. `cursor` is an opaque, repository-owned token
  (never inspected/constructed by callers above the infrastructure layer)
  — see `SqlAlchemyCommunityPostRepository`'s own docstring for its
  concrete encoding. Returns `(page, next_cursor)`; `next_cursor is None`
  means "no more results," the same "cursor absence signals the end"
  convention every keyset-pagination API uses.

No `update()` method on any interface: a repository returns the actual
aggregate object, the caller mutates it via its own methods, and the Unit
of Work's `commit()` persists the change through SQLAlchemy's
session-level change tracking — `add()` is upsert, the same shape every
other module's repository already uses.

`CommunityPostTopicRepository`/`CommunityPostTagRepository`/
`CommunityPostAttachmentRepository` enforce no soft-delete — an
assignment is either present or absent, never edited — the same shape
`CommunityRuleRepository`/`MedicalTopicRelationRepository` already
establish for their own child aggregates.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.community_posts.domain.entities import (
    CommunityPost,
    CommunityPostAttachment,
    CommunityPostTag,
    CommunityPostTopic,
)
from app.modules.community_posts.domain.enums import PostStatus, PostType, PostVisibility


class CommunityPostRepository(ABC):
    @abstractmethod
    async def get_by_id(self, post_id: UUID) -> CommunityPost | None: ...

    @abstractmethod
    async def get_by_slug(self, community_id: UUID, slug: str) -> CommunityPost | None: ...

    @abstractmethod
    async def search(
        self,
        *,
        organization_id: UUID,
        community_id: UUID | None = None,
        topic_id: UUID | None = None,
        author_id: UUID | None = None,
        post_type: Sequence[PostType] | None = None,
        status: Sequence[PostStatus] | None = None,
        visibility: Sequence[PostVisibility] | None = None,
        pinned_only: bool = False,
        featured_only: bool = False,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        query: str | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[CommunityPost], int]:
        """Full-filter search, backing `ListPostsService`/
        `SearchPostsService` — see this module's own SEARCH section
        (Community/Topic/Author/Type/Status/Visibility/Pinned/Featured/
        Date range/Keyword). `organization_id` is mandatory (not one of
        the optional filters) — every call is inherently tenant-scoped,
        the same non-negotiable-first-parameter shape
        `CommunityRepository.search`'s own `organization_id` already
        establishes; `community_id`/`topic_id` narrow *within* that
        tenant further, they never replace the tenant scope, since a
        platform-wide `MedicalTopic` can have posts attached to it from
        communities in *other* organizations too. `query` combines
        full-text search over `title`/`body`/`excerpt` with a partial
        match on `title` — the same `apply_combined_text_search` shape
        every other module's own `search()` already uses. Returns
        `(page, total_matching_count)`.
        """
        ...

    @abstractmethod
    async def browse_feed(
        self,
        *,
        organization_id: UUID,
        community_id: UUID | None = None,
        topic_id: UUID | None = None,
        author_id: UUID | None = None,
        pinned_first: bool = False,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[Sequence[CommunityPost], str | None]:
        """Cursor-paginated feed, restricted to `PUBLISHED` posts only —
        see this interface's own docstring for the full keyset-pagination
        reasoning. `pinned_first=True` (set only by
        `BrowseCommunityFeedService` — pinning is a per-community "sticky
        post" concept, not global, see `CommunityPost.set_pinned`'s own
        docstring) sorts `is_pinned` posts ahead of the normal
        `published_at DESC` ordering."""
        ...

    @abstractmethod
    async def add(self, post: CommunityPost) -> None: ...

    @abstractmethod
    async def remove(self, post_id: UUID) -> None:
        """Soft-delete: sets `deleted_at` directly at the infrastructure
        level without loading/mutating the domain entity — the same
        shape `CommunityRepository.remove`/`MedicalTopicRepository.remove`
        already use; a no-op if already deleted or missing."""
        ...


class CommunityPostTopicRepository(ABC):
    @abstractmethod
    async def get_by_id(self, post_topic_id: UUID) -> CommunityPostTopic | None: ...

    @abstractmethod
    async def list_by_post(self, post_id: UUID) -> list[CommunityPostTopic]: ...

    @abstractmethod
    async def list_post_ids_by_topic(
        self, topic_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[UUID]:
        """Backs `BrowseTopicFeedService` — every post id assigned to
        `topic_id`, newest assignment first."""
        ...

    @abstractmethod
    async def is_assigned(self, post_id: UUID, topic_id: UUID) -> bool: ...

    @abstractmethod
    async def add(self, assignment: CommunityPostTopic) -> None: ...

    @abstractmethod
    async def remove(self, post_topic_id: UUID) -> None:
        """Hard delete — a no-op if already missing."""
        ...


class CommunityPostTagRepository(ABC):
    @abstractmethod
    async def get_by_id(self, post_tag_id: UUID) -> CommunityPostTag | None: ...

    @abstractmethod
    async def list_by_post(self, post_id: UUID) -> list[CommunityPostTag]: ...

    @abstractmethod
    async def is_assigned(self, post_id: UUID, tag: str) -> bool: ...

    @abstractmethod
    async def add(self, assignment: CommunityPostTag) -> None: ...

    @abstractmethod
    async def remove(self, post_tag_id: UUID) -> None:
        """Hard delete — a no-op if already missing."""
        ...


class CommunityPostAttachmentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, attachment_id: UUID) -> CommunityPostAttachment | None: ...

    @abstractmethod
    async def list_by_post(self, post_id: UUID) -> list[CommunityPostAttachment]: ...

    @abstractmethod
    async def is_assigned(self, post_id: UUID, document_id: UUID) -> bool: ...

    @abstractmethod
    async def add(self, attachment: CommunityPostAttachment) -> None: ...

    @abstractmethod
    async def remove(self, attachment_id: UUID) -> None:
        """Hard delete — a no-op if already missing."""
        ...
