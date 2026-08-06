"""Unit tests for `DeleteTopicService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.medical_topics.application.dto import DeleteTopicInput
from app.modules.medical_topics.application.services.delete_topic_service import (
    DeleteTopicService,
)
from app.modules.medical_topics.domain.entities import MedicalTopic
from app.modules.medical_topics.domain.exceptions import TopicNotFoundError
from app.modules.medical_topics.domain.value_objects import TopicName, TopicSlug
from tests.unit.modules.medical_topics.application.fakes import (
    FakeMedicalTopicRepository,
    FakeUnitOfWork,
)


def _seeded() -> tuple[DeleteTopicService, FakeMedicalTopicRepository, FakeUnitOfWork]:
    topics = FakeMedicalTopicRepository()
    uow = FakeUnitOfWork()
    service = DeleteTopicService(topic_repository=topics, unit_of_work=uow)
    return service, topics, uow


class TestDeleteTopic:
    async def test_removes_the_topic(self) -> None:
        service, topics, _ = _seeded()
        topic = MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        await topics.add(topic)

        await service.execute(DeleteTopicInput(topic_id=topic.id))

        assert await topics.get_by_id(topic.id) is None

    async def test_unknown_topic_raises(self) -> None:
        service, _, _ = _seeded()
        with pytest.raises(TopicNotFoundError):
            await service.execute(DeleteTopicInput(topic_id=uuid4()))

    async def test_commits_the_unit_of_work(self) -> None:
        service, topics, uow = _seeded()
        topic = MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        await topics.add(topic)

        await service.execute(DeleteTopicInput(topic_id=topic.id))

        assert uow.committed is True
