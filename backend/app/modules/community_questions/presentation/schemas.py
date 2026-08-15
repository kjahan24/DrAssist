"""Pydantic v2 request/response schemas for the Community Questions
module.

Schemas never expose a domain entity directly, and never accept
server-controlled fields (`id`, `author_id`, ...) from the client — see
`docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention).
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.community_questions.domain.enums import (
    QuestionStatus,
    QuestionType,
    QuestionVisibility,
)
from app.schemas.base import ORJSONModel

_SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class QuestionResponse(ORJSONModel):
    id: UUID
    community_id: UUID
    organization_id: UUID
    author_id: UUID
    primary_topic_id: UUID
    slug: str
    title: str
    body: str
    summary: str
    question_type: QuestionType
    status: QuestionStatus
    visibility: QuestionVisibility
    is_anonymous: bool
    is_pinned: bool
    is_featured: bool
    read_time_minutes: int
    view_count: int
    follower_count: int
    bookmark_count: int
    share_count: int
    created_at: datetime
    updated_at: datetime
    accepted_answer_id: UUID | None = None
    published_at: datetime | None = None
    updated_by: UUID | None = None


class QuestionSearchResponse(ORJSONModel):
    items: list[QuestionResponse]
    total: int


class QuestionFeedResponse(ORJSONModel):
    items: list[QuestionResponse]
    next_cursor: str | None = None


class CreateQuestionRequest(ORJSONModel):
    primary_topic_id: UUID
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1)
    slug: str | None = Field(default=None, min_length=3, max_length=100, pattern=_SLUG_PATTERN)
    summary: str | None = Field(default=None, max_length=500)
    question_type: QuestionType = QuestionType.GENERAL
    visibility: QuestionVisibility = QuestionVisibility.PUBLIC
    is_anonymous: bool = False
    secondary_topic_ids: list[UUID] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class UpdateQuestionRequest(ORJSONModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    body: str | None = Field(default=None, min_length=1)
    summary: str | None = Field(default=None, max_length=500)
    regenerate_summary: bool = False
    question_type: QuestionType | None = None
    visibility: QuestionVisibility | None = None
    is_anonymous: bool | None = None


class SetQuestionPinnedRequest(ORJSONModel):
    pinned: bool


class SetQuestionFeaturedRequest(ORJSONModel):
    featured: bool


# --- Question topics (secondary) ------------------------------------------------------


class QuestionTopicResponse(ORJSONModel):
    id: UUID
    question_id: UUID
    topic_id: UUID


class AssignQuestionTopicRequest(ORJSONModel):
    topic_id: UUID


# --- Question tags -----------------------------------------------------------------------


class QuestionTagResponse(ORJSONModel):
    id: UUID
    question_id: UUID
    tag: str


class AssignQuestionTagRequest(ORJSONModel):
    tag: str = Field(min_length=1, max_length=50)


# --- Question attachments -----------------------------------------------------------------


class QuestionAttachmentResponse(ORJSONModel):
    id: UUID
    question_id: UUID
    document_id: UUID


class AddQuestionAttachmentRequest(ORJSONModel):
    document_id: UUID


# --- Question followers -------------------------------------------------------------------


class QuestionFollowerResponse(ORJSONModel):
    id: UUID
    question_id: UUID
    user_id: UUID
