"""In-memory test doubles for the Community Comments module's
repositories, Unit of Work, and the five cross-module query ports it
depends on (`CommunityQueryPort`/`PostQueryPort`/`QuestionQueryPort`/
`AnswerQueryPort`/`DocumentQueryPort`) — each implements the exact same
interface its real counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over
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
from app.modules.community_answers.public.dto import (
    AnswerStatus,
    AnswerVisibility,
    CommunityAnswerSummaryDTO,
)
from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.domain.entities import (
    CommunityComment,
    CommunityCommentAttachment,
    CommunityCommentRevision,
)
from app.modules.community_comments.domain.enums import CommentStatus, CommentTargetType
from app.modules.community_comments.domain.repositories import (
    CommunityCommentAttachmentRepository,
    CommunityCommentRepository,
    CommunityCommentRevisionRepository,
)
from app.modules.community_posts.public.dto import (
    CommunityPostSummaryDTO,
    PostStatus,
    PostType,
    PostVisibility,
)
from app.modules.community_posts.public.interfaces import PostQueryPort
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


def _encode_cursor(created_at: datetime, comment_id: UUID) -> str:
    payload = f"{created_at.isoformat()}{_CURSOR_SEPARATOR}{comment_id}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    payload = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    created_at_raw, comment_id_raw = payload.split(_CURSOR_SEPARATOR, 1)
    return datetime.fromisoformat(created_at_raw), UUID(comment_id_raw)


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


def make_post_summary(**overrides: object) -> CommunityPostSummaryDTO:
    now = datetime.now().astimezone()
    defaults: dict[str, object] = {
        "post_id": uuid4(),
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "author_id": uuid4(),
        "slug": "discussion-post",
        "title": "A discussion post",
        "body": "Body text.",
        "excerpt": "Excerpt.",
        "post_type": PostType.DISCUSSION,
        "status": PostStatus.PUBLISHED,
        "visibility": PostVisibility.PUBLIC,
        "is_anonymous": False,
        "is_pinned": False,
        "is_locked": False,
        "is_featured": False,
        "read_time_minutes": 1,
        "view_count": 0,
        "bookmark_count": 0,
        "share_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return CommunityPostSummaryDTO(**defaults)  # type: ignore[arg-type]


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


def make_answer_summary(**overrides: object) -> CommunityAnswerSummaryDTO:
    now = datetime.now().astimezone()
    defaults: dict[str, object] = {
        "answer_id": uuid4(),
        "question_id": uuid4(),
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "topic_id": uuid4(),
        "body": "Body text.",
        "summary": "Summary text.",
        "status": AnswerStatus.PUBLISHED,
        "visibility": AnswerVisibility.PUBLIC,
        "is_anonymous": False,
        "is_best_answer": False,
        "is_featured": False,
        "is_pinned": False,
        "view_count": 0,
        "share_count": 0,
        "revision_number": 1,
        "created_at": now,
        "updated_at": now,
        "author_id": uuid4(),
    }
    defaults.update(overrides)
    return CommunityAnswerSummaryDTO(**defaults)  # type: ignore[arg-type]


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


class FakePostQueryPort(PostQueryPort):
    def __init__(self) -> None:
        self._summaries: dict[UUID, CommunityPostSummaryDTO] = {}

    def add_post(self, summary: CommunityPostSummaryDTO) -> None:
        self._summaries[summary.post_id] = summary

    async def post_exists(self, post_id: UUID) -> bool:
        return post_id in self._summaries

    async def get_post_summary(self, post_id: UUID) -> CommunityPostSummaryDTO | None:
        return self._summaries.get(post_id)


class FakeQuestionQueryPort(QuestionQueryPort):
    def __init__(self) -> None:
        self._summaries: dict[UUID, CommunityQuestionSummaryDTO] = {}

    def add_question(self, summary: CommunityQuestionSummaryDTO) -> None:
        self._summaries[summary.question_id] = summary

    async def question_exists(self, question_id: UUID) -> bool:
        return question_id in self._summaries

    async def get_question_summary(self, question_id: UUID) -> CommunityQuestionSummaryDTO | None:
        return self._summaries.get(question_id)


class FakeAnswerQueryPort(AnswerQueryPort):
    def __init__(self) -> None:
        self._summaries: dict[UUID, CommunityAnswerSummaryDTO] = {}

    def add_answer(self, summary: CommunityAnswerSummaryDTO) -> None:
        self._summaries[summary.answer_id] = summary

    async def answer_exists(self, answer_id: UUID) -> bool:
        return answer_id in self._summaries

    async def get_answer_summary(self, answer_id: UUID) -> CommunityAnswerSummaryDTO | None:
        return self._summaries.get(answer_id)


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


class FakeCommunityCommentRepository(CommunityCommentRepository):
    def __init__(self) -> None:
        self._comments: dict[UUID, CommunityComment] = {}

    async def get_by_id(self, comment_id: UUID) -> CommunityComment | None:
        return self._comments.get(comment_id)

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
    ) -> tuple[Sequence[CommunityComment], str | None]:
        matches = [c for c in self._comments.values() if c.organization_id == organization_id]
        if not include_deleted:
            matches = [c for c in matches if c.status is not CommentStatus.DELETED]
        if target_type is not None:
            matches = [c for c in matches if c.target_type is target_type]
        if target_id is not None:
            matches = [c for c in matches if c.target_id == target_id]
        if community_id is not None:
            matches = [c for c in matches if c.community_id == community_id]
        if topic_id is not None:
            matches = [c for c in matches if c.topic_id == topic_id]
        if author_id is not None:
            matches = [c for c in matches if c.author_id == author_id]
        if parent_comment_id is not None:
            matches = [c for c in matches if c.parent_comment_id == parent_comment_id]
        if top_level_only:
            matches = [c for c in matches if c.parent_comment_id is None]
        if status:
            matches = [c for c in matches if c.status in status]
        if created_from is not None:
            matches = [c for c in matches if c.created_at >= created_from]
        if created_to is not None:
            matches = [c for c in matches if c.created_at <= created_to]
        if query:
            term = query.strip().lower()
            matches = [c for c in matches if term in str(c.body).lower()]

        reverse = sort_order == "desc"
        matches.sort(key=lambda c: (c.created_at, c.id), reverse=reverse)

        if cursor is not None:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            if reverse:
                matches = [
                    c for c in matches if (c.created_at, c.id) < (cursor_created_at, cursor_id)
                ]
            else:
                matches = [
                    c for c in matches if (c.created_at, c.id) > (cursor_created_at, cursor_id)
                ]

        has_more = len(matches) > limit
        page = matches[:limit]
        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = _encode_cursor(last.created_at, last.id)

        return page, next_cursor

    async def get_thread(
        self,
        root_comment_id: UUID,
        *,
        max_depth: int,
        status: Sequence[CommentStatus] | None = None,
        limit: int = 500,
    ) -> Sequence[CommunityComment]:
        matches = [
            c
            for c in self._comments.values()
            if c.root_comment_id == root_comment_id and c.depth <= max_depth
        ]
        if status:
            matches = [c for c in matches if c.status in status]
        matches.sort(key=lambda c: (c.depth, c.created_at))
        return matches[:limit]

    async def add(self, comment: CommunityComment) -> None:
        self._comments[comment.id] = comment


class FakeCommunityCommentRevisionRepository(CommunityCommentRevisionRepository):
    """No `remove()` seam — matches `CommunityCommentRevisionRepository`'s
    own docstring: revision history is immutable, full stop."""

    def __init__(self) -> None:
        self._revisions: dict[UUID, CommunityCommentRevision] = {}

    async def get_by_id(self, revision_id: UUID) -> CommunityCommentRevision | None:
        return self._revisions.get(revision_id)

    async def list_by_comment(
        self, comment_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[CommunityCommentRevision]:
        matches = [r for r in self._revisions.values() if r.comment_id.value == comment_id]
        matches.sort(key=lambda r: r.revision_number, reverse=True)
        return matches[offset : offset + limit]

    async def add(self, revision: CommunityCommentRevision) -> None:
        self._revisions[revision.id] = revision


class FakeCommunityCommentAttachmentRepository(CommunityCommentAttachmentRepository):
    def __init__(self) -> None:
        self._attachments: dict[UUID, CommunityCommentAttachment] = {}

    async def get_by_id(self, attachment_id: UUID) -> CommunityCommentAttachment | None:
        return self._attachments.get(attachment_id)

    async def list_by_comment(self, comment_id: UUID) -> list[CommunityCommentAttachment]:
        return [a for a in self._attachments.values() if a.comment_id.value == comment_id]

    async def is_assigned(self, comment_id: UUID, document_id: UUID) -> bool:
        return any(
            a.comment_id.value == comment_id and a.document_id == document_id
            for a in self._attachments.values()
        )

    async def add(self, attachment: CommunityCommentAttachment) -> None:
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
