"""Unit tests for `TrendingTopicsService`, using in-memory fakes."""

from uuid import uuid4

from app.modules.medical_topics.application.dto import TrendingTopicsInput
from app.modules.medical_topics.application.services.trending_topics_service import (
    TrendingTopicsService,
)
from app.modules.medical_topics.domain.entities import MedicalTopic
from app.modules.medical_topics.domain.enums import TopicStatus, TopicVisibility
from app.modules.medical_topics.domain.value_objects import TopicName, TopicSlug
from tests.unit.modules.medical_topics.application.fakes import FakeMedicalTopicRepository


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


class TestTrendingTopics:
    async def test_orders_by_trending_score_descending(self) -> None:
        topics = FakeMedicalTopicRepository()
        service = TrendingTopicsService(topic_repository=topics)
        low = await _published_public_topic(topics, name=TopicName("Low"))
        low.update_trending_score(2.0)
        await topics.add(low)
        high = await _published_public_topic(topics, name=TopicName("High"))
        high.update_trending_score(50.0)
        await topics.add(high)

        result = await service.get_trending(TrendingTopicsInput())

        assert [item.topic_id for item in result.items] == [high.id, low.id]

    async def test_excludes_draft_topics(self) -> None:
        topics = FakeMedicalTopicRepository()
        service = TrendingTopicsService(topic_repository=topics)
        draft = MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        await topics.add(draft)

        result = await service.get_trending(TrendingTopicsInput())

        assert result.total == 0

    async def test_filters_by_specialty_id(self) -> None:
        topics = FakeMedicalTopicRepository()
        service = TrendingTopicsService(topic_repository=topics)
        specialty_id = uuid4()
        matching = await _published_public_topic(
            topics, name=TopicName("Oncology"), specialty_id=specialty_id
        )
        await _published_public_topic(topics, name=TopicName("Cardiology"))

        result = await service.get_trending(TrendingTopicsInput(specialty_id=specialty_id))

        assert [item.topic_id for item in result.items] == [matching.id]

    async def test_respects_pagination(self) -> None:
        topics = FakeMedicalTopicRepository()
        service = TrendingTopicsService(topic_repository=topics)
        for i in range(3):
            await _published_public_topic(topics, name=TopicName(f"Topic {i}"))

        result = await service.get_trending(TrendingTopicsInput(offset=1, limit=1))

        assert len(result.items) == 1
        assert result.total == 3
