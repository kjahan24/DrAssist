"""Unit tests for `ListFollowingService` — the mirror image of
`ListFollowersService`."""

from uuid import uuid4

from app.modules.community_engagement.application.dto import ListFollowingInput
from app.modules.community_engagement.application.services.list_following_service import (
    ListFollowingService,
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
        ListFollowingService,
        FakeTopicFollowerRepository,
        FakeCommunityFollowerRepository,
        FakeDoctorFollowerRepository,
    ]
):
    topic_repo = FakeTopicFollowerRepository()
    community_repo = FakeCommunityFollowerRepository()
    doctor_repo = FakeDoctorFollowerRepository()
    service = ListFollowingService(
        topic_follower_repository=topic_repo,
        community_follower_repository=community_repo,
        doctor_follower_repository=doctor_repo,
    )
    return service, topic_repo, community_repo, doctor_repo


class TestListFollowingTopic:
    async def test_lists_topics_the_user_follows(self) -> None:
        service, topic_repo, _, _ = _service()
        user_id, topic_id = uuid4(), uuid4()
        await topic_repo.add(
            TopicFollower.create(user_id=user_id, organization_id=uuid4(), topic_id=topic_id)
        )

        result = await service.list_following(
            ListFollowingInput(follow_target_type=FollowTargetType.TOPIC, user_id=user_id)
        )
        assert [i.target_id for i in result.items] == [topic_id]

    async def test_excludes_other_users_follows(self) -> None:
        service, topic_repo, _, _ = _service()
        user_id = uuid4()
        await topic_repo.add(
            TopicFollower.create(user_id=uuid4(), organization_id=uuid4(), topic_id=uuid4())
        )

        result = await service.list_following(
            ListFollowingInput(follow_target_type=FollowTargetType.TOPIC, user_id=user_id)
        )
        assert result.items == ()


class TestListFollowingCommunity:
    async def test_lists_communities_the_user_follows(self) -> None:
        service, _, community_repo, _ = _service()
        user_id, community_id = uuid4(), uuid4()
        await community_repo.add(
            CommunityFollower.create(
                user_id=user_id, organization_id=uuid4(), community_id=community_id
            )
        )

        result = await service.list_following(
            ListFollowingInput(follow_target_type=FollowTargetType.COMMUNITY, user_id=user_id)
        )
        assert [i.target_id for i in result.items] == [community_id]


class TestListFollowingDoctor:
    async def test_lists_users_this_user_follows(self) -> None:
        service, _, _, doctor_repo = _service()
        follower_id, followed_id = uuid4(), uuid4()
        await doctor_repo.add(
            DoctorFollower.create(
                follower_user_id=follower_id, organization_id=uuid4(), followed_user_id=followed_id
            )
        )

        result = await service.list_following(
            ListFollowingInput(follow_target_type=FollowTargetType.DOCTOR, user_id=follower_id)
        )
        assert [i.target_id for i in result.items] == [followed_id]

    async def test_returns_a_next_cursor_when_more_results_remain(self) -> None:
        service, _, _, doctor_repo = _service()
        follower_id = uuid4()
        for _ in range(3):
            await doctor_repo.add(
                DoctorFollower.create(
                    follower_user_id=follower_id, organization_id=uuid4(), followed_user_id=uuid4()
                )
            )

        result = await service.list_following(
            ListFollowingInput(
                follow_target_type=FollowTargetType.DOCTOR, user_id=follower_id, limit=2
            )
        )
        assert len(result.items) == 2
        assert result.next_cursor is not None
