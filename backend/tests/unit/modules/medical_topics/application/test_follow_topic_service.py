"""Unit tests for `FollowTopicService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.medical_topics.application.dto import FollowTopicInput
from app.modules.medical_topics.application.services.follow_topic_service import (
    FollowTopicService,
)
from app.modules.medical_topics.domain.entities import MedicalTopic, MedicalTopicFollower
from app.modules.medical_topics.domain.events import TopicFollowed
from app.modules.medical_topics.domain.exceptions import (
    TopicAlreadyFollowedError,
    TopicNotFoundError,
)
from app.modules.medical_topics.domain.value_objects import TopicId, TopicName, TopicSlug
from tests.unit.modules.medical_topics.application.fakes import (
    FakeMedicalTopicFollowerRepository,
    FakeMedicalTopicRepository,
    FakeUnitOfWork,
)


def _seeded() -> (
    tuple[
        FollowTopicService,
        FakeMedicalTopicRepository,
        FakeMedicalTopicFollowerRepository,
        FakeUnitOfWork,
    ]
):
    topics = FakeMedicalTopicRepository()
    followers = FakeMedicalTopicFollowerRepository()
    uow = FakeUnitOfWork()
    service = FollowTopicService(
        topic_repository=topics, follower_repository=followers, unit_of_work=uow
    )
    return service, topics, followers, uow


class TestFollowTopic:
    async def test_creates_a_follower(self) -> None:
        service, topics, followers, _ = _seeded()
        topic = MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        await topics.add(topic)
        user_id = uuid4()

        output = await service.execute(FollowTopicInput(topic_id=topic.id, user_id=user_id))

        assert output.topic_id == topic.id
        assert output.user_id == user_id
        stored = await followers.get_by_topic_and_user(topic.id, user_id)
        assert stored is not None

    async def test_unknown_topic_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(TopicNotFoundError):
            await service.execute(FollowTopicInput(topic_id=uuid4(), user_id=uuid4()))

    async def test_already_following_raises(self) -> None:
        service, topics, followers, _ = _seeded()
        topic = MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        await topics.add(topic)
        user_id = uuid4()
        await followers.add(
            MedicalTopicFollower.create(topic_id=TopicId(topic.id), user_id=user_id)
        )

        with pytest.raises(TopicAlreadyFollowedError):
            await service.execute(FollowTopicInput(topic_id=topic.id, user_id=user_id))

    async def test_commits_the_unit_of_work(self) -> None:
        service, topics, _, uow = _seeded()
        topic = MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        await topics.add(topic)

        await service.execute(FollowTopicInput(topic_id=topic.id, user_id=uuid4()))

        assert uow.committed is True

    async def test_publishes_a_topic_followed_event(self) -> None:
        service, topics, _, uow = _seeded()
        topic = MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        await topics.add(topic)

        await service.execute(FollowTopicInput(topic_id=topic.id, user_id=uuid4()))

        assert any(isinstance(e, TopicFollowed) for e in uow.published_events)
