"""In-memory test doubles for the Community Engagement module's five
repositories, Unit of Work, and the seven cross-module query ports it
depends on (`PostQueryPort`/`QuestionQueryPort`/`AnswerQueryPort`/
`CommentQueryPort`/`TopicQueryPort`/`CommunityQueryPort`/`UserQueryPort`)
— each implements the exact same interface its real counterpart does,
per `docs/backend-architecture/12_testing_architecture.md` ("fakes over
mocks as the default"). Application-layer service tests depend on these,
never on a real database or a real peer module.
"""

import base64
from collections.abc import Sequence
from datetime import datetime
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
from app.modules.community_engagement.domain.entities import (
    CommunityFollower,
    DoctorFollower,
    SavedContent,
    TopicFollower,
    Vote,
)
from app.modules.community_engagement.domain.enums import EngagementTargetType, VoteType
from app.modules.community_engagement.domain.repositories import (
    CommunityFollowerRepository,
    DoctorFollowerRepository,
    SavedContentRepository,
    TopicFollowerRepository,
    VoteRepository,
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
from app.modules.medical_topics.public.dto import TopicStatus, TopicSummaryDTO, TopicVisibility
from app.modules.medical_topics.public.interfaces import TopicQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent

_CURSOR_SEPARATOR = "|"


def _encode_cursor(created_at: datetime, row_id: UUID) -> str:
    payload = f"{created_at.isoformat()}{_CURSOR_SEPARATOR}{row_id}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    payload = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    created_at_raw, row_id_raw = payload.split(_CURSOR_SEPARATOR, 1)
    return datetime.fromisoformat(created_at_raw), UUID(row_id_raw)


# --- Summary DTO builders --------------------------------------------------------------


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


def make_comment_summary(**overrides: object) -> CommunityCommentSummaryDTO:
    now = datetime.now().astimezone()
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


def make_topic_summary(**overrides: object) -> TopicSummaryDTO:
    now = datetime.now().astimezone()
    defaults: dict[str, object] = {
        "topic_id": uuid4(),
        "slug": "cardiology",
        "name": "Cardiology",
        "status": TopicStatus.PUBLISHED,
        "visibility": TopicVisibility.PUBLIC,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return TopicSummaryDTO(**defaults)  # type: ignore[arg-type]


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


class FakeTopicQueryPort(TopicQueryPort):
    def __init__(self) -> None:
        self._summaries: dict[UUID, TopicSummaryDTO] = {}

    def add_topic(self, summary: TopicSummaryDTO) -> None:
        self._summaries[summary.topic_id] = summary

    async def topic_exists(self, topic_id: UUID) -> bool:
        return topic_id in self._summaries

    async def get_topic_summary(self, topic_id: UUID) -> TopicSummaryDTO | None:
        return self._summaries.get(topic_id)

    async def get_topic_summary_by_slug(self, slug: str) -> TopicSummaryDTO | None:
        return next((s for s in self._summaries.values() if s.slug == slug), None)


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


# --- Fake repositories --------------------------------------------------------------


class FakeVoteRepository(VoteRepository):
    def __init__(self) -> None:
        self._votes: dict[UUID, Vote] = {}

    async def get_by_id(self, vote_id: UUID) -> Vote | None:
        return self._votes.get(vote_id)

    async def get_vote(
        self, user_id: UUID, target_type: EngagementTargetType, target_id: UUID
    ) -> Vote | None:
        for vote in self._votes.values():
            if (
                vote.user_id == user_id
                and vote.target_type is target_type
                and vote.target_id == target_id
            ):
                return vote
        return None

    async def count_votes(
        self, target_type: EngagementTargetType, target_id: UUID
    ) -> dict[VoteType, int]:
        counts: dict[VoteType, int] = {VoteType.UPVOTE: 0, VoteType.DOWNVOTE: 0}
        for vote in self._votes.values():
            if vote.target_type is target_type and vote.target_id == target_id:
                counts[vote.vote_type] += 1
        return counts

    async def add(self, vote: Vote) -> None:
        self._votes[vote.id] = vote

    async def remove(self, vote_id: UUID) -> None:
        self._votes.pop(vote_id, None)


class FakeSavedContentRepository(SavedContentRepository):
    def __init__(self) -> None:
        self._saved: dict[UUID, SavedContent] = {}

    async def get_by_id(self, saved_content_id: UUID) -> SavedContent | None:
        return self._saved.get(saved_content_id)

    async def get_saved(
        self, user_id: UUID, target_type: EngagementTargetType, target_id: UUID
    ) -> SavedContent | None:
        for saved in self._saved.values():
            if (
                saved.user_id == user_id
                and saved.target_type is target_type
                and saved.target_id == target_id
            ):
                return saved
        return None

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        target_type: EngagementTargetType | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[Sequence[SavedContent], str | None]:
        matches = [s for s in self._saved.values() if s.user_id == user_id]
        if target_type is not None:
            matches = [s for s in matches if s.target_type is target_type]
        matches.sort(key=lambda s: (s.created_at, s.id), reverse=True)

        if cursor is not None:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            matches = [s for s in matches if (s.created_at, s.id) < (cursor_created_at, cursor_id)]

        has_more = len(matches) > limit
        page = matches[:limit]
        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = _encode_cursor(last.created_at, last.id)
        return page, next_cursor

    async def add(self, saved: SavedContent) -> None:
        self._saved[saved.id] = saved

    async def remove(self, saved_content_id: UUID) -> None:
        self._saved.pop(saved_content_id, None)


class FakeTopicFollowerRepository(TopicFollowerRepository):
    def __init__(self) -> None:
        self._followers: dict[UUID, TopicFollower] = {}

    async def get_by_id(self, topic_follower_id: UUID) -> TopicFollower | None:
        return self._followers.get(topic_follower_id)

    async def get_follow(self, user_id: UUID, topic_id: UUID) -> TopicFollower | None:
        for follower in self._followers.values():
            if follower.user_id == user_id and follower.topic_id == topic_id:
                return follower
        return None

    async def list_followers(
        self, topic_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[TopicFollower], str | None]:
        matches = [f for f in self._followers.values() if f.topic_id == topic_id]
        return self._paginate(matches, cursor=cursor, limit=limit)

    async def list_following(
        self, user_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[TopicFollower], str | None]:
        matches = [f for f in self._followers.values() if f.user_id == user_id]
        return self._paginate(matches, cursor=cursor, limit=limit)

    async def count_followers(self, topic_id: UUID) -> int:
        return len([f for f in self._followers.values() if f.topic_id == topic_id])

    async def add(self, follower: TopicFollower) -> None:
        self._followers[follower.id] = follower

    async def remove(self, topic_follower_id: UUID) -> None:
        self._followers.pop(topic_follower_id, None)

    @staticmethod
    def _paginate(
        matches: list[TopicFollower], *, cursor: str | None, limit: int
    ) -> tuple[Sequence[TopicFollower], str | None]:
        matches = sorted(matches, key=lambda f: (f.created_at, f.id), reverse=True)
        if cursor is not None:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            matches = [f for f in matches if (f.created_at, f.id) < (cursor_created_at, cursor_id)]
        has_more = len(matches) > limit
        page = matches[:limit]
        next_cursor = None
        if has_more and page:
            next_cursor = _encode_cursor(page[-1].created_at, page[-1].id)
        return page, next_cursor


class FakeCommunityFollowerRepository(CommunityFollowerRepository):
    def __init__(self) -> None:
        self._followers: dict[UUID, CommunityFollower] = {}

    async def get_by_id(self, community_follower_id: UUID) -> CommunityFollower | None:
        return self._followers.get(community_follower_id)

    async def get_follow(self, user_id: UUID, community_id: UUID) -> CommunityFollower | None:
        for follower in self._followers.values():
            if follower.user_id == user_id and follower.community_id == community_id:
                return follower
        return None

    async def list_followers(
        self, community_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[CommunityFollower], str | None]:
        matches = [f for f in self._followers.values() if f.community_id == community_id]
        return self._paginate(matches, cursor=cursor, limit=limit)

    async def list_following(
        self, user_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[CommunityFollower], str | None]:
        matches = [f for f in self._followers.values() if f.user_id == user_id]
        return self._paginate(matches, cursor=cursor, limit=limit)

    async def count_followers(self, community_id: UUID) -> int:
        return len([f for f in self._followers.values() if f.community_id == community_id])

    async def add(self, follower: CommunityFollower) -> None:
        self._followers[follower.id] = follower

    async def remove(self, community_follower_id: UUID) -> None:
        self._followers.pop(community_follower_id, None)

    @staticmethod
    def _paginate(
        matches: list[CommunityFollower], *, cursor: str | None, limit: int
    ) -> tuple[Sequence[CommunityFollower], str | None]:
        matches = sorted(matches, key=lambda f: (f.created_at, f.id), reverse=True)
        if cursor is not None:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            matches = [f for f in matches if (f.created_at, f.id) < (cursor_created_at, cursor_id)]
        has_more = len(matches) > limit
        page = matches[:limit]
        next_cursor = None
        if has_more and page:
            next_cursor = _encode_cursor(page[-1].created_at, page[-1].id)
        return page, next_cursor


class FakeDoctorFollowerRepository(DoctorFollowerRepository):
    def __init__(self) -> None:
        self._followers: dict[UUID, DoctorFollower] = {}

    async def get_by_id(self, doctor_follower_id: UUID) -> DoctorFollower | None:
        return self._followers.get(doctor_follower_id)

    async def get_follow(
        self, follower_user_id: UUID, followed_user_id: UUID
    ) -> DoctorFollower | None:
        for follower in self._followers.values():
            if (
                follower.follower_user_id == follower_user_id
                and follower.followed_user_id == followed_user_id
            ):
                return follower
        return None

    async def list_followers(
        self, followed_user_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[DoctorFollower], str | None]:
        matches = [f for f in self._followers.values() if f.followed_user_id == followed_user_id]
        return self._paginate(matches, cursor=cursor, limit=limit)

    async def list_following(
        self, follower_user_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[DoctorFollower], str | None]:
        matches = [f for f in self._followers.values() if f.follower_user_id == follower_user_id]
        return self._paginate(matches, cursor=cursor, limit=limit)

    async def count_followers(self, followed_user_id: UUID) -> int:
        return len([f for f in self._followers.values() if f.followed_user_id == followed_user_id])

    async def add(self, follower: DoctorFollower) -> None:
        self._followers[follower.id] = follower

    async def remove(self, doctor_follower_id: UUID) -> None:
        self._followers.pop(doctor_follower_id, None)

    @staticmethod
    def _paginate(
        matches: list[DoctorFollower], *, cursor: str | None, limit: int
    ) -> tuple[Sequence[DoctorFollower], str | None]:
        matches = sorted(matches, key=lambda f: (f.created_at, f.id), reverse=True)
        if cursor is not None:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            matches = [f for f in matches if (f.created_at, f.id) < (cursor_created_at, cursor_id)]
        has_more = len(matches) > limit
        page = matches[:limit]
        next_cursor = None
        if has_more and page:
            next_cursor = _encode_cursor(page[-1].created_at, page[-1].id)
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
