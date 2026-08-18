"""Repository interfaces — one per aggregate root, expressed in domain
vocabulary only (no session, no SQL). Concrete implementations live in
`app.modules.community_answers.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

`CommunityAnswerRepository` exposes the same two-read-path split
`app.modules.community_questions.domain.repositories
.CommunityQuestionRepository` already establishes (`search()` for the
full-filter management/search view, `browse_feed()` for the cursor-
paginated consumer feed backing `ListQuestionAnswersService`/
`ListAuthorAnswersService` — see those services' own docstrings for why
"List" here still means cursor-paginated, per this task's own QUERY/
FILTERING section: "Use cursor pagination. Default ordering should be
deterministic.").

No `remove()` method on `CommunityAnswerRepository`: deletion is the
business-visible `CommunityAnswer.delete()` status transition, persisted
through the ordinary `add()` upsert — see `AnswerStatus`'s own docstring.
`search()`'s own `include_deleted` flag filters on `status != DELETED`
instead of a `deleted_at` column.

`browse_feed()` includes only `PUBLISHED` answers (unlike
`CommunityQuestionRepository.browse_feed`'s own PUBLISHED+CLOSED
inclusion — answers have no `CLOSED` status to also include, see
`AnswerStatus`'s own docstring).

`CommunityAnswerRevisionRepository` has no `remove()` method at all —
this task's own REVISION HISTORY section: "Revision history must be
immutable." Once a revision is written it can never be edited or
deleted, so there is no mutating or destructive method to expose, unlike
every other child-aggregate repository in this codebase (which all offer
at least a hard-delete `remove()`).

`CommunityAnswerAttachmentRepository` enforces no soft-delete — a row is
either present or absent, never edited — the same shape
`CommunityQuestionAttachmentRepository` already establishes.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.community_answers.domain.entities import (
    CommunityAnswer,
    CommunityAnswerAttachment,
    CommunityAnswerRevision,
)
from app.modules.community_answers.domain.enums import AnswerStatus, AnswerVisibility


class CommunityAnswerRepository(ABC):
    @abstractmethod
    async def get_by_id(self, answer_id: UUID) -> CommunityAnswer | None: ...

    @abstractmethod
    async def get_best_answer_for_question(self, question_id: UUID) -> CommunityAnswer | None:
        """The current best answer for `question_id`, if any — backs the
        "a question can have only one best answer" coordination in
        `MarkBestAnswerService`."""
        ...

    @abstractmethod
    async def search(
        self,
        *,
        organization_id: UUID,
        question_id: UUID | None = None,
        community_id: UUID | None = None,
        topic_id: UUID | None = None,
        author_id: UUID | None = None,
        status: Sequence[AnswerStatus] | None = None,
        visibility: Sequence[AnswerVisibility] | None = None,
        best_answer_only: bool = False,
        featured_only: bool = False,
        pinned_only: bool = False,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        query: str | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[CommunityAnswer], int]:
        """Full-filter search, backing `ListAnswersService`/
        `SearchAnswersService` — see this module's own QUERY/FILTERING
        section (Question/Community/Medical Topic/Author/Status/
        Visibility/Best Answer/Featured/Pinned/Keyword/Date range).
        `organization_id` is mandatory — every call is inherently
        tenant-scoped, the same non-negotiable-first-parameter shape
        `CommunityQuestionRepository.search`'s own `organization_id`
        already establishes. `query` combines full-text search over
        `body`/`summary` with no separate partial-match column (answers
        have no title/slug to substring-match against).
        `include_deleted=False` excludes `status == DELETED`. Returns
        `(page, total_matching_count)`.
        """
        ...

    @abstractmethod
    async def browse_feed(
        self,
        *,
        organization_id: UUID,
        question_id: UUID | None = None,
        community_id: UUID | None = None,
        author_id: UUID | None = None,
        pinned_first: bool = False,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[Sequence[CommunityAnswer], str | None]:
        """Cursor-paginated feed, restricted to `PUBLISHED` answers —
        see this interface's own docstring for the full keyset-
        pagination reasoning. `pinned_first=True` (set only by
        `ListQuestionAnswersService`) sorts `is_pinned` answers ahead of
        the normal `published_at DESC` ordering, the same "pinned shown
        once, on page 1 only" behavior `CommunityQuestionRepository
        .browse_feed` already establishes."""
        ...

    @abstractmethod
    async def add(self, answer: CommunityAnswer) -> None: ...


class CommunityAnswerRevisionRepository(ABC):
    @abstractmethod
    async def get_by_id(self, revision_id: UUID) -> CommunityAnswerRevision | None: ...

    @abstractmethod
    async def list_by_answer(
        self, answer_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[CommunityAnswerRevision]:
        """Newest revision first. No `remove()` exists on this
        interface at all — see this module's own docstring."""
        ...

    @abstractmethod
    async def add(self, revision: CommunityAnswerRevision) -> None: ...


class CommunityAnswerAttachmentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, attachment_id: UUID) -> CommunityAnswerAttachment | None: ...

    @abstractmethod
    async def list_by_answer(self, answer_id: UUID) -> list[CommunityAnswerAttachment]: ...

    @abstractmethod
    async def is_assigned(self, answer_id: UUID, document_id: UUID) -> bool: ...

    @abstractmethod
    async def add(self, attachment: CommunityAnswerAttachment) -> None: ...

    @abstractmethod
    async def remove(self, attachment_id: UUID) -> None:
        """Hard delete — a no-op if already missing."""
        ...
