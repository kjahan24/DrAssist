"""Repository interfaces (ports) for the Community Comments module.
Concrete implementations live in `infrastructure/repositories.py`; the
application layer depends only on these ABCs.

`CommunityCommentRepository` has one flexible `browse()` method — cursor-
paginated, supporting every QUERY/PAGINATION filter this task's own
section names (target/author/community/topic/status/parent/keyword/date
range) — rather than a `search()` (offset) + `browse_feed()` (cursor)
split like `app.modules.community_answers.domain.repositories
.CommunityAnswerRepository` has. This is a deliberate departure from that
precedent: this task's own QUERY/PAGINATION section states "Use
deterministic cursor pagination" once, covering the *entire* filter set
(including keyword search), unlike Phase 5.6's task text, which never
made that a blanket instruction — so `ListCommentsService`/
`ListRepliesService`/`SearchCommentsService`/a management "my drafts"
view all share this one method, each simply passing a different
combination of filters.

`get_thread` is a second, distinct method — not cursor-paginated, not a
recursive query — see its own docstring: a bounded-depth conversation
tree is fetched flat, in one shot, via `root_comment_id`/`depth`
columns.

No `remove()` on `CommunityCommentRepository`: deletion is the
`CommunityComment.delete()` status transition, persisted through the
ordinary `add()` upsert — see `CommentStatus`'s own docstring.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.community_comments.domain.entities import (
    CommunityComment,
    CommunityCommentAttachment,
    CommunityCommentRevision,
)
from app.modules.community_comments.domain.enums import CommentStatus, CommentTargetType


class CommunityCommentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, comment_id: UUID) -> CommunityComment | None: ...

    @abstractmethod
    async def browse(
        self,
        *,
        organization_id: UUID,
        target_type: CommentTargetType | None = None,
        target_id: UUID | None = None,
        community_id: UUID | None = None,
        topic_id: UUID | None = None,
        author_id: UUID | None = None,
        parent_comment_id: UUID | None = None,
        top_level_only: bool = False,
        status: Sequence[CommentStatus] | None = None,
        query: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        include_deleted: bool = False,
        sort_order: Literal["asc", "desc"] = "desc",
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[Sequence[CommunityComment], str | None]: ...

    @abstractmethod
    async def get_thread(
        self,
        root_comment_id: UUID,
        *,
        max_depth: int,
        status: Sequence[CommentStatus] | None = None,
        limit: int = 500,
    ) -> Sequence[CommunityComment]:
        """Every comment (the root itself, at `depth == 0`, plus every
        descendant reply) with `root_comment_id == root_comment_id` and
        `depth <= max_depth`, ordered `(depth, created_at)` ascending — a
        single flat, indexed query; the caller reconstructs the tree
        shape in memory from each row's own `parent_comment_id`. No
        recursive CTE, satisfying this task's own "Do not use unbounded
        recursive queries" / "Use safe bounded-depth thread retrieval"
        instructions. `limit` is a hard safety cap on total rows
        returned, independent of `max_depth` — a shallow-but-wide thread
        (thousands of direct replies to one root) is bounded too."""
        ...

    @abstractmethod
    async def add(self, comment: CommunityComment) -> None: ...


class CommunityCommentRevisionRepository(ABC):
    """No `remove()` method at all — see `CommunityCommentRevision`'s
    own docstring: revision history is immutable, full stop, the same
    "no destructive method on the interface itself" enforcement
    `app.modules.community_answers.domain.repositories
    .CommunityAnswerRevisionRepository` already establishes."""

    @abstractmethod
    async def get_by_id(self, revision_id: UUID) -> CommunityCommentRevision | None: ...

    @abstractmethod
    async def list_by_comment(
        self, comment_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[CommunityCommentRevision]: ...

    @abstractmethod
    async def add(self, revision: CommunityCommentRevision) -> None: ...


class CommunityCommentAttachmentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, attachment_id: UUID) -> CommunityCommentAttachment | None: ...

    @abstractmethod
    async def list_by_comment(self, comment_id: UUID) -> list[CommunityCommentAttachment]: ...

    @abstractmethod
    async def is_assigned(self, comment_id: UUID, document_id: UUID) -> bool: ...

    @abstractmethod
    async def add(self, attachment: CommunityCommentAttachment) -> None: ...

    @abstractmethod
    async def remove(self, attachment_id: UUID) -> None: ...
