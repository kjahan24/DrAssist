"""Unit tests for `UnfollowTopicService` — unconditionally idempotent."""

from uuid import uuid4

from app.modules.community_engagement.application.dto import UnfollowTopicInput
from app.modules.community_engagement.application.services.unfollow_topic_service import (
    UnfollowTopicService,
)
from app.modules.community_engagement.domain.entities import TopicFollower
from app.modules.community_engagement.domain.events import TopicUnfollowed
from tests.unit.modules.community_engagement.application.fakes import (
    FakeTopicFollowerRepository,
    FakeUnitOfWork,
)


def _seeded() -> tuple[UnfollowTopicService, FakeTopicFollowerRepository, FakeUnitOfWork]:
    followers = FakeTopicFollowerRepository()
    uow = FakeUnitOfWork()
    service = UnfollowTopicService(topic_follower_repository=followers, unit_of_work=uow)
    return service, followers, uow


class TestUnfollowTopic:
    async def test_removes_an_existing_follow(self) -> None:
        service, followers, _ = _seeded()
        user_id, topic_id = uuid4(), uuid4()
        follower = TopicFollower.create(user_id=user_id, organization_id=uuid4(), topic_id=topic_id)
        await followers.add(follower)

        await service.execute(UnfollowTopicInput(user_id=user_id, topic_id=topic_id))
        assert await followers.get_follow(user_id, topic_id) is None

    async def test_unfollowing_something_never_followed_is_a_silent_no_op(self) -> None:
        service, _, uow = _seeded()
        await service.execute(UnfollowTopicInput(user_id=uuid4(), topic_id=uuid4()))
        assert uow.committed is False

    async def test_commits_the_unit_of_work_when_a_follow_is_removed(self) -> None:
        service, followers, uow = _seeded()
        user_id, topic_id = uuid4(), uuid4()
        follower = TopicFollower.create(user_id=user_id, organization_id=uuid4(), topic_id=topic_id)
        await followers.add(follower)

        await service.execute(UnfollowTopicInput(user_id=user_id, topic_id=topic_id))
        assert uow.committed is True

    async def test_publishes_a_topic_unfollowed_event(self) -> None:
        service, followers, uow = _seeded()
        user_id, topic_id = uuid4(), uuid4()
        follower = TopicFollower.create(user_id=user_id, organization_id=uuid4(), topic_id=topic_id)
        await followers.add(follower)

        await service.execute(UnfollowTopicInput(user_id=user_id, topic_id=topic_id))
        assert any(isinstance(e, TopicUnfollowed) for e in uow.published_events)
