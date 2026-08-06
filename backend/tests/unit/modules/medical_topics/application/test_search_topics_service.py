"""Unit tests for `SearchTopicsService`, using in-memory fakes."""

from uuid import uuid4

from app.modules.medical_topics.application.dto import SearchTopicsInput
from app.modules.medical_topics.application.services.search_topics_service import (
    SearchTopicsService,
)
from app.modules.medical_topics.domain.entities import MedicalTopic, MedicalTopicAlias
from app.modules.medical_topics.domain.enums import TopicStatus, TopicVisibility
from app.modules.medical_topics.domain.value_objects import TopicId, TopicName, TopicSlug
from tests.unit.modules.medical_topics.application.fakes import (
    FakeMedicalTopicAliasRepository,
    FakeMedicalTopicRepository,
)


def _seeded() -> (
    tuple[SearchTopicsService, FakeMedicalTopicRepository, FakeMedicalTopicAliasRepository]
):
    topics = FakeMedicalTopicRepository()
    aliases = FakeMedicalTopicAliasRepository()
    service = SearchTopicsService(topic_repository=topics, alias_repository=aliases)
    return service, topics, aliases


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


class TestSearchTopics:
    async def test_matches_by_name(self) -> None:
        service, topics, _ = _seeded()
        oncology = await _published_public_topic(topics, name=TopicName("Oncology"))
        await _published_public_topic(topics, name=TopicName("Cardiology"))

        output = await service.search(SearchTopicsInput(query="onco"))

        assert output.total >= 1
        assert any(item.topic_id == oncology.id for item in output.items)

    async def test_excludes_draft_topics(self) -> None:
        service, topics, _ = _seeded()
        draft = MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        await topics.add(draft)

        output = await service.search(SearchTopicsInput(query="onco"))

        assert output.total == 0

    async def test_excludes_non_public_topics(self) -> None:
        service, topics, _ = _seeded()
        topic = MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        topic.update_profile(status=TopicStatus.PUBLISHED, visibility=TopicVisibility.PRIVATE)
        await topics.add(topic)

        output = await service.search(SearchTopicsInput(query="onco"))

        assert output.total == 0

    async def test_matches_via_alias(self) -> None:
        service, topics, aliases = _seeded()
        topic = await _published_public_topic(topics, name=TopicName("Cardiac Arrhythmia"))
        await aliases.add(
            MedicalTopicAlias.create(
                topic_id=TopicId(topic.id), alias=TopicName("heart arrhythmia")
            )
        )

        output = await service.search(SearchTopicsInput(query="heart arrhythmia"))

        assert any(item.topic_id == topic.id for item in output.items)

    async def test_filters_by_specialty_id(self) -> None:
        service, topics, _ = _seeded()
        specialty_id = uuid4()
        matching = await _published_public_topic(
            topics, name=TopicName("Oncology"), specialty_id=specialty_id
        )
        await _published_public_topic(topics, name=TopicName("Oncology Two"))

        output = await service.search(
            SearchTopicsInput(query="oncology", specialty_id=specialty_id)
        )

        assert [item.topic_id for item in output.items] == [matching.id]

    async def test_no_matches_returns_empty(self) -> None:
        service, topics, _ = _seeded()
        await _published_public_topic(topics, name=TopicName("Oncology"))

        output = await service.search(SearchTopicsInput(query="nephrology"))

        assert output.total == 0
        assert output.items == ()
