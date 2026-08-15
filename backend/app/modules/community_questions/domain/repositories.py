"""Repository interfaces — one per aggregate root, expressed in domain
vocabulary only (no session, no SQL). Concrete implementations live in
`app.modules.community_questions.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

`CommunityQuestionRepository` exposes the same two-read-path split
`app.modules.community_posts.domain.repositories.CommunityPostRepository`
already establishes (`search()` for the full-filter management view,
`browse_feed()` for the cursor-paginated consumer feed) — see that
interface's own docstring for the full keyset-pagination reasoning,
which applies identically here.

Two deliberate differences from `CommunityPostRepository`:

- No `remove()` method: deletion here is a business-visible
  `CommunityQuestion.delete()` status transition (persisted through the
  ordinary `add()` upsert), not an infrastructure-only soft delete — see
  `QuestionStatus`'s own docstring. `search()`'s own `include_deleted`
  flag filters on `status != DELETED` instead of a `deleted_at` column.
- `topic_id` filtering (on both `search()` and `browse_feed()`) must
  match *either* `primary_topic_id` *or* a `community_question_topics`
  secondary assignment — this task's own DOMAIN section splits "one
  primary" from "optional secondary" topics, so a topic-scoped query has
  to check both places; see `SqlAlchemyCommunityQuestionRepository
  ._topic_scoped_question_ids`'s own docstring for the concrete query.

`browse_feed()` includes both `PUBLISHED` and `CLOSED` questions (not
`PUBLISHED`-only, unlike `CommunityPostRepository.browse_feed`) — a
closed question is still real, visible content (its answers, once the
Answers module exists, remain readable); "closed" means "no longer
accepting new engagement," not "hidden." `DRAFT`/`ARCHIVED`/`DELETED`
are still excluded.

`CommunityQuestionTopicRepository`/`CommunityQuestionTagRepository`/
`CommunityQuestionAttachmentRepository`/`CommunityQuestionFollowerRepository`
all enforce no soft-delete — a row is either present or absent, never
edited — the same shape `CommunityPostTopicRepository`/
`CommunityPostTagRepository`/`CommunityPostAttachmentRepository` already
establish for their own child aggregates.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.community_questions.domain.entities import (
    CommunityQuestion,
    CommunityQuestionAttachment,
    CommunityQuestionFollower,
    CommunityQuestionTag,
    CommunityQuestionTopic,
)
from app.modules.community_questions.domain.enums import (
    QuestionStatus,
    QuestionType,
    QuestionVisibility,
)


class CommunityQuestionRepository(ABC):
    @abstractmethod
    async def get_by_id(self, question_id: UUID) -> CommunityQuestion | None: ...

    @abstractmethod
    async def get_by_slug(self, community_id: UUID, slug: str) -> CommunityQuestion | None: ...

    @abstractmethod
    async def search(
        self,
        *,
        organization_id: UUID,
        community_id: UUID | None = None,
        topic_id: UUID | None = None,
        author_id: UUID | None = None,
        question_type: Sequence[QuestionType] | None = None,
        status: Sequence[QuestionStatus] | None = None,
        visibility: Sequence[QuestionVisibility] | None = None,
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
    ) -> tuple[Sequence[CommunityQuestion], int]:
        """Full-filter search, backing `ListQuestionsService`/
        `SearchQuestionsService` — see this module's own SEARCH section
        (Community/Topic/Author/Type/Status/Visibility/Date/Pinned/
        Featured/Keyword). `organization_id` is mandatory — every call is
        inherently tenant-scoped, the same non-negotiable-first-parameter
        shape `CommunityPostRepository.search`'s own `organization_id`
        already establishes. `query` combines full-text search over
        `title`/`body`/`summary` with a partial match on `title`.
        `include_deleted=False` excludes `status == DELETED` (see this
        interface's own docstring). Returns `(page, total_matching_count)`.
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
    ) -> tuple[Sequence[CommunityQuestion], str | None]:
        """Cursor-paginated feed, restricted to `PUBLISHED`/`CLOSED`
        questions — see this interface's own docstring for the full
        keyset-pagination and status-inclusion reasoning. `pinned_first
        =True` (set only by `BrowseCommunityQuestionsService`) sorts
        `is_pinned` questions ahead of the normal `published_at DESC`
        ordering, the same "pinned shown once, on page 1 only" behavior
        `CommunityPostRepository.browse_feed` already establishes."""
        ...

    @abstractmethod
    async def add(self, question: CommunityQuestion) -> None: ...


class CommunityQuestionTopicRepository(ABC):
    @abstractmethod
    async def get_by_id(self, question_topic_id: UUID) -> CommunityQuestionTopic | None: ...

    @abstractmethod
    async def list_by_question(self, question_id: UUID) -> list[CommunityQuestionTopic]: ...

    @abstractmethod
    async def list_question_ids_by_topic(
        self, topic_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[UUID]:
        """Every question id with a *secondary* assignment to `topic_id`
        — newest assignment first. Does not include questions where
        `topic_id` is only the *primary* topic; callers needing both
        (e.g. `BrowseTopicQuestionsService`, via
        `CommunityQuestionRepository.browse_feed`'s own `topic_id`
        filter) get that union at the `CommunityQuestionRepository`
        level, not here."""
        ...

    @abstractmethod
    async def is_assigned(self, question_id: UUID, topic_id: UUID) -> bool: ...

    @abstractmethod
    async def add(self, assignment: CommunityQuestionTopic) -> None: ...

    @abstractmethod
    async def remove(self, question_topic_id: UUID) -> None:
        """Hard delete — a no-op if already missing."""
        ...


class CommunityQuestionTagRepository(ABC):
    @abstractmethod
    async def get_by_id(self, question_tag_id: UUID) -> CommunityQuestionTag | None: ...

    @abstractmethod
    async def list_by_question(self, question_id: UUID) -> list[CommunityQuestionTag]: ...

    @abstractmethod
    async def is_assigned(self, question_id: UUID, tag: str) -> bool: ...

    @abstractmethod
    async def add(self, assignment: CommunityQuestionTag) -> None: ...

    @abstractmethod
    async def remove(self, question_tag_id: UUID) -> None:
        """Hard delete — a no-op if already missing."""
        ...


class CommunityQuestionAttachmentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, attachment_id: UUID) -> CommunityQuestionAttachment | None: ...

    @abstractmethod
    async def list_by_question(self, question_id: UUID) -> list[CommunityQuestionAttachment]: ...

    @abstractmethod
    async def is_assigned(self, question_id: UUID, document_id: UUID) -> bool: ...

    @abstractmethod
    async def add(self, attachment: CommunityQuestionAttachment) -> None: ...

    @abstractmethod
    async def remove(self, attachment_id: UUID) -> None:
        """Hard delete — a no-op if already missing."""
        ...


class CommunityQuestionFollowerRepository(ABC):
    @abstractmethod
    async def get_by_id(self, follower_id: UUID) -> CommunityQuestionFollower | None: ...

    @abstractmethod
    async def get_by_question_and_user(
        self, question_id: UUID, user_id: UUID
    ) -> CommunityQuestionFollower | None: ...

    @abstractmethod
    async def list_by_question(
        self, question_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[CommunityQuestionFollower]: ...

    @abstractmethod
    async def is_following(self, question_id: UUID, user_id: UUID) -> bool: ...

    @abstractmethod
    async def add(self, follower: CommunityQuestionFollower) -> None: ...

    @abstractmethod
    async def remove(self, follower_id: UUID) -> None:
        """Hard delete — a no-op if already missing."""
        ...
