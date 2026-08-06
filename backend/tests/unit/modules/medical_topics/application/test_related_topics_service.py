"""Unit tests for `RelatedTopicsService`, using in-memory fakes."""

from uuid import uuid4

from app.modules.medical_topics.application.dto import RelatedTopicsInput
from app.modules.medical_topics.application.services.related_topics_service import (
    RelatedTopicsService,
)
from app.modules.medical_topics.domain.entities import MedicalTopic, MedicalTopicRelation
from app.modules.medical_topics.domain.enums import TopicStatus, TopicVisibility
from app.modules.medical_topics.domain.value_objects import TopicId, TopicName, TopicSlug
from tests.unit.modules.medical_topics.application.fakes import (
    FakeMedicalTopicRelationRepository,
    FakeMedicalTopicRepository,
)


def _seeded() -> (
    tuple[RelatedTopicsService, FakeMedicalTopicRepository, FakeMedicalTopicRelationRepository]
):
    topics = FakeMedicalTopicRepository()
    relations = FakeMedicalTopicRelationRepository()
    service = RelatedTopicsService(topic_repository=topics, relation_repository=relations)
    return service, topics, relations


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


class TestRelatedTopics:
    async def test_returns_the_related_topic(self) -> None:
        service, topics, relations = _seeded()
        a = await _published_public_topic(topics, name=TopicName("A"))
        b = await _published_public_topic(topics, name=TopicName("B"))
        await relations.add(
            MedicalTopicRelation.create(topic_id=TopicId(a.id), related_topic_id=b.id)
        )

        result = await service.get_related(RelatedTopicsInput(topic_id=a.id))

        assert [item.topic_id for item in result.items] == [b.id]

    async def test_is_symmetric(self) -> None:
        """A relation `(A, B)` makes B appear in A's related list *and*
        A appear in B's — see `MedicalTopicRelationRepository.list_related`'s
        own docstring."""
        service, topics, relations = _seeded()
        a = await _published_public_topic(topics, name=TopicName("A"))
        b = await _published_public_topic(topics, name=TopicName("B"))
        await relations.add(
            MedicalTopicRelation.create(topic_id=TopicId(a.id), related_topic_id=b.id)
        )

        result = await service.get_related(RelatedTopicsInput(topic_id=b.id))

        assert [item.topic_id for item in result.items] == [a.id]

    async def test_excludes_non_discoverable_related_topics(self) -> None:
        service, topics, relations = _seeded()
        a = await _published_public_topic(topics, name=TopicName("A"))
        draft_related = MedicalTopic.create(slug=TopicSlug("draft-topic"), name=TopicName("Draft"))
        await topics.add(draft_related)
        await relations.add(
            MedicalTopicRelation.create(topic_id=TopicId(a.id), related_topic_id=draft_related.id)
        )

        result = await service.get_related(RelatedTopicsInput(topic_id=a.id))

        assert result.items == ()

    async def test_no_relations_returns_empty(self) -> None:
        service, topics, _ = _seeded()
        a = await _published_public_topic(topics, name=TopicName("A"))

        result = await service.get_related(RelatedTopicsInput(topic_id=a.id))

        assert result.items == ()

    async def test_respects_limit(self) -> None:
        service, topics, relations = _seeded()
        a = await _published_public_topic(topics, name=TopicName("A"))
        for i in range(3):
            other = await _published_public_topic(topics, name=TopicName(f"Other {i}"))
            await relations.add(
                MedicalTopicRelation.create(topic_id=TopicId(a.id), related_topic_id=other.id)
            )

        result = await service.get_related(RelatedTopicsInput(topic_id=a.id, limit=2))

        assert len(result.items) == 2
