"""Unit tests for `ManageTopicAliasesService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.medical_topics.application.dto import CreateTopicAliasInput, DeleteTopicAliasInput
from app.modules.medical_topics.application.services.manage_topic_aliases_service import (
    ManageTopicAliasesService,
)
from app.modules.medical_topics.domain.entities import MedicalTopic
from app.modules.medical_topics.domain.exceptions import (
    DuplicateTopicAliasError,
    TopicAliasNotFoundError,
    TopicNotFoundError,
)
from app.modules.medical_topics.domain.value_objects import TopicName, TopicSlug
from tests.unit.modules.medical_topics.application.fakes import (
    FakeMedicalTopicAliasRepository,
    FakeMedicalTopicRepository,
    FakeUnitOfWork,
)


def _seeded() -> (
    tuple[
        ManageTopicAliasesService,
        FakeMedicalTopicAliasRepository,
        FakeMedicalTopicRepository,
        MedicalTopic,
        FakeUnitOfWork,
    ]
):
    aliases = FakeMedicalTopicAliasRepository()
    topics = FakeMedicalTopicRepository()
    uow = FakeUnitOfWork()
    service = ManageTopicAliasesService(
        alias_repository=aliases, topic_repository=topics, unit_of_work=uow
    )
    return (
        service,
        aliases,
        topics,
        MedicalTopic.create(
            slug=TopicSlug("cardiac-arrhythmia"), name=TopicName("Cardiac Arrhythmia")
        ),
        uow,
    )


class TestCreateAlias:
    async def test_creates_an_alias(self) -> None:
        service, aliases, topics, topic, _ = _seeded()
        await topics.add(topic)

        summary = await service.create_alias(
            CreateTopicAliasInput(topic_id=topic.id, alias="heart arrhythmia")
        )

        assert summary.alias == "heart arrhythmia"
        stored = await aliases.get_by_id(summary.alias_id)
        assert stored is not None

    async def test_unknown_topic_raises(self) -> None:
        service, _, _, _, _ = _seeded()
        with pytest.raises(TopicNotFoundError):
            await service.create_alias(
                CreateTopicAliasInput(topic_id=uuid4(), alias="heart arrhythmia")
            )

    async def test_duplicate_alias_raises(self) -> None:
        service, _, topics, topic, _ = _seeded()
        await topics.add(topic)
        await service.create_alias(
            CreateTopicAliasInput(topic_id=topic.id, alias="heart arrhythmia")
        )
        with pytest.raises(DuplicateTopicAliasError):
            await service.create_alias(
                CreateTopicAliasInput(topic_id=topic.id, alias="heart arrhythmia")
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, topics, topic, uow = _seeded()
        await topics.add(topic)
        await service.create_alias(
            CreateTopicAliasInput(topic_id=topic.id, alias="heart arrhythmia")
        )
        assert uow.committed is True


class TestListAliases:
    async def test_lists_aliases_for_the_topic(self) -> None:
        service, _, topics, topic, _ = _seeded()
        await topics.add(topic)
        created = await service.create_alias(
            CreateTopicAliasInput(topic_id=topic.id, alias="heart arrhythmia")
        )

        results = await service.list_aliases(topic.id)

        assert [a.alias_id for a in results] == [created.alias_id]

    async def test_no_aliases_returns_empty(self) -> None:
        service, _, topics, topic, _ = _seeded()
        await topics.add(topic)
        assert await service.list_aliases(topic.id) == []


class TestDeleteAlias:
    async def test_removes_the_alias(self) -> None:
        service, aliases, topics, topic, _ = _seeded()
        await topics.add(topic)
        created = await service.create_alias(
            CreateTopicAliasInput(topic_id=topic.id, alias="heart arrhythmia")
        )

        await service.delete_alias(DeleteTopicAliasInput(alias_id=created.alias_id))

        assert await aliases.get_by_id(created.alias_id) is None

    async def test_unknown_alias_raises(self) -> None:
        service, _, _, _, _ = _seeded()
        with pytest.raises(TopicAliasNotFoundError):
            await service.delete_alias(DeleteTopicAliasInput(alias_id=uuid4()))
