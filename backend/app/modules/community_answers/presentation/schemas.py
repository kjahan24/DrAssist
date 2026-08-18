"""Pydantic v2 request/response schemas for the Community Answers
module.

Schemas never expose a domain entity directly, and never accept
server-controlled fields (`id`, `author_id`, ...) from the client — see
`docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention).

`AnswerResponse.author_id` is `UUID | None`, not a mandatory `UUID` —
mirrors `CommunityAnswerSummaryDTO.author_id`'s own nullability exactly;
see that DTO's own docstring in `application/dto.py` for the "anonymous
identity must remain hidden through the public API" reasoning this
schema simply passes through unchanged.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.community_answers.domain.enums import AnswerStatus, AnswerVisibility
from app.schemas.base import ORJSONModel


class AnswerResponse(ORJSONModel):
    id: UUID
    question_id: UUID
    community_id: UUID
    organization_id: UUID
    topic_id: UUID
    body: str
    summary: str
    status: AnswerStatus
    visibility: AnswerVisibility
    is_anonymous: bool
    is_best_answer: bool
    is_featured: bool
    is_pinned: bool
    view_count: int
    share_count: int
    revision_number: int
    created_at: datetime
    updated_at: datetime
    author_id: UUID | None = None
    published_at: datetime | None = None
    updated_by: UUID | None = None


class AnswerSearchResponse(ORJSONModel):
    items: list[AnswerResponse]
    total: int


class AnswerFeedResponse(ORJSONModel):
    items: list[AnswerResponse]
    next_cursor: str | None = None


class CreateAnswerRequest(ORJSONModel):
    body: str = Field(min_length=1)
    summary: str | None = Field(default=None, max_length=500)
    visibility: AnswerVisibility = AnswerVisibility.PUBLIC
    is_anonymous: bool = False


class UpdateAnswerRequest(ORJSONModel):
    body: str | None = Field(default=None, min_length=1)
    summary: str | None = Field(default=None, max_length=500)
    regenerate_summary: bool = False


class SetAnswerFeaturedRequest(ORJSONModel):
    featured: bool


class SetAnswerPinnedRequest(ORJSONModel):
    pinned: bool


# --- Answer revisions ----------------------------------------------------------------


class AnswerRevisionResponse(ORJSONModel):
    id: UUID
    answer_id: UUID
    revision_number: int
    previous_body: str
    author_id: UUID
    created_at: datetime


# --- Answer attachments ---------------------------------------------------------------


class AnswerAttachmentResponse(ORJSONModel):
    id: UUID
    answer_id: UUID
    document_id: UUID


class AddAnswerAttachmentRequest(ORJSONModel):
    document_id: UUID
