"""Pydantic v2 request/response schemas for the Community Comments
module.

Schemas never expose a domain entity directly, and never accept
server-controlled fields (`id`, `author_id`, ...) from the client — see
`docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention).

`CommentResponse.author_id` is `UUID | None`, not a mandatory `UUID` —
mirrors `CommunityCommentSummaryDTO.author_id`'s own nullability exactly;
see that DTO's own docstring in `application/dto.py` for the "Anonymous
Comments"/"Anonymous Replies" reasoning this schema simply passes through
unchanged.

`CreateCommentRequest` has no `target_type`/`target_id` fields — the
router takes them as query parameters instead (mirroring
`app.modules.community_answers.presentation.schemas.CreateAnswerRequest`'s
own `question_id`-as-query-param precedent); `CreateReplyRequest` has no
`parent_comment_id` field at all — the router takes it from the URL path
(`POST /community-comments/{comment_id}/replies`).
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.community_comments.domain.enums import CommentStatus, CommentTargetType
from app.schemas.base import ORJSONModel


class CommentResponse(ORJSONModel):
    id: UUID
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


class CommentFeedResponse(ORJSONModel):
    items: list[CommentResponse]
    next_cursor: str | None = None


class CommentSearchResponse(ORJSONModel):
    items: list[CommentResponse]
    next_cursor: str | None = None


class ThreadResponse(ORJSONModel):
    items: list[CommentResponse]


class CreateCommentRequest(ORJSONModel):
    body: str = Field(min_length=1)
    is_anonymous: bool = False


class CreateReplyRequest(ORJSONModel):
    body: str = Field(min_length=1)
    is_anonymous: bool = False


class UpdateCommentRequest(ORJSONModel):
    body: str | None = Field(default=None, min_length=1)


# --- Comment revisions ----------------------------------------------------------


class CommentRevisionResponse(ORJSONModel):
    id: UUID
    comment_id: UUID
    revision_number: int
    previous_body: str
    author_id: UUID
    created_at: datetime


# --- Comment attachments ---------------------------------------------------------


class CommentAttachmentResponse(ORJSONModel):
    id: UUID
    comment_id: UUID
    document_id: UUID


class AddCommentAttachmentRequest(ORJSONModel):
    document_id: UUID
