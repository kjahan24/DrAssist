"""In-memory test doubles for the Community Questions module's
repositories, Unit of Work, and the three cross-module query ports it
depends on (`CommunityQueryPort`/`TopicQueryPort`/`DocumentQueryPort`) —
each implements the exact same interface its real counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer service tests depend on these, never
on a real database or a real peer module.
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
    CommunityVisibility,
)
from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_questions.domain.entities import (
    CommunityQuestion,
    CommunityQuestionAttachment,
    CommunityQuestionFollower,
    CommunityQuestionTag,
    CommunityQuestionTopic,
)
from app.modules.community_questions.domain.enums import (
    QuestionStatus,
    QuestionType,
    QuestionVisibility,
)
from app.modules.community_questions.domain.repositories import (
    CommunityQuestionAttachmentRepository,
    CommunityQuestionFollowerRepository,
    CommunityQuestionRepository,
    CommunityQuestionTagRepository,
    CommunityQuestionTopicRepository,
)
from app.modules.documents.public.dto import MedicalDocumentSummaryDTO
from app.modules.documents.public.interfaces import DocumentQueryPort
from app.modules.medical_topics.public.dto import TopicSummaryDTO
from app.modules.medical_topics.public.interfaces import TopicQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent

_CURSOR_SEPARATOR = "|"
_LIVE_FEED_STATUSES = (QuestionStatus.PUBLISHED, QuestionStatus.CLOSED)


def _encode_cursor(published_at: datetime, question_id: UUID) -> str:
    payload = f"{published_at.isoformat()}{_CURSOR_SEPARATOR}{question_id}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    payload = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    published_at_raw, question_id_raw = payload.split(_CURSOR_SEPARATOR, 1)
    return datetime.fromisoformat(published_at_raw), UUID(question_id_raw)


def make_community_summary(**overrides: object) -> CommunitySummaryDTO:
    now = datetime.now().astimezone()
    defaults: dict[str, object] = {
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "slug": "oncology",
        "name": "Oncology",
        "visibility": CommunityVisibility.PUBLIC,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return CommunitySummaryDTO(**defaults)  # type: ignore[arg-type]


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


class FakeCommunityQueryPort(CommunityQueryPort):
    def __init__(self) -> None:
        self._communities: dict[UUID, CommunitySummaryDTO] = {}
        self._memberships: dict[tuple[UUID, UUID], CommunityMemberSummaryDTO] = {}

    def add_community(self, summary: CommunitySummaryDTO) -> None:
        self._communities[summary.community_id] = summary

    def add_membership(self, summary: CommunityMemberSummaryDTO) -> None:
        self._memberships[(summary.community_id, summary.user_id)] = summary

    async def community_exists(self, community_id: UUID) -> bool:
        return community_id in self._communities

    async def get_community_summary(self, community_id: UUID) -> CommunitySummaryDTO | None:
        return self._communities.get(community_id)

    async def get_membership(
        self, community_id: UUID, user_id: UUID
    ) -> CommunityMemberSummaryDTO | None:
        return self._memberships.get((community_id, user_id))

    async def is_active_member(self, community_id: UUID, user_id: UUID) -> bool:
        member = self._memberships.get((community_id, user_id))
        return member is not None and member.status is CommunityMemberStatus.ACTIVE


class FakeTopicQueryPort(TopicQueryPort):
    def __init__(self) -> None:
        self._topic_ids: set[UUID] = set()
        self._summaries: dict[UUID, TopicSummaryDTO] = {}

    def add_topic(self, topic_id: UUID) -> None:
        self._topic_ids.add(topic_id)

    async def topic_exists(self, topic_id: UUID) -> bool:
        return topic_id in self._topic_ids

    async def get_topic_summary(self, topic_id: UUID) -> TopicSummaryDTO | None:
        return self._summaries.get(topic_id)

    async def get_topic_summary_by_slug(self, slug: str) -> TopicSummaryDTO | None:
        return next((s for s in self._summaries.values() if s.slug == slug), None)


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


class FakeCommunityQuestionRepository(CommunityQuestionRepository):
    def __init__(self) -> None:
        self._questions: dict[UUID, CommunityQuestion] = {}
        self._secondary_topic_assignments: dict[UUID, set[UUID]] = {}

    def assign_topic_for_search(self, question_id: UUID, topic_id: UUID) -> None:
        """Test-only seam backing the `topic_id` filter's *secondary*
        half — the real repository joins against
        `community_question_topics`; this fake tracks assignments
        directly, the same pattern
        `FakeCommunityPostRepository.assign_topic_for_search` already
        establishes."""
        self._secondary_topic_assignments.setdefault(question_id, set()).add(topic_id)

    def _matches_topic(self, question: CommunityQuestion, topic_id: UUID) -> bool:
        return question.primary_topic_id == topic_id or topic_id in (
            self._secondary_topic_assignments.get(question.id, set())
        )

    async def get_by_id(self, question_id: UUID) -> CommunityQuestion | None:
        return self._questions.get(question_id)

    async def get_by_slug(self, community_id: UUID, slug: str) -> CommunityQuestion | None:
        normalized = slug.strip().lower()
        for question in self._questions.values():
            if question.community_id == community_id and str(question.slug) == normalized:
                return question
        return None

    async def search(
        self,
        *,
        organization_id: UUID,
        community_id: UUID | None = None,
        topic_id: UUID | None = None,
        author_id: UUID | None = None,
        question_type: Sequence[QuestionType] | None = None,
        status: Sequence[QuestionStatus] | None = None,
        visibility: Sequence[QuestionVisibility] | None = None,
        pinned_only: bool = False,
        featured_only: bool = False,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        query: str | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[CommunityQuestion], int]:
        matches = [q for q in self._questions.values() if q.organization_id == organization_id]
        if not include_deleted:
            matches = [q for q in matches if q.status is not QuestionStatus.DELETED]
        if community_id is not None:
            matches = [q for q in matches if q.community_id == community_id]
        if author_id is not None:
            matches = [q for q in matches if q.author_id == author_id]
        if topic_id is not None:
            matches = [q for q in matches if self._matches_topic(q, topic_id)]
        if question_type:
            matches = [q for q in matches if q.question_type in question_type]
        if status:
            matches = [q for q in matches if q.status in status]
        if visibility:
            matches = [q for q in matches if q.visibility in visibility]
        if pinned_only:
            matches = [q for q in matches if q.is_pinned]
        if featured_only:
            matches = [q for q in matches if q.is_featured]
        if created_from is not None:
            matches = [q for q in matches if q.created_at >= created_from]
        if created_to is not None:
            matches = [q for q in matches if q.created_at <= created_to]
        if query:
            term = query.strip().lower()
            matches = [
                q
                for q in matches
                if term in str(q.title).lower()
                or term in q.body.lower()
                or term in str(q.summary).lower()
            ]
        matches.sort(key=lambda q: getattr(q, sort_by, q.created_at), reverse=sort_order == "desc")
        total = len(matches)
        return matches[offset : offset + limit], total

    async def browse_feed(
        self,
        *,
        organization_id: UUID,
        community_id: UUID | None = None,
        topic_id: UUID | None = None,
        author_id: UUID | None = None,
        pinned_first: bool = False,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[Sequence[CommunityQuestion], str | None]:
        matches = [
            q
            for q in self._questions.values()
            if q.organization_id == organization_id and q.status in _LIVE_FEED_STATUSES
        ]
        if community_id is not None:
            matches = [q for q in matches if q.community_id == community_id]
        if author_id is not None:
            matches = [q for q in matches if q.author_id == author_id]
        if topic_id is not None:
            matches = [q for q in matches if self._matches_topic(q, topic_id)]

        pinned_models: list[CommunityQuestion] = []
        if pinned_first and cursor is None:
            pinned_models = sorted(
                (q for q in matches if q.is_pinned),
                key=lambda q: (q.published_at, q.id),
                reverse=True,
            )

        remaining = limit - len(pinned_models)
        regular_models: list[CommunityQuestion] = []
        regular_has_more = False
        if remaining > 0:
            regular_candidates = matches
            if pinned_first:
                regular_candidates = [q for q in regular_candidates if not q.is_pinned]
            if cursor is not None:
                cursor_published_at, cursor_id = _decode_cursor(cursor)
                regular_candidates = [
                    q
                    for q in regular_candidates
                    if q.published_at is not None
                    and (q.published_at, q.id) < (cursor_published_at, cursor_id)
                ]
            regular_candidates = sorted(
                regular_candidates, key=lambda q: (q.published_at, q.id), reverse=True
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

    async def add(self, question: CommunityQuestion) -> None:
        self._questions[question.id] = question


class FakeCommunityQuestionTopicRepository(CommunityQuestionTopicRepository):
    def __init__(self) -> None:
        self._assignments: dict[UUID, CommunityQuestionTopic] = {}

    async def get_by_id(self, question_topic_id: UUID) -> CommunityQuestionTopic | None:
        return self._assignments.get(question_topic_id)

    async def list_by_question(self, question_id: UUID) -> list[CommunityQuestionTopic]:
        return [a for a in self._assignments.values() if a.question_id.value == question_id]

    async def list_question_ids_by_topic(
        self, topic_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[UUID]:
        matches = [
            a.question_id.value for a in self._assignments.values() if a.topic_id == topic_id
        ]
        return matches[offset : offset + limit]

    async def is_assigned(self, question_id: UUID, topic_id: UUID) -> bool:
        return any(
            a.question_id.value == question_id and a.topic_id == topic_id
            for a in self._assignments.values()
        )

    async def add(self, assignment: CommunityQuestionTopic) -> None:
        self._assignments[assignment.id] = assignment

    async def remove(self, question_topic_id: UUID) -> None:
        self._assignments.pop(question_topic_id, None)


class FakeCommunityQuestionTagRepository(CommunityQuestionTagRepository):
    def __init__(self) -> None:
        self._assignments: dict[UUID, CommunityQuestionTag] = {}

    async def get_by_id(self, question_tag_id: UUID) -> CommunityQuestionTag | None:
        return self._assignments.get(question_tag_id)

    async def list_by_question(self, question_id: UUID) -> list[CommunityQuestionTag]:
        return [a for a in self._assignments.values() if a.question_id.value == question_id]

    async def is_assigned(self, question_id: UUID, tag: str) -> bool:
        normalized = tag.strip().lower()
        return any(
            a.question_id.value == question_id and a.tag == normalized
            for a in self._assignments.values()
        )

    async def add(self, assignment: CommunityQuestionTag) -> None:
        self._assignments[assignment.id] = assignment

    async def remove(self, question_tag_id: UUID) -> None:
        self._assignments.pop(question_tag_id, None)


class FakeCommunityQuestionAttachmentRepository(CommunityQuestionAttachmentRepository):
    def __init__(self) -> None:
        self._attachments: dict[UUID, CommunityQuestionAttachment] = {}

    async def get_by_id(self, attachment_id: UUID) -> CommunityQuestionAttachment | None:
        return self._attachments.get(attachment_id)

    async def list_by_question(self, question_id: UUID) -> list[CommunityQuestionAttachment]:
        return [a for a in self._attachments.values() if a.question_id.value == question_id]

    async def is_assigned(self, question_id: UUID, document_id: UUID) -> bool:
        return any(
            a.question_id.value == question_id and a.document_id == document_id
            for a in self._attachments.values()
        )

    async def add(self, attachment: CommunityQuestionAttachment) -> None:
        self._attachments[attachment.id] = attachment

    async def remove(self, attachment_id: UUID) -> None:
        self._attachments.pop(attachment_id, None)


class FakeCommunityQuestionFollowerRepository(CommunityQuestionFollowerRepository):
    def __init__(self) -> None:
        self._followers: dict[UUID, CommunityQuestionFollower] = {}

    async def get_by_id(self, follower_id: UUID) -> CommunityQuestionFollower | None:
        return self._followers.get(follower_id)

    async def get_by_question_and_user(
        self, question_id: UUID, user_id: UUID
    ) -> CommunityQuestionFollower | None:
        for follower in self._followers.values():
            if follower.question_id.value == question_id and follower.user_id == user_id:
                return follower
        return None

    async def list_by_question(
        self, question_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[CommunityQuestionFollower]:
        matches = [f for f in self._followers.values() if f.question_id.value == question_id]
        return matches[offset : offset + limit]

    async def is_following(self, question_id: UUID, user_id: UUID) -> bool:
        return any(
            f.question_id.value == question_id and f.user_id == user_id
            for f in self._followers.values()
        )

    async def add(self, follower: CommunityQuestionFollower) -> None:
        self._followers[follower.id] = follower

    async def remove(self, follower_id: UUID) -> None:
        self._followers.pop(follower_id, None)


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
