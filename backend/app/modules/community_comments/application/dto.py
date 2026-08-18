"""Data Transfer Objects for the Community Comments module's application
layer.

Distinct from both domain entities (never leave the module) and API
schemas (`presentation/schemas.py`, the Pydantic v2 validation boundary).
Use-case input/output DTOs are plain, immutable dataclasses — the same
shape `app.modules.community_answers.application.dto` already
establishes; `CommunityCommentSummaryDTO` is also re-exported from
`public/dto.py` for other modules to depend on.

`CommunityCommentSummaryDTO.author_id` is `UUID | None`, not a mandatory
`UUID` — the same "anonymous identity must remain hidden through the
public API" masking `CommunityAnswerSummaryDTO.author_id` already
establishes (see `_summary_mappers.comment_to_summary`'s own docstring),
applied here to this task's own "Anonymous Comments"/"Anonymous Replies"
features.

Every listing/searching input (`ListCommentsInput`/`ListRepliesInput`/
`SearchCommentsInput`) is cursor-paginated — see
`CommunityCommentRepository`'s own docstring for why this module departs
from Phase 5.6's offset+cursor split.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.community_comments.domain.enums import CommentStatus, CommentTargetType

# --- CreateComment / CreateReply -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateCommentInput:
    target_type: CommentTargetType
    target_id: UUID
    author_id: UUID
    body: str
    is_anonymous: bool = False


@dataclass(frozen=True, slots=True)
class CreateCommentOutput:
    comment_id: UUID
    target_type: CommentTargetType
    target_id: UUID
    status: CommentStatus


@dataclass(frozen=True, slots=True)
class CreateReplyInput:
    parent_comment_id: UUID
    author_id: UUID
    body: str
    is_anonymous: bool = False


@dataclass(frozen=True, slots=True)
class CreateReplyOutput:
    comment_id: UUID
    parent_comment_id: UUID
    root_comment_id: UUID
    depth: int
    status: CommentStatus


# --- UpdateComment (also used for replies — see domain module docstring) -------------


@dataclass(frozen=True, slots=True)
class UpdateCommentInput:
    comment_id: UUID
    acting_user_id: UUID
    body: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateCommentOutput:
    comment_id: UUID
    status: CommentStatus
    revision_number: int


# --- DeleteComment / lifecycle actions (also used for replies) -----------------------


@dataclass(frozen=True, slots=True)
class DeleteCommentInput:
    comment_id: UUID
    acting_user_id: UUID


@dataclass(frozen=True, slots=True)
class PublishCommentInput:
    comment_id: UUID
    acting_user_id: UUID


@dataclass(frozen=True, slots=True)
class ArchiveCommentInput:
    comment_id: UUID
    acting_user_id: UUID


@dataclass(frozen=True, slots=True)
class RestoreCommentInput:
    comment_id: UUID
    acting_user_id: UUID


# --- Cross-cutting read model (also re-exported via public/dto.py) -------------------


@dataclass(frozen=True, slots=True)
class CommunityCommentSummaryDTO:
    comment_id: UUID
    target_type: CommentTargetType
    target_id: UUID
    community_id: UUID
    organization_id: UUID
    body: str
    status: CommentStatus
    is_anonymous: bool
    root_comment_id: UUID
    depth: int
    revision_number: int
    created_at: datetime
    updated_at: datetime
    topic_id: UUID | None = None
    parent_comment_id: UUID | None = None
    author_id: UUID | None = None
    published_at: datetime | None = None
    updated_by: UUID | None = None

    @property
    def id(self) -> UUID:
        """Alias for `comment_id` — see `CommunityAnswerSummaryDTO.id`'s
        own docstring for the full reasoning (identical situation in
        every module)."""
        return self.comment_id


# --- ListComments (cursor, top-level-only, target-scoped) ----------------------------


@dataclass(frozen=True, slots=True)
class ListCommentsInput:
    organization_id: UUID
    target_type: CommentTargetType
    target_id: UUID
    status: tuple[CommentStatus, ...] | None = None
    sort_order: Literal["asc", "desc"] = "desc"
    cursor: str | None = None
    limit: int = 20


# --- ListReplies (cursor, direct-children-only, parent-scoped) -----------------------


@dataclass(frozen=True, slots=True)
class ListRepliesInput:
    organization_id: UUID
    parent_comment_id: UUID
    status: tuple[CommentStatus, ...] | None = None
    sort_order: Literal["asc", "desc"] = "desc"
    cursor: str | None = None
    limit: int = 20


@dataclass(frozen=True, slots=True)
class CommentFeedOutput:
    items: tuple[CommunityCommentSummaryDTO, ...]
    next_cursor: str | None = None


# --- SearchComments (cursor, full filter set — also backs the "my drafts" view) ------


@dataclass(frozen=True, slots=True)
class SearchCommentsInput:
    organization_id: UUID
    query: str | None = None
    target_type: CommentTargetType | None = None
    target_id: UUID | None = None
    community_id: UUID | None = None
    topic_id: UUID | None = None
    author_id: UUID | None = None
    parent_comment_id: UUID | None = None
    top_level_only: bool = False
    status: tuple[CommentStatus, ...] | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    include_deleted: bool = False
    sort_order: Literal["asc", "desc"] = "desc"
    cursor: str | None = None
    limit: int = 20


@dataclass(frozen=True, slots=True)
class SearchCommentsOutput:
    items: tuple[CommunityCommentSummaryDTO, ...]
    next_cursor: str | None = None


# --- GetThread (bounded-depth, flat — the caller reconstructs the tree shape) --------


@dataclass(frozen=True, slots=True)
class ThreadOutput:
    items: tuple[CommunityCommentSummaryDTO, ...]


# --- Comment revisions ------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CommentRevisionSummaryDTO:
    revision_id: UUID
    comment_id: UUID
    revision_number: int
    previous_body: str
    author_id: UUID
    created_at: datetime

    @property
    def id(self) -> UUID:
        return self.revision_id


# --- Comment attachments -----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CommentAttachmentSummaryDTO:
    attachment_id: UUID
    comment_id: UUID
    document_id: UUID

    @property
    def id(self) -> UUID:
        return self.attachment_id


@dataclass(frozen=True, slots=True)
class AddCommentAttachmentInput:
    comment_id: UUID
    acting_user_id: UUID
    document_id: UUID


@dataclass(frozen=True, slots=True)
class RemoveCommentAttachmentInput:
    comment_id: UUID
    acting_user_id: UUID
    attachment_id: UUID
