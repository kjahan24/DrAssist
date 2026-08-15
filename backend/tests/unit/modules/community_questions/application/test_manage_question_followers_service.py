"""Unit tests for `ManageQuestionFollowersService`, using in-memory
fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityMemberStatus, CommunityRole
from app.modules.community_questions.application.dto import (
    FollowQuestionInput,
    UnfollowQuestionInput,
)
from app.modules.community_questions.application.services.manage_question_followers_service import (
    ManageQuestionFollowersService,
)
from app.modules.community_questions.domain.entities import CommunityQuestion
from app.modules.community_questions.domain.enums import QuestionVisibility
from app.modules.community_questions.domain.events import (
    CommunityQuestionFollowed,
    CommunityQuestionUnfollowed,
)
from app.modules.community_questions.domain.exceptions import (
    DuplicateQuestionFollowerError,
    QuestionFollowerNotFoundError,
    QuestionNotFoundError,
    QuestionNotViewableError,
)
from app.modules.community_questions.domain.value_objects import QuestionTitle
from tests.unit.modules.community_questions.application.fakes import (
    FakeCommunityQueryPort,
    FakeCommunityQuestionFollowerRepository,
    FakeCommunityQuestionRepository,
    FakeUnitOfWork,
    make_community_summary,
    make_member_summary,
)


def _seeded() -> (
    tuple[
        ManageQuestionFollowersService,
        FakeCommunityQuestionRepository,
        FakeCommunityQuestionFollowerRepository,
        FakeCommunityQueryPort,
        FakeUnitOfWork,
    ]
):
    questions = FakeCommunityQuestionRepository()
    followers = FakeCommunityQuestionFollowerRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = ManageQuestionFollowersService(
        question_follower_repository=followers,
        question_repository=questions,
        community_query_port=communities,
        unit_of_work=uow,
    )
    return service, questions, followers, communities, uow


async def _seed_question(
    questions: FakeCommunityQuestionRepository,
    communities: FakeCommunityQueryPort,
    **overrides: object,
) -> CommunityQuestion:
    defaults: dict[str, object] = {
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "author_id": uuid4(),
        "primary_topic_id": uuid4(),
        "title": QuestionTitle("Title"),
        "body": "Body",
    }
    defaults.update(overrides)
    question = CommunityQuestion.create(**defaults)  # type: ignore[arg-type]
    await questions.add(question)
    communities.add_community(make_community_summary(community_id=question.community_id))
    return question


class TestFollow:
    async def test_a_member_follows_a_public_question(self) -> None:
        service, questions, followers, communities, _ = _seeded()
        question = await _seed_question(questions, communities)
        user_id = uuid4()

        summary = await service.follow(
            FollowQuestionInput(question_id=question.id, acting_user_id=user_id)
        )
        assert summary.user_id == user_id
        assert len(await followers.list_by_question(question.id)) == 1

    async def test_follow_increments_the_questions_follower_count(self) -> None:
        service, questions, _, communities, _ = _seeded()
        question = await _seed_question(questions, communities)

        await service.follow(FollowQuestionInput(question_id=question.id, acting_user_id=uuid4()))
        stored = await questions.get_by_id(question.id)
        assert stored is not None
        assert stored.follower_count == 1

    async def test_a_non_member_can_follow_a_public_question(self) -> None:
        service, questions, _, communities, _ = _seeded()
        question = await _seed_question(
            questions, communities, visibility=QuestionVisibility.PUBLIC
        )

        summary = await service.follow(
            FollowQuestionInput(question_id=question.id, acting_user_id=uuid4())
        )
        assert summary.question_id == question.id

    async def test_a_non_member_cannot_follow_a_members_only_question(self) -> None:
        service, questions, _, communities, _ = _seeded()
        question = await _seed_question(
            questions, communities, visibility=QuestionVisibility.MEMBERS_ONLY
        )

        with pytest.raises(QuestionNotViewableError):
            await service.follow(
                FollowQuestionInput(question_id=question.id, acting_user_id=uuid4())
            )

    async def test_an_active_member_can_follow_a_members_only_question(self) -> None:
        service, questions, _, communities, _ = _seeded()
        question = await _seed_question(
            questions, communities, visibility=QuestionVisibility.MEMBERS_ONLY
        )
        user_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=question.community_id,
                user_id=user_id,
                role=CommunityRole.MEMBER,
                status=CommunityMemberStatus.ACTIVE,
            )
        )

        summary = await service.follow(
            FollowQuestionInput(question_id=question.id, acting_user_id=user_id)
        )
        assert summary.user_id == user_id

    async def test_unknown_question_raises(self) -> None:
        service, _, _, _, _ = _seeded()
        with pytest.raises(QuestionNotFoundError):
            await service.follow(FollowQuestionInput(question_id=uuid4(), acting_user_id=uuid4()))

    async def test_already_following_raises(self) -> None:
        service, questions, _, communities, _ = _seeded()
        question = await _seed_question(questions, communities)
        user_id = uuid4()
        await service.follow(FollowQuestionInput(question_id=question.id, acting_user_id=user_id))

        with pytest.raises(DuplicateQuestionFollowerError):
            await service.follow(
                FollowQuestionInput(question_id=question.id, acting_user_id=user_id)
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, questions, _, communities, uow = _seeded()
        question = await _seed_question(questions, communities)
        await service.follow(FollowQuestionInput(question_id=question.id, acting_user_id=uuid4()))
        assert uow.committed is True

    async def test_publishes_a_community_question_followed_event(self) -> None:
        service, questions, _, communities, uow = _seeded()
        question = await _seed_question(questions, communities)
        await service.follow(FollowQuestionInput(question_id=question.id, acting_user_id=uuid4()))
        assert any(isinstance(e, CommunityQuestionFollowed) for e in uow.published_events)


class TestListFollowers:
    async def test_lists_followers(self) -> None:
        service, questions, _, communities, _ = _seeded()
        question = await _seed_question(questions, communities)
        user_id = uuid4()
        await service.follow(FollowQuestionInput(question_id=question.id, acting_user_id=user_id))

        result = await service.list_followers(question.id)
        assert [f.user_id for f in result] == [user_id]

    async def test_returns_empty_for_a_question_with_no_followers(self) -> None:
        service, questions, _, communities, _ = _seeded()
        question = await _seed_question(questions, communities)

        assert await service.list_followers(question.id) == []


class TestUnfollow:
    async def test_unfollow_removes_the_follower_row(self) -> None:
        service, questions, followers, communities, _ = _seeded()
        question = await _seed_question(questions, communities)
        user_id = uuid4()
        await service.follow(FollowQuestionInput(question_id=question.id, acting_user_id=user_id))

        await service.unfollow(
            UnfollowQuestionInput(question_id=question.id, acting_user_id=user_id)
        )
        assert await followers.list_by_question(question.id) == []

    async def test_unfollow_decrements_the_questions_follower_count(self) -> None:
        service, questions, _, communities, _ = _seeded()
        question = await _seed_question(questions, communities)
        user_id = uuid4()
        await service.follow(FollowQuestionInput(question_id=question.id, acting_user_id=user_id))

        await service.unfollow(
            UnfollowQuestionInput(question_id=question.id, acting_user_id=user_id)
        )
        stored = await questions.get_by_id(question.id)
        assert stored is not None
        assert stored.follower_count == 0

    async def test_unknown_question_raises(self) -> None:
        service, _, _, _, _ = _seeded()
        with pytest.raises(QuestionNotFoundError):
            await service.unfollow(
                UnfollowQuestionInput(question_id=uuid4(), acting_user_id=uuid4())
            )

    async def test_not_following_raises(self) -> None:
        service, questions, _, communities, _ = _seeded()
        question = await _seed_question(questions, communities)

        with pytest.raises(QuestionFollowerNotFoundError):
            await service.unfollow(
                UnfollowQuestionInput(question_id=question.id, acting_user_id=uuid4())
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, questions, _, communities, uow = _seeded()
        question = await _seed_question(questions, communities)
        user_id = uuid4()
        await service.follow(FollowQuestionInput(question_id=question.id, acting_user_id=user_id))

        await service.unfollow(
            UnfollowQuestionInput(question_id=question.id, acting_user_id=user_id)
        )
        assert uow.committed is True

    async def test_publishes_a_community_question_unfollowed_event(self) -> None:
        service, questions, _, communities, uow = _seeded()
        question = await _seed_question(questions, communities)
        user_id = uuid4()
        await service.follow(FollowQuestionInput(question_id=question.id, acting_user_id=user_id))

        await service.unfollow(
            UnfollowQuestionInput(question_id=question.id, acting_user_id=user_id)
        )
        assert any(isinstance(e, CommunityQuestionUnfollowed) for e in uow.published_events)
