"""Unit tests for `ListFollowersService` — one service dispatching
across all three follower repositories by `FollowTargetType`."""

from uuid import uuid4

from app.modules.community_engagement.application.dto import ListFollowersInput
from app.modules.community_engagement.application.services.list_followers_service import (
    ListFollowersService,
)
from app.modules.community_engagement.domain.entities import (
    CommunityFollower,
    DoctorFollower,
    TopicFollower,
)
from app.modules.community_engagement.domain.enums import FollowTargetType
from tests.unit.modules.community_engagement.application.fakes import (
    FakeCommunityFollowerRepository,
    FakeDoctorFollowerRepository,
    FakeTopicFollowerRepository,
)


def _service() -> (
    tuple[
        ListFollowersService,
        FakeTopicFollowerRepository,
        FakeCommunityFollowerRepository,
        FakeDoctorFollowerRepository,
    ]
):
    topic_repo = FakeTopicFollowerRepository()
    community_repo = FakeCommunityFollowerRepository()
    doctor_repo = FakeDoctorFollowerRepository()
    service = ListFollowersService(
        topic_follower_repository=topic_repo,
        community_follower_repository=community_repo,
        doctor_follower_repository=doctor_repo,
    )
    return service, topic_repo, community_repo, doctor_repo


class TestListFollowersTopic:
    async def test_lists_followers_of_a_topic(self) -> None:
        service, topic_repo, _, _ = _service()
        topic_id, user_id = uuid4(), uuid4()
        await topic_repo.add(
            TopicFollower.create(user_id=user_id, organization_id=uuid4(), topic_id=topic_id)
        )

        result = await service.list_followers(
            ListFollowersInput(follow_target_type=FollowTargetType.TOPIC, target_id=topic_id)
        )
        assert [i.user_id for i in result.items] == [user_id]
        assert result.items[0].follow_target_type is FollowTargetType.TOPIC
        assert result.items[0].target_id == topic_id

    async def test_excludes_followers_of_other_topics(self) -> None:
        service, topic_repo, _, _ = _service()
        topic_id = uuid4()
        await topic_repo.add(
            TopicFollower.create(user_id=uuid4(), organization_id=uuid4(), topic_id=uuid4())
        )

        result = await service.list_followers(
            ListFollowersInput(follow_target_type=FollowTargetType.TOPIC, target_id=topic_id)
        )
        assert result.items == ()


class TestListFollowersCommunity:
    async def test_lists_followers_of_a_community(self) -> None:
        service, _, community_repo, _ = _service()
        community_id, user_id = uuid4(), uuid4()
        await community_repo.add(
            CommunityFollower.create(
                user_id=user_id, organization_id=uuid4(), community_id=community_id
            )
        )

        result = await service.list_followers(
            ListFollowersInput(
                follow_target_type=FollowTargetType.COMMUNITY, target_id=community_id
            )
        )
        assert [i.user_id for i in result.items] == [user_id]
        assert result.items[0].follow_target_type is FollowTargetType.COMMUNITY


class TestListFollowersDoctor:
    async def test_lists_followers_of_a_doctor(self) -> None:
        service, _, _, doctor_repo = _service()
        followed_id, follower_id = uuid4(), uuid4()
        await doctor_repo.add(
            DoctorFollower.create(
                follower_user_id=follower_id, organization_id=uuid4(), followed_user_id=followed_id
            )
        )

        result = await service.list_followers(
            ListFollowersInput(follow_target_type=FollowTargetType.DOCTOR, target_id=followed_id)
        )
        assert [i.user_id for i in result.items] == [follower_id]
        assert result.items[0].follow_target_type is FollowTargetType.DOCTOR
        assert result.items[0].target_id == followed_id

    async def test_returns_a_next_cursor_when_more_results_remain(self) -> None:
        service, _, _, doctor_repo = _service()
        followed_id = uuid4()
        for _ in range(3):
            await doctor_repo.add(
                DoctorFollower.create(
                    follower_user_id=uuid4(), organization_id=uuid4(), followed_user_id=followed_id
                )
            )

        result = await service.list_followers(
            ListFollowersInput(
                follow_target_type=FollowTargetType.DOCTOR, target_id=followed_id, limit=2
            )
        )
        assert len(result.items) == 2
        assert result.next_cursor is not None
