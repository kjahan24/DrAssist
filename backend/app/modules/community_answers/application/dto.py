"""Data Transfer Objects for the Community Answers module's application
layer.

Distinct from both domain entities (never leave the module) and API
schemas (`presentation/schemas.py`, the Pydantic v2 validation boundary).
Use-case input/output DTOs are plain, immutable dataclasses — the same
shape `app.modules.community_questions.application.dto` already
establishes; `CommunityAnswerSummaryDTO` is also re-exported from
`public/dto.py` for other modules to depend on.

`CommunityAnswerSummaryDTO.author_id` is `UUID | None`, not a mandatory
`UUID` — see `_summary_mappers.answer_to_summary`'s own docstring for why:
this task's own DOMAIN section requires "Anonymous identity must remain
hidden through the public API," so the mapper unconditionally sets this
field to `None` whenever the source `CommunityAnswer.is_anonymous` is
`True`, in every read path (`GetAnswer`/`ListAnswers`/`SearchAnswers`/
the cursor feeds), with no viewer-aware exception even for the answer's
own author or a moderator — the simplest, safest reading of "must remain
hidden through the public API." The stored entity's own `author_id`
stays intact for authorization purposes (`UpdateAnswerService` etc. read
it directly off the domain entity, never off this masked DTO).
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.community_answers.domain.enums import AnswerStatus, AnswerVisibility

# --- CreateAnswer ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateAnswerInput:
    question_id: UUID
    author_id: UUID
    body: str
    summary: str | None = None
    visibility: AnswerVisibility = AnswerVisibility.PUBLIC
    is_anonymous: bool = False


@dataclass(frozen=True, slots=True)
class CreateAnswerOutput:
    answer_id: UUID
    question_id: UUID
    status: AnswerStatus


# --- UpdateAnswer ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UpdateAnswerInput:
    answer_id: UUID
    acting_user_id: UUID
    body: str | None = None
    summary: str | None = None
    regenerate_summary: bool = False


@dataclass(frozen=True, slots=True)
class UpdateAnswerOutput:
    answer_id: UUID
    status: AnswerStatus
    revision_number: int


# --- DeleteAnswer / lifecycle actions ------------------------------------------------


@dataclass(frozen=True, slots=True)
class DeleteAnswerInput:
    answer_id: UUID
    acting_user_id: UUID


@dataclass(frozen=True, slots=True)
class PublishAnswerInput:
    answer_id: UUID
    acting_user_id: UUID


@dataclass(frozen=True, slots=True)
class ArchiveAnswerInput:
    answer_id: UUID
    acting_user_id: UUID


@dataclass(frozen=True, slots=True)
class RestoreAnswerInput:
    answer_id: UUID
    acting_user_id: UUID


# --- Best answer -------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MarkBestAnswerInput:
    question_id: UUID
    answer_id: UUID
    acting_user_id: UUID


@dataclass(frozen=True, slots=True)
class RemoveBestAnswerInput:
    question_id: UUID
    answer_id: UUID
    acting_user_id: UUID


# --- FeatureAnswer / PinAnswer (moderator-only toggles) ------------------------------


@dataclass(frozen=True, slots=True)
class SetAnswerFeaturedInput:
    answer_id: UUID
    acting_user_id: UUID
    featured: bool


@dataclass(frozen=True, slots=True)
class SetAnswerPinnedInput:
    answer_id: UUID
    acting_user_id: UUID
    pinned: bool


# --- Cross-cutting read models (also re-exported via public/dto.py) ------------------


@dataclass(frozen=True, slots=True)
class CommunityAnswerSummaryDTO:
    answer_id: UUID
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

    @property
    def id(self) -> UUID:
        """Alias for `answer_id` — see `CommunityQuestionSummaryDTO.id`'s
        own docstring for the full reasoning (identical situation in
        every module)."""
        return self.answer_id


# --- ListAnswers / SearchAnswers (offset-paged, full-filter) -------------------------


@dataclass(frozen=True, slots=True)
class ListAnswersInput:
    organization_id: UUID
    question_id: UUID | None = None
    community_id: UUID | None = None
    topic_id: UUID | None = None
    author_id: UUID | None = None
    status: tuple[AnswerStatus, ...] | None = None
    visibility: tuple[AnswerVisibility, ...] | None = None
    best_answer_only: bool = False
    featured_only: bool = False
    pinned_only: bool = False
    created_from: datetime | None = None
    created_to: datetime | None = None
    query: str | None = None
    include_deleted: bool = False
    sort_by: str = "created_at"
    sort_order: str = "desc"
    offset: int = 0
    limit: int = 20


@dataclass(frozen=True, slots=True)
class ListAnswersOutput:
    items: tuple[CommunityAnswerSummaryDTO, ...]
    total: int


@dataclass(frozen=True, slots=True)
class SearchAnswersInput:
    organization_id: UUID
    query: str
    question_id: UUID | None = None
    community_id: UUID | None = None
    topic_id: UUID | None = None
    author_id: UUID | None = None
    status: tuple[AnswerStatus, ...] | None = None
    visibility: tuple[AnswerVisibility, ...] | None = None
    best_answer_only: bool = False
    featured_only: bool = False
    pinned_only: bool = False
    created_from: datetime | None = None
    created_to: datetime | None = None
    offset: int = 0
    limit: int = 20


@dataclass(frozen=True, slots=True)
class SearchAnswersOutput:
    items: tuple[CommunityAnswerSummaryDTO, ...]
    total: int


# --- ListQuestionAnswers / ListAuthorAnswers (cursor-paged) --------------------------


@dataclass(frozen=True, slots=True)
class ListQuestionAnswersInput:
    organization_id: UUID
    question_id: UUID
    cursor: str | None = None
    limit: int = 20


@dataclass(frozen=True, slots=True)
class ListAuthorAnswersInput:
    organization_id: UUID
    author_id: UUID
    cursor: str | None = None
    limit: int = 20


@dataclass(frozen=True, slots=True)
class AnswerFeedOutput:
    items: tuple[CommunityAnswerSummaryDTO, ...]
    next_cursor: str | None = None


# --- Answer revisions ----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AnswerRevisionSummaryDTO:
    revision_id: UUID
    answer_id: UUID
    revision_number: int
    previous_body: str
    author_id: UUID
    created_at: datetime

    @property
    def id(self) -> UUID:
        return self.revision_id


# --- Answer attachments ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AnswerAttachmentSummaryDTO:
    attachment_id: UUID
    answer_id: UUID
    document_id: UUID

    @property
    def id(self) -> UUID:
        return self.attachment_id


@dataclass(frozen=True, slots=True)
class AddAnswerAttachmentInput:
    answer_id: UUID
    acting_user_id: UUID
    document_id: UUID


@dataclass(frozen=True, slots=True)
class RemoveAnswerAttachmentInput:
    answer_id: UUID
    acting_user_id: UUID
    attachment_id: UUID
