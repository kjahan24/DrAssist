"""Unit tests for `UnfollowTopicService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.medical_topics.application.dto import UnfollowTopicInput
from app.modules.medical_topics.application.services.unfollow_topic_service import (
    UnfollowTopicService,
)
from app.modules.medical_topics.domain.entities import MedicalTopicFollower
from app.modules.medical_topics.domain.exceptions import TopicNotFollowedError
from app.modules.medical_topics.domain.value_objects import TopicId
from tests.unit.modules.medical_topics.application.fakes import (
    FakeMedicalTopicFollowerRepository,
    FakeUnitOfWork,
)


def _seeded() -> tuple[UnfollowTopicService, FakeMedicalTopicFollowerRepository, FakeUnitOfWork]:
    followers = FakeMedicalTopicFollowerRepository()
    uow = FakeUnitOfWork()
    service = UnfollowTopicService(follower_repository=followers, unit_of_work=uow)
    return service, followers, uow


class TestUnfollowTopic:
    async def test_removes_the_follower(self) -> None:
        service, followers, _ = _seeded()
        topic_id, user_id = uuid4(), uuid4()
        await followers.add(
            MedicalTopicFollower.create(topic_id=TopicId(topic_id), user_id=user_id)
        )

        await service.execute(UnfollowTopicInput(topic_id=topic_id, user_id=user_id))

        assert await followers.get_by_topic_and_user(topic_id, user_id) is None

    async def test_not_following_raises(self) -> None:
        service, _, _ = _seeded()
        with pytest.raises(TopicNotFollowedError):
            await service.execute(UnfollowTopicInput(topic_id=uuid4(), user_id=uuid4()))

    async def test_commits_the_unit_of_work(self) -> None:
        service, followers, uow = _seeded()
        topic_id, user_id = uuid4(), uuid4()
        await followers.add(
            MedicalTopicFollower.create(topic_id=TopicId(topic_id), user_id=user_id)
        )

        await service.execute(UnfollowTopicInput(topic_id=topic_id, user_id=user_id))

        assert uow.committed is True
