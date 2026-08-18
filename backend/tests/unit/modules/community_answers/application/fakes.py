"""In-memory test doubles for the Community Answers module's
repositories, Unit of Work, and the three cross-module query ports it
depends on (`CommunityQueryPort`/`QuestionQueryPort`/`DocumentQueryPort`)
— each implements the exact same interface its real counterpart does,
per `docs/backend-architecture/12_testing_architecture.md` ("fakes over
mocks as the default"). Application-layer service tests depend on these,
never on a real database or a real peer module.
"""

import base64
from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from app.modules.community.public.dto import (
    CommunityMemberStatus,
    CommunityMemberSummaryDTO,
    CommunityRole,
    CommunitySummaryDTO,
)
from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_answers.domain.entities import (
    CommunityAnswer,
    CommunityAnswerAttachment,
    CommunityAnswerRevision,
)
from app.modules.community_answers.domain.enums import AnswerStatus, AnswerVisibility
from app.modules.community_answers.domain.repositories import (
    CommunityAnswerAttachmentRepository,
    CommunityAnswerRepository,
    CommunityAnswerRevisionRepository,
)
from app.modules.community_questions.public.dto import (
    CommunityQuestionSummaryDTO,
    QuestionStatus,
    QuestionType,
    QuestionVisibility,
)
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from app.modules.documents.public.dto import MedicalDocumentSummaryDTO
from app.modules.documents.public.interfaces import DocumentQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent

_CURSOR_SEPARATOR = "|"


def _encode_cursor(published_at: datetime, answer_id: UUID) -> str:
    payload = f"{published_at.isoformat()}{_CURSOR_SEPARATOR}{answer_id}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    payload = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    published_at_raw, answer_id_raw = payload.split(_CURSOR_SEPARATOR, 1)
    return datetime.fromisoformat(published_at_raw), UUID(answer_id_raw)


def make_member_summary(**overrides: object) -> CommunityMemberSummaryDTO:
    defaults: dict[str, object] = {
        "member_id": uuid4(),
        "community_id": uuid4(),
        "user_id": uuid4(),
        "role": CommunityRole.MEMBER,
        "status": CommunityMemberStatus.ACTIVE,
        "joined_at": datetime.now().astimezone(),
    }
    defaults.update(overrides)
    return CommunityMemberSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_question_summary(**overrides: object) -> CommunityQuestionSummaryDTO:
    now = datetime.now().astimezone()
    defaults: dict[str, object] = {
        "question_id": uuid4(),
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "author_id": uuid4(),
        "primary_topic_id": uuid4(),
        "slug": "how-to-manage-hypertension",
        "title": "How to manage hypertension?",
        "body": "Body text.",
        "summary": "Summary text.",
        "question_type": QuestionType.GENERAL,
        "status": QuestionStatus.PUBLISHED,
        "visibility": QuestionVisibility.PUBLIC,
        "is_anonymous": False,
        "is_pinned": False,
        "is_featured": False,
        "read_time_minutes": 1,
        "view_count": 0,
        "follower_count": 0,
        "bookmark_count": 0,
        "share_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return CommunityQuestionSummaryDTO(**defaults)  # type: ignore[arg-type]


class FakeCommunityQueryPort(CommunityQueryPort):
    def __init__(self) -> None:
        self._memberships: dict[tuple[UUID, UUID], CommunityMemberSummaryDTO] = {}

    def add_membership(self, summary: CommunityMemberSummaryDTO) -> None:
        self._memberships[(summary.community_id, summary.user_id)] = summary

    async def community_exists(self, community_id: UUID) -> bool:
        return any(key[0] == community_id for key in self._memberships)

    async def get_community_summary(self, community_id: UUID) -> CommunitySummaryDTO | None:
        return None

    async def get_membership(
        self, community_id: UUID, user_id: UUID
    ) -> CommunityMemberSummaryDTO | None:
        return self._memberships.get((community_id, user_id))

    async def is_active_member(self, community_id: UUID, user_id: UUID) -> bool:
        member = self._memberships.get((community_id, user_id))
        return member is not None and member.status is CommunityMemberStatus.ACTIVE


class FakeQuestionQueryPort(QuestionQueryPort):
    def __init__(self) -> None:
        self._summaries: dict[UUID, CommunityQuestionSummaryDTO] = {}

    def add_question(self, summary: CommunityQuestionSummaryDTO) -> None:
        self._summaries[summary.question_id] = summary

    async def question_exists(self, question_id: UUID) -> bool:
        return question_id in self._summaries

    async def get_question_summary(self, question_id: UUID) -> CommunityQuestionSummaryDTO | None:
        return self._summaries.get(question_id)


class FakeDocumentQueryPort(DocumentQueryPort):
    def __init__(self) -> None:
        self._document_ids: set[UUID] = set()

    def add_document(self, document_id: UUID) -> None:
        self._document_ids.add(document_id)

    async def document_exists(self, document_id: UUID) -> bool:
        return document_id in self._document_ids

    async def get_document_summary(self, document_id: UUID) -> MedicalDocumentSummaryDTO | None:
        return None

    async def list_documents_for_patient(self, patient_id: UUID) -> list[MedicalDocumentSummaryDTO]:
        return []

    async def list_documents_for_visit(self, visit_id: UUID) -> list[MedicalDocumentSummaryDTO]:
        return []

    async def list_documents_for_appointment(
        self, appointment_id: UUID
    ) -> list[MedicalDocumentSummaryDTO]:
        return []


class FakeCommunityAnswerRepository(CommunityAnswerRepository):
    def __init__(self) -> None:
        self._answers: dict[UUID, CommunityAnswer] = {}

    async def get_by_id(self, answer_id: UUID) -> CommunityAnswer | None:
        return self._answers.get(answer_id)

    async def get_best_answer_for_question(self, question_id: UUID) -> CommunityAnswer | None:
        for answer in self._answers.values():
            if answer.question_id == question_id and answer.is_best_answer:
                return answer
        return None

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
        matches = [a for a in self._answers.values() if a.organization_id == organization_id]
        if not include_deleted:
            matches = [a for a in matches if a.status is not AnswerStatus.DELETED]
        if question_id is not None:
            matches = [a for a in matches if a.question_id == question_id]
        if community_id is not None:
            matches = [a for a in matches if a.community_id == community_id]
        if topic_id is not None:
            matches = [a for a in matches if a.topic_id == topic_id]
        if author_id is not None:
            matches = [a for a in matches if a.author_id == author_id]
        if status:
            matches = [a for a in matches if a.status in status]
        if visibility:
            matches = [a for a in matches if a.visibility in visibility]
        if best_answer_only:
            matches = [a for a in matches if a.is_best_answer]
        if featured_only:
            matches = [a for a in matches if a.is_featured]
        if pinned_only:
            matches = [a for a in matches if a.is_pinned]
        if created_from is not None:
            matches = [a for a in matches if a.created_at >= created_from]
        if created_to is not None:
            matches = [a for a in matches if a.created_at <= created_to]
        if query:
            term = query.strip().lower()
            matches = [
                a for a in matches if term in str(a.body).lower() or term in str(a.summary).lower()
            ]
        matches.sort(key=lambda a: getattr(a, sort_by, a.created_at), reverse=sort_order == "desc")
        total = len(matches)
        return matches[offset : offset + limit], total

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
        matches = [
            a
            for a in self._answers.values()
            if a.organization_id == organization_id and a.status is AnswerStatus.PUBLISHED
        ]
        if question_id is not None:
            matches = [a for a in matches if a.question_id == question_id]
        if community_id is not None:
            matches = [a for a in matches if a.community_id == community_id]
        if author_id is not None:
            matches = [a for a in matches if a.author_id == author_id]

        pinned_models: list[CommunityAnswer] = []
        if pinned_first and cursor is None:
            pinned_models = sorted(
                (a for a in matches if a.is_pinned),
                key=lambda a: (a.published_at, a.id),
                reverse=True,
            )

        remaining = limit - len(pinned_models)
        regular_models: list[CommunityAnswer] = []
        regular_has_more = False
        if remaining > 0:
            regular_candidates = matches
            if pinned_first:
                regular_candidates = [a for a in regular_candidates if not a.is_pinned]
            if cursor is not None:
                cursor_published_at, cursor_id = _decode_cursor(cursor)
                regular_candidates = [
                    a
                    for a in regular_candidates
                    if a.published_at is not None
                    and (a.published_at, a.id) < (cursor_published_at, cursor_id)
                ]
            regular_candidates = sorted(
                regular_candidates, key=lambda a: (a.published_at, a.id), reverse=True
            )
            regular_has_more = len(regular_candidates) > remaining
            regular_models = regular_candidates[:remaining]

        page = [*pinned_models, *regular_models]
        next_cursor = None
        if regular_has_more and regular_models:
            last = regular_models[-1]
            assert last.published_at is not None
            next_cursor = _encode_cursor(last.published_at, last.id)

        return page, next_cursor

    async def add(self, answer: CommunityAnswer) -> None:
        self._answers[answer.id] = answer


class FakeCommunityAnswerRevisionRepository(CommunityAnswerRevisionRepository):
    """No `remove()` seam — matches `CommunityAnswerRevisionRepository`'s
    own docstring: revision history is immutable, full stop."""

    def __init__(self) -> None:
        self._revisions: dict[UUID, CommunityAnswerRevision] = {}

    async def get_by_id(self, revision_id: UUID) -> CommunityAnswerRevision | None:
        return self._revisions.get(revision_id)

    async def list_by_answer(
        self, answer_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[CommunityAnswerRevision]:
        matches = [r for r in self._revisions.values() if r.answer_id.value == answer_id]
        matches.sort(key=lambda r: r.revision_number, reverse=True)
        return matches[offset : offset + limit]

    async def add(self, revision: CommunityAnswerRevision) -> None:
        self._revisions[revision.id] = revision


class FakeCommunityAnswerAttachmentRepository(CommunityAnswerAttachmentRepository):
    def __init__(self) -> None:
        self._attachments: dict[UUID, CommunityAnswerAttachment] = {}

    async def get_by_id(self, attachment_id: UUID) -> CommunityAnswerAttachment | None:
        return self._attachments.get(attachment_id)

    async def list_by_answer(self, answer_id: UUID) -> list[CommunityAnswerAttachment]:
        return [a for a in self._attachments.values() if a.answer_id.value == answer_id]

    async def is_assigned(self, answer_id: UUID, document_id: UUID) -> bool:
        return any(
            a.answer_id.value == answer_id and a.document_id == document_id
            for a in self._attachments.values()
        )

    async def add(self, attachment: CommunityAnswerAttachment) -> None:
        self._attachments[attachment.id] = attachment

    async def remove(self, attachment_id: UUID) -> None:
        self._attachments.pop(attachment_id, None)


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.published_events: list[DomainEvent] = []
        self._pending_events: list[DomainEvent] = []

    def collect_events(self, events: list[DomainEvent]) -> None:
        self._pending_events.extend(events)

    async def commit(self) -> None:
        self.committed = True
        self.published_events.extend(self._pending_events)
        self._pending_events = []

    async def rollback(self) -> None:
        self.rolled_back = True
        self._pending_events = []

    async def flush(self) -> None:
        pass
