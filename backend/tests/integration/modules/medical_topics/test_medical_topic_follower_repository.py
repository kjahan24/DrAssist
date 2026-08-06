"""Integration tests for `SqlAlchemyMedicalTopicFollowerRepository`,
including the `(topic_id, user_id)` uniqueness constraint and its FKs to
`medical_topics`/`users`, against a real PostgreSQL instance."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.medical_topics._helpers import persist_user, unique_suffix

from app.modules.medical_topics.domain.entities import MedicalTopic, MedicalTopicFollower
from app.modules.medical_topics.domain.value_objects import TopicId, TopicName, TopicSlug
from app.modules.medical_topics.infrastructure.models import MedicalTopicFollowerModel
from app.modules.medical_topics.infrastructure.repositories import (
    SqlAlchemyMedicalTopicFollowerRepository,
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


class TestMedicalTopicFollowerRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        topic = await _persist_topic(db_session)
        user = await persist_user(db_session)
        repo = SqlAlchemyMedicalTopicFollowerRepository(db_session)

        follower = MedicalTopicFollower.create(topic_id=TopicId(topic.id), user_id=user.id)
        await repo.add(follower)
        await db_session.commit()

        reloaded = await repo.get_by_topic_and_user(topic.id, user.id)
        assert reloaded is not None
        assert reloaded.topic_id.value == topic.id
        assert reloaded.user_id == user.id


class TestGetByTopicAndUser:
    async def test_returns_none_when_absent(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicFollowerRepository(db_session)
        assert await repo.get_by_topic_and_user(uuid4(), uuid4()) is None


class TestListByTopic:
    async def test_scopes_to_the_topic(self, db_session: AsyncSession) -> None:
        topic_a = await _persist_topic(db_session)
        topic_b = await _persist_topic(db_session)
        user_a = await persist_user(db_session)
        user_b = await persist_user(db_session)
        repo = SqlAlchemyMedicalTopicFollowerRepository(db_session)

        follower_a = MedicalTopicFollower.create(topic_id=TopicId(topic_a.id), user_id=user_a.id)
        follower_b = MedicalTopicFollower.create(topic_id=TopicId(topic_b.id), user_id=user_b.id)
        await repo.add(follower_a)
        await repo.add(follower_b)
        await db_session.commit()

        results = await repo.list_by_topic(topic_a.id)
        assert [f.id for f in results] == [follower_a.id]

    async def test_respects_pagination(self, db_session: AsyncSession) -> None:
        topic = await _persist_topic(db_session)
        repo = SqlAlchemyMedicalTopicFollowerRepository(db_session)
        for _ in range(3):
            user = await persist_user(db_session)
            await repo.add(MedicalTopicFollower.create(topic_id=TopicId(topic.id), user_id=user.id))
            await db_session.commit()

        page = await repo.list_by_topic(topic.id, offset=1, limit=1)
        assert len(page) == 1


class TestListByUser:
    async def test_scopes_to_the_user(self, db_session: AsyncSession) -> None:
        topic_a = await _persist_topic(db_session)
        topic_b = await _persist_topic(db_session)
        user = await persist_user(db_session)
        other_user = await persist_user(db_session)
        repo = SqlAlchemyMedicalTopicFollowerRepository(db_session)

        membership_a = MedicalTopicFollower.create(topic_id=TopicId(topic_a.id), user_id=user.id)
        membership_b = MedicalTopicFollower.create(
            topic_id=TopicId(topic_b.id), user_id=other_user.id
        )
        await repo.add(membership_a)
        await repo.add(membership_b)
        await db_session.commit()

        results = await repo.list_by_user(user.id)
        assert [f.id for f in results] == [membership_a.id]


class TestCountByTopic:
    async def test_counts_followers_of_the_topic(self, db_session: AsyncSession) -> None:
        topic = await _persist_topic(db_session)
        repo = SqlAlchemyMedicalTopicFollowerRepository(db_session)
        for _ in range(3):
            user = await persist_user(db_session)
            await repo.add(MedicalTopicFollower.create(topic_id=TopicId(topic.id), user_id=user.id))
        await db_session.commit()

        assert await repo.count_by_topic(topic.id) == 3

    async def test_returns_zero_for_a_topic_with_no_followers(
        self, db_session: AsyncSession
    ) -> None:
        topic = await _persist_topic(db_session)
        repo = SqlAlchemyMedicalTopicFollowerRepository(db_session)
        assert await repo.count_by_topic(topic.id) == 0


class TestRemove:
    async def test_removes_the_follower_row(self, db_session: AsyncSession) -> None:
        topic = await _persist_topic(db_session)
        user = await persist_user(db_session)
        repo = SqlAlchemyMedicalTopicFollowerRepository(db_session)
        follower = MedicalTopicFollower.create(topic_id=TopicId(topic.id), user_id=user.id)
        await repo.add(follower)
        await db_session.commit()

        await repo.remove(topic.id, user.id)
        await db_session.commit()

        assert await repo.get_by_topic_and_user(topic.id, user.id) is None

    async def test_is_a_no_op_when_not_following(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicFollowerRepository(db_session)
        await repo.remove(uuid4(), uuid4())  # must not raise
        await db_session.commit()


class TestUniqueTopicUserConstraint:
    async def test_duplicate_follower_row_violates_the_constraint(
        self, db_session: AsyncSession
    ) -> None:
        topic = await _persist_topic(db_session)
        user = await persist_user(db_session)
        repo = SqlAlchemyMedicalTopicFollowerRepository(db_session)

        first = MedicalTopicFollower.create(topic_id=TopicId(topic.id), user_id=user.id)
        await repo.add(first)
        await db_session.commit()

        second = MedicalTopicFollower.create(topic_id=TopicId(topic.id), user_id=user.id)
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestMedicalTopicFollowerRequiresValidReferences:
    async def test_nonexistent_topic_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        user = await persist_user(db_session)
        repo = SqlAlchemyMedicalTopicFollowerRepository(db_session)

        follower = MedicalTopicFollower.create(topic_id=TopicId(uuid4()), user_id=user.id)
        await repo.add(follower)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_user_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        topic = await _persist_topic(db_session)
        repo = SqlAlchemyMedicalTopicFollowerRepository(db_session)

        follower = MedicalTopicFollower.create(topic_id=TopicId(topic.id), user_id=uuid4())
        await repo.add(follower)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestMedicalTopicFollowerModelDirectInsert:
    async def test_model_insert_and_query(self, db_session: AsyncSession) -> None:
        topic = await _persist_topic(db_session)
        user = await persist_user(db_session)
        model = MedicalTopicFollowerModel(topic_id=topic.id, user_id=user.id)
        db_session.add(model)
        await db_session.commit()

        reloaded = await db_session.get(MedicalTopicFollowerModel, model.id)
        assert reloaded is not None
        assert reloaded.topic_id == topic.id
        assert reloaded.user_id == user.id
