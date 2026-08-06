"""Unit tests for `FeaturedTopicsService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.medical_topics.application.dto import FeaturedTopicsInput, SetTopicFeaturedInput
from app.modules.medical_topics.application.services.featured_topics_service import (
    FeaturedTopicsService,
)
from app.modules.medical_topics.domain.entities import MedicalTopic
from app.modules.medical_topics.domain.enums import TopicStatus, TopicVisibility
from app.modules.medical_topics.domain.events import MedicalTopicFeaturedChanged
from app.modules.medical_topics.domain.exceptions import TopicNotFoundError
from app.modules.medical_topics.domain.value_objects import TopicName, TopicSlug
from tests.unit.modules.medical_topics.application.fakes import (
    FakeMedicalTopicRepository,
    FakeUnitOfWork,
)


def _seeded() -> tuple[FeaturedTopicsService, FakeMedicalTopicRepository, FakeUnitOfWork]:
    topics = FakeMedicalTopicRepository()
    uow = FakeUnitOfWork()
    service = FeaturedTopicsService(topic_repository=topics, unit_of_work=uow)
    return service, topics, uow


async def _published_public_topic(
    topics: FakeMedicalTopicRepository, **overrides: object
) -> MedicalTopic:
    defaults: dict[str, object] = {
        "slug": TopicSlug(f"topic-{uuid4().hex[:8]}"),
        "name": TopicName("Test Topic"),
    }
    defaults.update(overrides)
    topic = MedicalTopic.create(**defaults)  # type: ignore[arg-type]
    topic.update_profile(status=TopicStatus.PUBLISHED, visibility=TopicVisibility.PUBLIC)
    await topics.add(topic)
    return topic


class TestListFeatured:
    async def test_returns_only_featured_topics(self) -> None:
        service, topics, _ = _seeded()
        featured = await _published_public_topic(topics, name=TopicName("Oncology"))
        featured.set_featured(True)
        await topics.add(featured)
        await _published_public_topic(topics, name=TopicName("Cardiology"))

        result = await service.list_featured(FeaturedTopicsInput())

        assert [item.topic_id for item in result.items] == [featured.id]

    async def test_no_featured_topics_returns_empty(self) -> None:
        service, topics, _ = _seeded()
        await _published_public_topic(topics, name=TopicName("Oncology"))

        result = await service.list_featured(FeaturedTopicsInput())

        assert result.total == 0


class TestSetFeatured:
    async def test_sets_a_topic_as_featured(self) -> None:
        service, topics, _ = _seeded()
        topic = MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        await topics.add(topic)

        await service.set_featured(SetTopicFeaturedInput(topic_id=topic.id, featured=True))

        stored = await topics.get_by_id(topic.id)
        assert stored is not None
        assert stored.is_featured is True

    async def test_unsets_a_featured_topic(self) -> None:
        service, topics, _ = _seeded()
        topic = MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        topic.set_featured(True)
        await topics.add(topic)

        await service.set_featured(SetTopicFeaturedInput(topic_id=topic.id, featured=False))

        stored = await topics.get_by_id(topic.id)
        assert stored is not None
        assert stored.is_featured is False

    async def test_unknown_topic_raises(self) -> None:
        service, _, _ = _seeded()
        with pytest.raises(TopicNotFoundError):
            await service.set_featured(SetTopicFeaturedInput(topic_id=uuid4(), featured=True))

    async def test_commits_the_unit_of_work(self) -> None:
        service, topics, uow = _seeded()
        topic = MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        await topics.add(topic)

        await service.set_featured(SetTopicFeaturedInput(topic_id=topic.id, featured=True))

        assert uow.committed is True

    async def test_publishes_a_medical_topic_featured_changed_event(self) -> None:
        service, topics, uow = _seeded()
        topic = MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        await topics.add(topic)

        await service.set_featured(SetTopicFeaturedInput(topic_id=topic.id, featured=True))

        assert any(isinstance(e, MedicalTopicFeaturedChanged) for e in uow.published_events)
