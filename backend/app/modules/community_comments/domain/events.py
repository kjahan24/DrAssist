"""Domain events published by Community Comments module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork`.

Like `app.modules.community_answers.domain.events.CommunityAnswerDeleted`,
`CommunityCommentDeleted` *does* exist — deletion here is a
business-visible status transition (`CommunityComment.delete()`), not an
infrastructure-only concern, see `CommentStatus`'s own docstring.

`CommunityCommentCreated` carries `parent_comment_id` (nullable) so a
future listener (e.g. a notification module) can distinguish "new
top-level comment" from "new reply" without a separate event type.
"""

from dataclasses import dataclass
from uuid import UUID

from app.modules.community_comments.domain.enums import CommentTargetType
from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class CommunityCommentCreated(DomainEvent):
    comment_id: UUID
    target_type: CommentTargetType
    target_id: UUID
    author_id: UUID
    parent_comment_id: UUID | None


@dataclass(frozen=True, kw_only=True)
class CommunityCommentUpdated(DomainEvent):
    comment_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityCommentPublished(DomainEvent):
    comment_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityCommentArchived(DomainEvent):
    comment_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityCommentRestored(DomainEvent):
    comment_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityCommentDeleted(DomainEvent):
    comment_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityCommentRevisionCreated(DomainEvent):
    revision_id: UUID
    comment_id: UUID
    revision_number: int


@dataclass(frozen=True, kw_only=True)
class CommunityCommentAttachmentAdded(DomainEvent):
    attachment_id: UUID
    comment_id: UUID
    document_id: UUID
