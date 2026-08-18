"""Unit tests for `FollowTopicService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community_engagement.application.dto import FollowTopicInput
from app.modules.community_engagement.application.services.follow_topic_service import (
    FollowTopicService,
)
from app.modules.community_engagement.domain.enums import FollowTargetType
from app.modules.community_engagement.domain.events import TopicFollowed
from app.modules.community_engagement.domain.exceptions import TopicNotFoundForFollowError
from tests.unit.modules.community_engagement.application.fakes import (
    FakeTopicFollowerRepository,
    FakeTopicQueryPort,
    FakeUnitOfWork,
    make_topic_summary,
)


def _seeded() -> (
    tuple[FollowTopicService, FakeTopicFollowerRepository, FakeTopicQueryPort, FakeUnitOfWork]
):
    followers = FakeTopicFollowerRepository()
    topics = FakeTopicQueryPort()
    uow = FakeUnitOfWork()
    service = FollowTopicService(
        topic_follower_repository=followers, topic_query_port=topics, unit_of_work=uow
    )
    return service, followers, topics, uow


class TestFollowTopic:
    async def test_creates_a_follow(self) -> None:
        service, followers, topics, _ = _seeded()
        topic_id, user_id, org_id = uuid4(), uuid4(), uuid4()
        topics.add_topic(make_topic_summary(topic_id=topic_id))

        result = await service.execute(
            FollowTopicInput(user_id=user_id, organization_id=org_id, topic_id=topic_id)
        )
        assert result.follow_target_type is FollowTargetType.TOPIC
        assert result.target_id == topic_id
        assert result.user_id == user_id
        stored = await followers.get_follow(user_id, topic_id)
        assert stored is not None

    async def test_unknown_topic_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(TopicNotFoundForFollowError):
            await service.execute(
                FollowTopicInput(user_id=uuid4(), organization_id=uuid4(), topic_id=uuid4())
            )

    async def test_idempotent_when_already_following(self) -> None:
        service, followers, topics, uow = _seeded()
        topic_id, user_id, org_id = uuid4(), uuid4(), uuid4()
        topics.add_topic(make_topic_summary(topic_id=topic_id))
        first = await service.execute(
            FollowTopicInput(user_id=user_id, organization_id=org_id, topic_id=topic_id)
        )

        uow.committed = False
        second = await service.execute(
            FollowTopicInput(user_id=user_id, organization_id=org_id, topic_id=topic_id)
        )
        assert second.follow_id == first.follow_id
        assert uow.committed is False

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, topics, uow = _seeded()
        topic_id = uuid4()
        topics.add_topic(make_topic_summary(topic_id=topic_id))

        await service.execute(
            FollowTopicInput(user_id=uuid4(), organization_id=uuid4(), topic_id=topic_id)
        )
        assert uow.committed is True

    async def test_publishes_a_topic_followed_event(self) -> None:
        service, _, topics, uow = _seeded()
        topic_id = uuid4()
        topics.add_topic(make_topic_summary(topic_id=topic_id))

        await service.execute(
            FollowTopicInput(user_id=uuid4(), organization_id=uuid4(), topic_id=topic_id)
        )
        assert any(isinstance(e, TopicFollowed) for e in uow.published_events)
