"""In-memory test doubles for the Community Moderation module's four
repositories, Unit of Work, and the eight cross-module query ports it
depends on (`PostQueryPort`/`QuestionQueryPort`/`AnswerQueryPort`/
`CommentQueryPort`/`CommunityQueryPort`/`UserQueryPort`/`DoctorQueryPort`)
— each implements the exact same interface its real counterpart does,
per `docs/backend-architecture/12_testing_architecture.md` ("fakes over
mocks as the default"). Application-layer service tests depend on these,
never on a real database or a real peer module.
"""

import base64
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol, TypeVar
from uuid import UUID, uuid4

from app.modules.authentication.domain.enums import UserStatus
from app.modules.authentication.public.dto import UserSummaryDTO
from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.community.public.dto import (
    CommunityMemberStatus,
    CommunityMemberSummaryDTO,
    CommunityRole,
    CommunitySummaryDTO,
    CommunityVisibility,
)
from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_answers.public.dto import (
    AnswerStatus,
    AnswerVisibility,
    CommunityAnswerSummaryDTO,
)
from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.public.dto import (
    CommentStatus,
    CommentTargetType,
    CommunityCommentSummaryDTO,
)
from app.modules.community_comments.public.interfaces import CommentQueryPort
from app.modules.community_moderation.domain.entities import (
    CommunityReport,
    DoctorVerification,
    ModerationAction,
    ModerationRestriction,
)
from app.modules.community_moderation.domain.enums import (
    ModerationTargetType,
    ReportPriority,
    ReportStatus,
)
from app.modules.community_moderation.domain.repositories import (
    CommunityReportRepository,
    DoctorVerificationRepository,
    ModerationActionRepository,
    ModerationRestrictionRepository,
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
from app.modules.doctor.domain.enums import DoctorStatus
from app.modules.doctor.public.dto import DoctorSummaryDTO
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent

_CURSOR_SEPARATOR = "|"
_OPEN_STATUSES = (ReportStatus.OPEN, ReportStatus.UNDER_REVIEW)


def _encode_cursor(created_at: datetime, row_id: UUID) -> str:
    payload = f"{created_at.isoformat()}{_CURSOR_SEPARATOR}{row_id}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    payload = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    created_at_raw, row_id_raw = payload.split(_CURSOR_SEPARATOR, 1)
    return datetime.fromisoformat(created_at_raw), UUID(row_id_raw)


# --- Summary DTO builders --------------------------------------------------------------


def make_post_summary(**overrides: object) -> CommunityPostSummaryDTO:
    now = datetime.now(UTC)
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
    now = datetime.now(UTC)
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
    now = datetime.now(UTC)
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


def make_comment_summary(**overrides: object) -> CommunityCommentSummaryDTO:
    now = datetime.now(UTC)
    comment_id = uuid4()
    defaults: dict[str, object] = {
        "comment_id": comment_id,
        "target_type": CommentTargetType.POST,
        "target_id": uuid4(),
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "body": "Body text.",
        "status": CommentStatus.PUBLISHED,
        "is_anonymous": False,
        "root_comment_id": comment_id,
        "depth": 0,
        "revision_number": 1,
        "created_at": now,
        "updated_at": now,
        "author_id": uuid4(),
    }
    defaults.update(overrides)
    return CommunityCommentSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_community_summary(**overrides: object) -> CommunitySummaryDTO:
    now = datetime.now(UTC)
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
        "joined_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return CommunityMemberSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_user_summary(**overrides: object) -> UserSummaryDTO:
    defaults: dict[str, object] = {
        "user_id": uuid4(),
        "organization_id": uuid4(),
        "email": "user@example.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "status": UserStatus.ACTIVE,
    }
    defaults.update(overrides)
    return UserSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_doctor_summary(**overrides: object) -> DoctorSummaryDTO:
    defaults: dict[str, object] = {
        "doctor_id": uuid4(),
        "organization_id": uuid4(),
        "user_id": uuid4(),
        "employee_id": "EMP-001",
        "joining_date": datetime.now(UTC).date(),
        "status": DoctorStatus.ACTIVE,
    }
    defaults.update(overrides)
    return DoctorSummaryDTO(**defaults)  # type: ignore[arg-type]


# --- Fake query ports --------------------------------------------------------------


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


class FakeCommentQueryPort(CommentQueryPort):
    def __init__(self) -> None:
        self._summaries: dict[UUID, CommunityCommentSummaryDTO] = {}

    def add_comment(self, summary: CommunityCommentSummaryDTO) -> None:
        self._summaries[summary.comment_id] = summary

    async def comment_exists(self, comment_id: UUID) -> bool:
        return comment_id in self._summaries

    async def get_comment_summary(self, comment_id: UUID) -> CommunityCommentSummaryDTO | None:
        return self._summaries.get(comment_id)


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


class FakeUserQueryPort(UserQueryPort):
    def __init__(self) -> None:
        self._summaries: dict[UUID, UserSummaryDTO] = {}

    def add_user(self, summary: UserSummaryDTO) -> None:
        self._summaries[summary.user_id] = summary

    async def user_exists(self, user_id: UUID) -> bool:
        return user_id in self._summaries

    async def get_user_summary(self, user_id: UUID) -> UserSummaryDTO | None:
        return self._summaries.get(user_id)


class FakeDoctorQueryPort(DoctorQueryPort):
    def __init__(self) -> None:
        self._summaries: dict[UUID, DoctorSummaryDTO] = {}

    def add_doctor(self, summary: DoctorSummaryDTO) -> None:
        self._summaries[summary.doctor_id] = summary

    async def doctor_exists(self, doctor_id: UUID) -> bool:
        return doctor_id in self._summaries

    async def is_active(self, doctor_id: UUID) -> bool:
        summary = self._summaries.get(doctor_id)
        return summary is not None and summary.status is DoctorStatus.ACTIVE

    async def get_doctor_summary(self, doctor_id: UUID) -> DoctorSummaryDTO | None:
        return self._summaries.get(doctor_id)


# --- Fake repositories --------------------------------------------------------------


class FakeCommunityReportRepository(CommunityReportRepository):
    def __init__(self) -> None:
        self._reports: dict[UUID, CommunityReport] = {}

    async def get_by_id(self, report_id: UUID) -> CommunityReport | None:
        return self._reports.get(report_id)

    async def get_open_report(
        self, reporter_id: UUID, target_type: ModerationTargetType, target_id: UUID
    ) -> CommunityReport | None:
        matches = [
            r
            for r in self._reports.values()
            if r.reporter_id == reporter_id
            and r.target_type is target_type
            and r.target_id == target_id
            and r.status in _OPEN_STATUSES
        ]
        matches.sort(key=lambda r: r.created_at, reverse=True)
        return matches[0] if matches else None

    async def list_reports(
        self,
        *,
        organization_id: UUID,
        community_id: UUID | None = None,
        status: ReportStatus | None = None,
        priority: ReportPriority | None = None,
        assigned_moderator_id: UUID | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[Sequence[CommunityReport], str | None]:
        matches = [r for r in self._reports.values() if r.organization_id == organization_id]
        if community_id is not None:
            matches = [r for r in matches if r.community_id == community_id]
        if status is not None:
            matches = [r for r in matches if r.status is status]
        if priority is not None:
            matches = [r for r in matches if r.priority is priority]
        if assigned_moderator_id is not None:
            matches = [r for r in matches if r.assigned_moderator_id == assigned_moderator_id]
        return _paginate(matches, cursor=cursor, limit=limit)

    async def add(self, report: CommunityReport) -> None:
        self._reports[report.id] = report


class FakeModerationActionRepository(ModerationActionRepository):
    def __init__(self) -> None:
        self._actions: dict[UUID, ModerationAction] = {}

    async def get_by_id(self, action_id: UUID) -> ModerationAction | None:
        return self._actions.get(action_id)

    async def get_latest_for_target(
        self, target_type: ModerationTargetType, target_id: UUID
    ) -> ModerationAction | None:
        matches = [
            a
            for a in self._actions.values()
            if a.target_type is target_type and a.target_id == target_id
        ]
        matches.sort(key=lambda a: a.created_at, reverse=True)
        return matches[0] if matches else None

    async def list_for_target(
        self,
        target_type: ModerationTargetType,
        target_id: UUID,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[Sequence[ModerationAction], str | None]:
        matches = [
            a
            for a in self._actions.values()
            if a.target_type is target_type and a.target_id == target_id
        ]
        return _paginate(matches, cursor=cursor, limit=limit)

    async def list_for_actor(
        self, actor_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[ModerationAction], str | None]:
        matches = [a for a in self._actions.values() if a.actor_id == actor_id]
        return _paginate(matches, cursor=cursor, limit=limit)

    async def add(self, action: ModerationAction) -> None:
        self._actions[action.id] = action


class FakeModerationRestrictionRepository(ModerationRestrictionRepository):
    def __init__(self) -> None:
        self._restrictions: dict[UUID, ModerationRestriction] = {}

    async def get_by_id(self, restriction_id: UUID) -> ModerationRestriction | None:
        return self._restrictions.get(restriction_id)

    async def list_active_for_user(
        self,
        user_id: UUID,
        *,
        community_id: UUID | None = None,
        now: datetime | None = None,
    ) -> Sequence[ModerationRestriction]:
        matches = [r for r in self._restrictions.values() if r.user_id == user_id]
        if community_id is not None:
            matches = [r for r in matches if r.community_id == community_id]
        return [r for r in matches if r.is_active(now=now)]

    async def list_for_user(
        self, user_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[ModerationRestriction], str | None]:
        matches = [r for r in self._restrictions.values() if r.user_id == user_id]
        return _paginate(matches, cursor=cursor, limit=limit)

    async def add(self, restriction: ModerationRestriction) -> None:
        self._restrictions[restriction.id] = restriction


class FakeDoctorVerificationRepository(DoctorVerificationRepository):
    def __init__(self) -> None:
        self._verifications: dict[UUID, DoctorVerification] = {}

    async def get_by_id(self, verification_id: UUID) -> DoctorVerification | None:
        return self._verifications.get(verification_id)

    async def get_by_doctor_id(self, doctor_id: UUID) -> DoctorVerification | None:
        for verification in self._verifications.values():
            if verification.doctor_id == doctor_id:
                return verification
        return None

    async def add(self, verification: DoctorVerification) -> None:
        self._verifications[verification.id] = verification


class _HasCreatedAtAndId(Protocol):
    created_at: datetime
    id: UUID


_T = TypeVar("_T", bound=_HasCreatedAtAndId)


def _paginate(
    matches: list[_T], *, cursor: str | None, limit: int
) -> tuple[Sequence[_T], str | None]:
    ordered = sorted(matches, key=lambda m: (m.created_at, m.id), reverse=True)
    if cursor is not None:
        cursor_created_at, cursor_id = _decode_cursor(cursor)
        ordered = [m for m in ordered if (m.created_at, m.id) < (cursor_created_at, cursor_id)]
    has_more = len(ordered) > limit
    page = ordered[:limit]
    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = _encode_cursor(last.created_at, last.id)
    return page, next_cursor


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
