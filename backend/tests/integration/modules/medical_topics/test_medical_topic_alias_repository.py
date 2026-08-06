"""Integration tests for `SqlAlchemyMedicalTopicAliasRepository`,
including the `(topic_id, alias)` uniqueness constraint and its FK to
`medical_topics`, against a real PostgreSQL instance."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.medical_topics._helpers import unique_suffix

from app.modules.medical_topics.domain.entities import MedicalTopic, MedicalTopicAlias
from app.modules.medical_topics.domain.value_objects import TopicId, TopicName, TopicSlug
from app.modules.medical_topics.infrastructure.models import MedicalTopicAliasModel
from app.modules.medical_topics.infrastructure.repositories import (
    SqlAlchemyMedicalTopicAliasRepository,
    SqlAlchemyMedicalTopicRepository,
)


async def _persist_topic(db_session: AsyncSession) -> MedicalTopic:
    repo = SqlAlchemyMedicalTopicRepository(db_session)
    topic = MedicalTopic.create(
        slug=TopicSlug(f"topic-{unique_suffix()}"), name=TopicName("Test Topic")
    )
    await repo.add(topic)
    await db_session.commit()
    return topic


class TestMedicalTopicAliasRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        topic = await _persist_topic(db_session)
        repo = SqlAlchemyMedicalTopicAliasRepository(db_session)

        alias = MedicalTopicAlias.create(
            topic_id=TopicId(topic.id), alias=TopicName("heart arrhythmia")
        )
        await repo.add(alias)
        await db_session.commit()

        reloaded = await repo.get_by_id(alias.id)
        assert reloaded is not None
        assert reloaded.topic_id.value == topic.id
        assert str(reloaded.alias) == "heart arrhythmia"


class TestGetById:
    async def test_returns_none_for_an_unknown_id(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicAliasRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None


class TestListByTopic:
    async def test_scopes_to_the_topic(self, db_session: AsyncSession) -> None:
        topic_a = await _persist_topic(db_session)
        topic_b = await _persist_topic(db_session)
        repo = SqlAlchemyMedicalTopicAliasRepository(db_session)

        alias_a = MedicalTopicAlias.create(topic_id=TopicId(topic_a.id), alias=TopicName("alias a"))
        alias_b = MedicalTopicAlias.create(topic_id=TopicId(topic_b.id), alias=TopicName("alias b"))
        await repo.add(alias_a)
        await repo.add(alias_b)
        await db_session.commit()

        results = await repo.list_by_topic(topic_a.id)
        assert [a.id for a in results] == [alias_a.id]

    async def test_no_aliases_returns_empty(self, db_session: AsyncSession) -> None:
        topic = await _persist_topic(db_session)
        repo = SqlAlchemyMedicalTopicAliasRepository(db_session)
        assert await repo.list_by_topic(topic.id) == []


class TestSearchByAlias:
    async def test_matches_by_partial_alias(self, db_session: AsyncSession) -> None:
        topic = await _persist_topic(db_session)
        repo = SqlAlchemyMedicalTopicAliasRepository(db_session)
        suffix = unique_suffix()
        target = MedicalTopicAlias.create(
            topic_id=TopicId(topic.id), alias=TopicName(f"heart-{suffix}")
        )
        other = MedicalTopicAlias.create(
            topic_id=TopicId(topic.id), alias=TopicName(f"lung-{suffix}")
        )
        await repo.add(target)
        await repo.add(other)
        await db_session.commit()

        results, total = await repo.search_by_alias(f"heart-{suffix}")

        assert total == 1
        assert [a.id for a in results] == [target.id]

    async def test_no_matches_returns_empty(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicAliasRepository(db_session)
        results, total = await repo.search_by_alias(f"no-such-alias-{unique_suffix()}")
        assert total == 0
        assert results == []


class TestUniqueTopicAliasConstraint:
    async def test_duplicate_alias_for_the_same_topic_violates_the_constraint(
        self, db_session: AsyncSession
    ) -> None:
        topic = await _persist_topic(db_session)
        repo = SqlAlchemyMedicalTopicAliasRepository(db_session)
        alias_text = TopicName(f"alias-{unique_suffix()}")

        first = MedicalTopicAlias.create(topic_id=TopicId(topic.id), alias=alias_text)
        await repo.add(first)
        await db_session.commit()

        second = MedicalTopicAlias.create(topic_id=TopicId(topic.id), alias=alias_text)
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestRemove:
    async def test_removes_the_alias_row(self, db_session: AsyncSession) -> None:
        topic = await _persist_topic(db_session)
        repo = SqlAlchemyMedicalTopicAliasRepository(db_session)
        alias = MedicalTopicAlias.create(
            topic_id=TopicId(topic.id), alias=TopicName("heart arrhythmia")
        )
        await repo.add(alias)
        await db_session.commit()

        await repo.remove(alias.id)
        await db_session.commit()

        assert await repo.get_by_id(alias.id) is None

    async def test_is_a_no_op_for_an_unknown_id(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicAliasRepository(db_session)
        await repo.remove(uuid4())  # must not raise
        await db_session.commit()


class TestMedicalTopicAliasRequiresValidReferences:
    async def test_nonexistent_topic_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyMedicalTopicAliasRepository(db_session)
        alias = MedicalTopicAlias.create(topic_id=TopicId(uuid4()), alias=TopicName("alias"))
        await repo.add(alias)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestMedicalTopicAliasModelDirectInsert:
    async def test_model_insert_and_query(self, db_session: AsyncSession) -> None:
        topic = await _persist_topic(db_session)
        model = MedicalTopicAliasModel(topic_id=topic.id, alias="direct alias")
        db_session.add(model)
        await db_session.commit()

        reloaded = await db_session.get(MedicalTopicAliasModel, model.id)
        assert reloaded is not None
        assert reloaded.alias == "direct alias"
