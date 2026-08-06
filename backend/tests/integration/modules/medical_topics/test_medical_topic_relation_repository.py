"""Integration tests for `SqlAlchemyMedicalTopicRelationRepository`,
including the symmetric `list_related`/`exists` queries, the
`(topic_id, related_topic_id)` uniqueness constraint, and its FKs to
`medical_topics`, against a real PostgreSQL instance."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.medical_topics._helpers import unique_suffix

from app.modules.medical_topics.domain.entities import MedicalTopic, MedicalTopicRelation
from app.modules.medical_topics.domain.enums import TopicRelationType
from app.modules.medical_topics.domain.value_objects import TopicId, TopicName, TopicSlug
from app.modules.medical_topics.infrastructure.models import MedicalTopicRelationModel
from app.modules.medical_topics.infrastructure.repositories import (
    SqlAlchemyMedicalTopicRelationRepository,
    SqlAlchemyMedicalTopicRepository,
)


async def _persist_topic(db_session: AsyncSession, name: str = "Test Topic") -> MedicalTopic:
    repo = SqlAlchemyMedicalTopicRepository(db_session)
    topic = MedicalTopic.create(slug=TopicSlug(f"topic-{unique_suffix()}"), name=TopicName(name))
    await repo.add(topic)
    await db_session.commit()
    return topic


class TestMedicalTopicRelationRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        a = await _persist_topic(db_session, "A")
        b = await _persist_topic(db_session, "B")
        repo = SqlAlchemyMedicalTopicRelationRepository(db_session)

        relation = MedicalTopicRelation.create(
            topic_id=TopicId(a.id), related_topic_id=b.id, relation_type=TopicRelationType.SEE_ALSO
        )
        await repo.add(relation)
        await db_session.commit()

        reloaded = await repo.get_by_id(relation.id)
        assert reloaded is not None
        assert reloaded.topic_id.value == a.id
        assert reloaded.related_topic_id == b.id
        assert reloaded.relation_type is TopicRelationType.SEE_ALSO


class TestGetById:
    async def test_returns_none_for_an_unknown_id(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRelationRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None


class TestListRelated:
    async def test_returns_the_related_topic(self, db_session: AsyncSession) -> None:
        a = await _persist_topic(db_session, "A")
        b = await _persist_topic(db_session, "B")
        repo = SqlAlchemyMedicalTopicRelationRepository(db_session)
        relation = MedicalTopicRelation.create(topic_id=TopicId(a.id), related_topic_id=b.id)
        await repo.add(relation)
        await db_session.commit()

        results = await repo.list_related(a.id)

        assert [r.id for r in results] == [relation.id]

    async def test_is_symmetric(self, db_session: AsyncSession) -> None:
        a = await _persist_topic(db_session, "A")
        b = await _persist_topic(db_session, "B")
        repo = SqlAlchemyMedicalTopicRelationRepository(db_session)
        relation = MedicalTopicRelation.create(topic_id=TopicId(a.id), related_topic_id=b.id)
        await repo.add(relation)
        await db_session.commit()

        results = await repo.list_related(b.id)

        assert [r.id for r in results] == [relation.id]

    async def test_no_relations_returns_empty(self, db_session: AsyncSession) -> None:
        a = await _persist_topic(db_session, "A")
        repo = SqlAlchemyMedicalTopicRelationRepository(db_session)
        assert await repo.list_related(a.id) == []


class TestExists:
    async def test_true_for_a_direct_pair(self, db_session: AsyncSession) -> None:
        a = await _persist_topic(db_session, "A")
        b = await _persist_topic(db_session, "B")
        repo = SqlAlchemyMedicalTopicRelationRepository(db_session)
        await repo.add(MedicalTopicRelation.create(topic_id=TopicId(a.id), related_topic_id=b.id))
        await db_session.commit()

        assert await repo.exists(a.id, b.id) is True

    async def test_true_for_the_reverse_pair(self, db_session: AsyncSession) -> None:
        a = await _persist_topic(db_session, "A")
        b = await _persist_topic(db_session, "B")
        repo = SqlAlchemyMedicalTopicRelationRepository(db_session)
        await repo.add(MedicalTopicRelation.create(topic_id=TopicId(a.id), related_topic_id=b.id))
        await db_session.commit()

        assert await repo.exists(b.id, a.id) is True

    async def test_false_when_no_relation_exists(self, db_session: AsyncSession) -> None:
        a = await _persist_topic(db_session, "A")
        b = await _persist_topic(db_session, "B")
        repo = SqlAlchemyMedicalTopicRelationRepository(db_session)
        assert await repo.exists(a.id, b.id) is False


class TestUniqueTopicRelationConstraint:
    async def test_duplicate_pair_violates_the_constraint(self, db_session: AsyncSession) -> None:
        a = await _persist_topic(db_session, "A")
        b = await _persist_topic(db_session, "B")
        repo = SqlAlchemyMedicalTopicRelationRepository(db_session)

        first = MedicalTopicRelation.create(topic_id=TopicId(a.id), related_topic_id=b.id)
        await repo.add(first)
        await db_session.commit()

        second = MedicalTopicRelation.create(topic_id=TopicId(a.id), related_topic_id=b.id)
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestRemove:
    async def test_removes_the_relation_row(self, db_session: AsyncSession) -> None:
        a = await _persist_topic(db_session, "A")
        b = await _persist_topic(db_session, "B")
        repo = SqlAlchemyMedicalTopicRelationRepository(db_session)
        relation = MedicalTopicRelation.create(topic_id=TopicId(a.id), related_topic_id=b.id)
        await repo.add(relation)
        await db_session.commit()

        await repo.remove(relation.id)
        await db_session.commit()

        assert await repo.get_by_id(relation.id) is None

    async def test_is_a_no_op_for_an_unknown_id(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRelationRepository(db_session)
        await repo.remove(uuid4())  # must not raise
        await db_session.commit()


class TestMedicalTopicRelationRequiresValidReferences:
    async def test_nonexistent_topic_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        b = await _persist_topic(db_session, "B")
        repo = SqlAlchemyMedicalTopicRelationRepository(db_session)
        relation = MedicalTopicRelation.create(topic_id=TopicId(uuid4()), related_topic_id=b.id)
        await repo.add(relation)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_related_topic_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        a = await _persist_topic(db_session, "A")
        repo = SqlAlchemyMedicalTopicRelationRepository(db_session)
        relation = MedicalTopicRelation.create(topic_id=TopicId(a.id), related_topic_id=uuid4())
        await repo.add(relation)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestMedicalTopicRelationModelDirectInsert:
    async def test_model_insert_and_query(self, db_session: AsyncSession) -> None:
        a = await _persist_topic(db_session, "A")
        b = await _persist_topic(db_session, "B")
        model = MedicalTopicRelationModel(topic_id=a.id, related_topic_id=b.id)
        db_session.add(model)
        await db_session.commit()

        reloaded = await db_session.get(MedicalTopicRelationModel, model.id)
        assert reloaded is not None
        assert reloaded.relation_type is TopicRelationType.RELATED
