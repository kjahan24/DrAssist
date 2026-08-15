"""Data Transfer Objects for the Community Questions module's application
layer.

Distinct from both domain entities (never leave the module) and API
schemas (`presentation/schemas.py`, the Pydantic v2 validation boundary).
Use-case input/output DTOs are plain, immutable dataclasses — the same
shape `app.modules.community_posts.application.dto` already establishes;
`CommunityQuestionSummaryDTO` is also re-exported from `public/dto.py`
for other modules to depend on.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.community_questions.domain.enums import (
    QuestionStatus,
    QuestionType,
    QuestionVisibility,
)

# --- CreateQuestion --------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateQuestionInput:
    community_id: UUID
    author_id: UUID
    primary_topic_id: UUID
    title: str
    body: str
    slug: str | None = None
    summary: str | None = None
    question_type: QuestionType = QuestionType.GENERAL
    visibility: QuestionVisibility = QuestionVisibility.PUBLIC
    is_anonymous: bool = False
    secondary_topic_ids: tuple[UUID, ...] = ()
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CreateQuestionOutput:
    question_id: UUID
    community_id: UUID
    slug: str
    title: str
    status: QuestionStatus


# --- UpdateQuestion --------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UpdateQuestionInput:
    question_id: UUID
    acting_user_id: UUID
    title: str | None = None
    body: str | None = None
    summary: str | None = None
    regenerate_summary: bool = False
    question_type: QuestionType | None = None
    visibility: QuestionVisibility | None = None
    is_anonymous: bool | None = None


@dataclass(frozen=True, slots=True)
class UpdateQuestionOutput:
    question_id: UUID
    title: str
    status: QuestionStatus
    visibility: QuestionVisibility


# --- DeleteQuestion / lifecycle actions -------------------------------------------


@dataclass(frozen=True, slots=True)
class DeleteQuestionInput:
    question_id: UUID
    acting_user_id: UUID


@dataclass(frozen=True, slots=True)
class PublishQuestionInput:
    question_id: UUID
    acting_user_id: UUID


@dataclass(frozen=True, slots=True)
class ArchiveQuestionInput:
    question_id: UUID
    acting_user_id: UUID


@dataclass(frozen=True, slots=True)
class CloseQuestionInput:
    question_id: UUID
    acting_user_id: UUID


@dataclass(frozen=True, slots=True)
class ReopenQuestionInput:
    question_id: UUID
    acting_user_id: UUID


# --- PinQuestion / FeatureQuestion (moderator-only toggles) -----------------------


@dataclass(frozen=True, slots=True)
class SetQuestionPinnedInput:
    question_id: UUID
    acting_user_id: UUID
    pinned: bool


@dataclass(frozen=True, slots=True)
class SetQuestionFeaturedInput:
    question_id: UUID
    acting_user_id: UUID
    featured: bool


# --- Cross-cutting read models (also re-exported via public/dto.py) --------------


@dataclass(frozen=True, slots=True)
class CommunityQuestionSummaryDTO:
    question_id: UUID
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

    @property
    def id(self) -> UUID:
        """Alias for `question_id` — see `CommunityPostSummaryDTO.id`'s
        own docstring for the full reasoning (identical situation in
        every module)."""
        return self.question_id


# --- ListQuestions / SearchQuestions (offset-paged, full-filter) -----------------


@dataclass(frozen=True, slots=True)
class ListQuestionsInput:
    organization_id: UUID
    community_id: UUID | None = None
    topic_id: UUID | None = None
    author_id: UUID | None = None
    question_type: tuple[QuestionType, ...] | None = None
    status: tuple[QuestionStatus, ...] | None = None
    visibility: tuple[QuestionVisibility, ...] | None = None
    pinned_only: bool = False
    featured_only: bool = False
    created_from: datetime | None = None
    created_to: datetime | None = None
    query: str | None = None
    include_deleted: bool = False
    sort_by: str = "created_at"
    sort_order: str = "desc"
    offset: int = 0
    limit: int = 20


@dataclass(frozen=True, slots=True)
class ListQuestionsOutput:
    items: tuple[CommunityQuestionSummaryDTO, ...]
    total: int


@dataclass(frozen=True, slots=True)
class SearchQuestionsInput:
    organization_id: UUID
    query: str
    community_id: UUID | None = None
    topic_id: UUID | None = None
    author_id: UUID | None = None
    question_type: tuple[QuestionType, ...] | None = None
    status: tuple[QuestionStatus, ...] | None = None
    visibility: tuple[QuestionVisibility, ...] | None = None
    pinned_only: bool = False
    featured_only: bool = False
    created_from: datetime | None = None
    created_to: datetime | None = None
    offset: int = 0
    limit: int = 20


@dataclass(frozen=True, slots=True)
class SearchQuestionsOutput:
    items: tuple[CommunityQuestionSummaryDTO, ...]
    total: int


# --- Browse*Questions (cursor-paged) ----------------------------------------------


@dataclass(frozen=True, slots=True)
class BrowseCommunityQuestionsInput:
    community_id: UUID
    cursor: str | None = None
    limit: int = 20


@dataclass(frozen=True, slots=True)
class BrowseTopicQuestionsInput:
    organization_id: UUID
    topic_id: UUID
    cursor: str | None = None
    limit: int = 20


@dataclass(frozen=True, slots=True)
class BrowseAuthorQuestionsInput:
    organization_id: UUID
    author_id: UUID
    cursor: str | None = None
    limit: int = 20


@dataclass(frozen=True, slots=True)
class QuestionFeedOutput:
    items: tuple[CommunityQuestionSummaryDTO, ...]
    next_cursor: str | None = None


# --- Question topics (secondary) --------------------------------------------------


@dataclass(frozen=True, slots=True)
class QuestionTopicSummaryDTO:
    question_topic_id: UUID
    question_id: UUID
    topic_id: UUID

    @property
    def id(self) -> UUID:
        return self.question_topic_id


@dataclass(frozen=True, slots=True)
class AssignQuestionTopicInput:
    question_id: UUID
    acting_user_id: UUID
    topic_id: UUID


@dataclass(frozen=True, slots=True)
class UnassignQuestionTopicInput:
    question_id: UUID
    acting_user_id: UUID
    question_topic_id: UUID


# --- Question tags -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class QuestionTagSummaryDTO:
    question_tag_id: UUID
    question_id: UUID
    tag: str

    @property
    def id(self) -> UUID:
        return self.question_tag_id


@dataclass(frozen=True, slots=True)
class AssignQuestionTagInput:
    question_id: UUID
    acting_user_id: UUID
    tag: str


@dataclass(frozen=True, slots=True)
class UnassignQuestionTagInput:
    question_id: UUID
    acting_user_id: UUID
    question_tag_id: UUID


# --- Question attachments -----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class QuestionAttachmentSummaryDTO:
    attachment_id: UUID
    question_id: UUID
    document_id: UUID

    @property
    def id(self) -> UUID:
        return self.attachment_id


@dataclass(frozen=True, slots=True)
class AddQuestionAttachmentInput:
    question_id: UUID
    acting_user_id: UUID
    document_id: UUID


@dataclass(frozen=True, slots=True)
class RemoveQuestionAttachmentInput:
    question_id: UUID
    acting_user_id: UUID
    attachment_id: UUID


# --- Question followers -----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class QuestionFollowerSummaryDTO:
    follower_id: UUID
    question_id: UUID
    user_id: UUID

    @property
    def id(self) -> UUID:
        return self.follower_id


@dataclass(frozen=True, slots=True)
class FollowQuestionInput:
    question_id: UUID
    acting_user_id: UUID


@dataclass(frozen=True, slots=True)
class UnfollowQuestionInput:
    question_id: UUID
    acting_user_id: UUID
