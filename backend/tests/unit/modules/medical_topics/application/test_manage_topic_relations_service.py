"""Unit tests for `ManageTopicRelationsService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.medical_topics.application.dto import (
    CreateTopicRelationInput,
    DeleteTopicRelationInput,
)
from app.modules.medical_topics.application.services.manage_topic_relations_service import (
    ManageTopicRelationsService,
)
from app.modules.medical_topics.domain.entities import MedicalTopic
from app.modules.medical_topics.domain.exceptions import (
    DuplicateTopicRelationError,
    TopicCannotRelateToItselfError,
    TopicNotFoundError,
    TopicRelationNotFoundError,
)
from app.modules.medical_topics.domain.value_objects import TopicName, TopicSlug
from tests.unit.modules.medical_topics.application.fakes import (
    FakeMedicalTopicRelationRepository,
    FakeMedicalTopicRepository,
    FakeUnitOfWork,
)


def _seeded() -> (
    tuple[
        ManageTopicRelationsService,
        FakeMedicalTopicRelationRepository,
        FakeMedicalTopicRepository,
        FakeUnitOfWork,
    ]
):
    relations = FakeMedicalTopicRelationRepository()
    topics = FakeMedicalTopicRepository()
    uow = FakeUnitOfWork()
    service = ManageTopicRelationsService(
        relation_repository=relations, topic_repository=topics, unit_of_work=uow
    )
    return service, relations, topics, uow


async def _add_topic(topics: FakeMedicalTopicRepository, name: str) -> MedicalTopic:
    topic = MedicalTopic.create(slug=TopicSlug(f"topic-{uuid4().hex[:8]}"), name=TopicName(name))
    await topics.add(topic)
    return topic


class TestAddRelation:
    async def test_creates_a_relation(self) -> None:
        service, relations, topics, _ = _seeded()
        a = await _add_topic(topics, "A")
        b = await _add_topic(topics, "B")

        summary = await service.add_relation(
            CreateTopicRelationInput(topic_id=a.id, related_topic_id=b.id)
        )

        assert summary.topic_id == a.id
        assert summary.related_topic_id == b.id
        assert await relations.exists(a.id, b.id) is True

    async def test_unknown_topic_raises(self) -> None:
        service, _, topics, _ = _seeded()
        a = await _add_topic(topics, "A")
        with pytest.raises(TopicNotFoundError):
            await service.add_relation(
                CreateTopicRelationInput(topic_id=a.id, related_topic_id=uuid4())
            )

    async def test_unknown_related_topic_raises(self) -> None:
        service, _, topics, _ = _seeded()
        a = await _add_topic(topics, "A")
        with pytest.raises(TopicNotFoundError):
            await service.add_relation(
                CreateTopicRelationInput(topic_id=uuid4(), related_topic_id=a.id)
            )

    async def test_relating_a_topic_to_itself_raises(self) -> None:
        service, _, topics, _ = _seeded()
        a = await _add_topic(topics, "A")
        with pytest.raises(TopicCannotRelateToItselfError):
            await service.add_relation(
                CreateTopicRelationInput(topic_id=a.id, related_topic_id=a.id)
            )

    async def test_duplicate_relation_raises(self) -> None:
        service, _, topics, _ = _seeded()
        a = await _add_topic(topics, "A")
        b = await _add_topic(topics, "B")
        await service.add_relation(CreateTopicRelationInput(topic_id=a.id, related_topic_id=b.id))
        with pytest.raises(DuplicateTopicRelationError):
            await service.add_relation(
                CreateTopicRelationInput(topic_id=a.id, related_topic_id=b.id)
            )

    async def test_reverse_duplicate_relation_raises(self) -> None:
        """`(B, A)` is the same relation as `(A, B)` — the existence
        check is symmetric."""
        service, _, topics, _ = _seeded()
        a = await _add_topic(topics, "A")
        b = await _add_topic(topics, "B")
        await service.add_relation(CreateTopicRelationInput(topic_id=a.id, related_topic_id=b.id))
        with pytest.raises(DuplicateTopicRelationError):
            await service.add_relation(
                CreateTopicRelationInput(topic_id=b.id, related_topic_id=a.id)
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, topics, uow = _seeded()
        a = await _add_topic(topics, "A")
        b = await _add_topic(topics, "B")
        await service.add_relation(CreateTopicRelationInput(topic_id=a.id, related_topic_id=b.id))
        assert uow.committed is True


class TestListRelations:
    async def test_lists_relations_for_the_topic(self) -> None:
        service, _, topics, _ = _seeded()
        a = await _add_topic(topics, "A")
        b = await _add_topic(topics, "B")
        created = await service.add_relation(
            CreateTopicRelationInput(topic_id=a.id, related_topic_id=b.id)
        )

        results = await service.list_relations(a.id)

        assert [r.relation_id for r in results] == [created.relation_id]

    async def test_no_relations_returns_empty(self) -> None:
        service, _, topics, _ = _seeded()
        a = await _add_topic(topics, "A")
        assert await service.list_relations(a.id) == []


class TestDeleteRelation:
    async def test_removes_the_relation(self) -> None:
        service, relations, topics, _ = _seeded()
        a = await _add_topic(topics, "A")
        b = await _add_topic(topics, "B")
        created = await service.add_relation(
            CreateTopicRelationInput(topic_id=a.id, related_topic_id=b.id)
        )

        await service.delete_relation(DeleteTopicRelationInput(relation_id=created.relation_id))

        assert await relations.get_by_id(created.relation_id) is None

    async def test_unknown_relation_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(TopicRelationNotFoundError):
            await service.delete_relation(DeleteTopicRelationInput(relation_id=uuid4()))
