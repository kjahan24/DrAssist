"""Integration tests for `SqlAlchemyMedicalTopicRepository`, including
the platform-wide unique slug constraint, self-referencing `parent_id`
FK, and search/filter/sort/pagination behavior, against a real
PostgreSQL instance."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.medical_topics._helpers import persist_user, unique_suffix

from app.modules.medical_topics.domain.entities import MedicalTopic, TopicSpecialty
from app.modules.medical_topics.domain.enums import TopicStatus, TopicVisibility
from app.modules.medical_topics.domain.value_objects import (
    TopicDescription,
    TopicName,
    TopicSlug,
)
from app.modules.medical_topics.infrastructure.models import MedicalTopicModel
from app.modules.medical_topics.infrastructure.repositories import (
    SqlAlchemyMedicalTopicRepository,
    SqlAlchemyTopicSpecialtyRepository,
)


def _unique_slug() -> str:
    return f"topic-{unique_suffix()}"


def _make_topic(**overrides: object) -> MedicalTopic:
    """`name` defaults to a uniquely-suffixed value (not a shared literal
    like `"Test Topic"`) — tests run repeatedly against the same shared,
    non-torn-down database (see this file's own module docstring), so a
    fixed default name would accumulate rows across runs and break any
    assertion that expects a `query=` search to match *only* the row a
    given test itself created."""

    defaults: dict[str, object] = {
        "slug": TopicSlug(_unique_slug()),
        "name": TopicName(f"Test Topic {unique_suffix()}"),
    }
    defaults.update(overrides)
    return MedicalTopic.create(**defaults)  # type: ignore[arg-type]


class TestMedicalTopicRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        user = await persist_user(db_session)
        repo = SqlAlchemyMedicalTopicRepository(db_session)

        topic = _make_topic(
            name=TopicName("Cardiac Arrhythmia"),
            description=TopicDescription("Covers irregular heart rhythms."),
            visibility=TopicVisibility.UNLISTED,
            created_by=user.id,
        )
        await repo.add(topic)
        await db_session.commit()

        reloaded = await repo.get_by_id(topic.id)
        assert reloaded is not None
        assert str(reloaded.name) == "Cardiac Arrhythmia"
        assert str(reloaded.description) == "Covers irregular heart rhythms."
        assert reloaded.visibility is TopicVisibility.UNLISTED
        assert reloaded.created_by == user.id

    async def test_update_round_trips(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        topic = _make_topic()
        await repo.add(topic)
        await db_session.commit()

        topic.update_profile(name=TopicName("Renamed"))
        await repo.add(topic)
        await db_session.commit()

        reloaded = await repo.get_by_id(topic.id)
        assert reloaded is not None
        assert str(reloaded.name) == "Renamed"

    async def test_self_referencing_parent_round_trips(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        parent = _make_topic(name=TopicName("Cardiology"))
        await repo.add(parent)
        await db_session.commit()

        child = _make_topic(name=TopicName("Arrhythmia"), parent_id=parent.id)
        await repo.add(child)
        await db_session.commit()

        reloaded = await repo.get_by_id(child.id)
        assert reloaded is not None
        assert reloaded.parent_id == parent.id


class TestGetById:
    async def test_returns_none_for_an_unknown_id(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None

    async def test_returns_none_for_a_soft_deleted_topic(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        topic = _make_topic()
        await repo.add(topic)
        await db_session.commit()

        await repo.remove(topic.id)
        await db_session.commit()

        assert await repo.get_by_id(topic.id) is None


class TestGetBySlug:
    async def test_returns_the_matching_topic(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        slug = _unique_slug()
        topic = _make_topic(slug=TopicSlug(slug))
        await repo.add(topic)
        await db_session.commit()

        found = await repo.get_by_slug(slug)
        assert found is not None and found.id == topic.id

    async def test_is_case_insensitive(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        slug = _unique_slug()
        topic = _make_topic(slug=TopicSlug(slug))
        await repo.add(topic)
        await db_session.commit()

        found = await repo.get_by_slug(slug.upper())
        assert found is not None and found.id == topic.id

    async def test_returns_none_for_an_unknown_slug(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        assert await repo.get_by_slug("no-such-slug") is None


class TestListChildren:
    async def test_returns_only_direct_children(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        parent = _make_topic(name=TopicName("Cardiology"))
        await repo.add(parent)
        await db_session.commit()
        child = _make_topic(name=TopicName("Arrhythmia"), parent_id=parent.id)
        await repo.add(child)
        unrelated = _make_topic(name=TopicName("Oncology"))
        await repo.add(unrelated)
        await db_session.commit()

        results = await repo.list_children(parent.id)

        assert [t.id for t in results] == [child.id]

    async def test_respects_pagination(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        parent = _make_topic()
        await repo.add(parent)
        await db_session.commit()
        for i in range(3):
            await repo.add(_make_topic(name=TopicName(f"Child {i}"), parent_id=parent.id))
        await db_session.commit()

        page = await repo.list_children(parent.id, offset=1, limit=1)
        assert len(page) == 1


class TestSearch:
    async def test_query_filters_by_name(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        target = _make_topic(name=TopicName(f"Oncology Care {unique_suffix()}"))
        other = _make_topic(name=TopicName(f"Cardiology Care {unique_suffix()}"))
        await repo.add(target)
        await repo.add(other)
        await db_session.commit()

        results, total = await repo.search(query=str(target.name))

        assert total == 1
        assert [t.id for t in results] == [target.id]

    async def test_status_filter(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        published = _make_topic()
        published.update_profile(status=TopicStatus.PUBLISHED)
        draft = _make_topic()
        await repo.add(published)
        await repo.add(draft)
        await db_session.commit()

        results, total = await repo.search(status=[TopicStatus.PUBLISHED])

        result_ids = {t.id for t in results}
        assert published.id in result_ids
        assert draft.id not in result_ids
        assert total >= 1

    async def test_visibility_filter(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        private = _make_topic(visibility=TopicVisibility.PRIVATE)
        public = _make_topic(visibility=TopicVisibility.PUBLIC)
        await repo.add(private)
        await repo.add(public)
        await db_session.commit()

        results, _ = await repo.search(visibility=[TopicVisibility.PRIVATE])

        result_ids = {t.id for t in results}
        assert private.id in result_ids
        assert public.id not in result_ids

    async def test_specialty_id_filter(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        specialty_repo = SqlAlchemyTopicSpecialtyRepository(db_session)
        suffix = unique_suffix()
        specialty = TopicSpecialty.create(
            name=TopicName(f"Specialty {suffix}"), slug=TopicSlug(f"specialty-{suffix}")
        )
        await specialty_repo.add(specialty)
        await db_session.commit()

        matching = _make_topic(specialty_id=specialty.id)
        other = _make_topic()
        await repo.add(matching)
        await repo.add(other)
        await db_session.commit()

        results, total = await repo.search(specialty_id=specialty.id)

        assert total == 1
        assert [t.id for t in results] == [matching.id]

    async def test_featured_only_filter(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        featured = _make_topic()
        featured.set_featured(True)
        unfeatured = _make_topic()
        await repo.add(featured)
        await repo.add(unfeatured)
        await db_session.commit()

        results, _ = await repo.search(featured_only=True)

        result_ids = {t.id for t in results}
        assert featured.id in result_ids
        assert unfeatured.id not in result_ids

    async def test_excludes_soft_deleted_by_default(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        topic = _make_topic()
        await repo.add(topic)
        await db_session.commit()
        await repo.remove(topic.id)
        await db_session.commit()

        results, _ = await repo.search(query=str(topic.name))

        assert topic.id not in {t.id for t in results}

    async def test_include_deleted_returns_soft_deleted_rows(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        topic = _make_topic()
        await repo.add(topic)
        await db_session.commit()
        await repo.remove(topic.id)
        await db_session.commit()

        results, _ = await repo.search(query=str(topic.name), include_deleted=True)

        assert topic.id in {t.id for t in results}

    async def test_sort_by_trending_score_descending(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        low = _make_topic()
        low.update_trending_score(2.0)
        high = _make_topic()
        high.update_trending_score(50.0)
        await repo.add(low)
        await repo.add(high)
        await db_session.commit()

        results, _ = await repo.search(sort_by="trending_score", sort_order="desc", limit=200)

        result_ids = [t.id for t in results]
        assert result_ids.index(high.id) < result_ids.index(low.id)

    async def test_pagination_within_search(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        suffix = unique_suffix()
        for i in range(3):
            await repo.add(_make_topic(name=TopicName(f"Paginated {suffix} {i}")))
            await db_session.commit()

        results, total = await repo.search(query=f"Paginated {suffix}", offset=1, limit=1)

        assert total == 3
        assert len(results) == 1


class TestListByIds:
    async def test_returns_matching_topics(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        a = _make_topic()
        b = _make_topic()
        await repo.add(a)
        await repo.add(b)
        await db_session.commit()

        results = await repo.list_by_ids([a.id, b.id, uuid4()])

        result_ids = {t.id for t in results}
        assert result_ids == {a.id, b.id}

    async def test_empty_input_returns_empty(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        assert await repo.list_by_ids([]) == []


class TestRemove:
    async def test_sets_deleted_at(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        topic = _make_topic()
        await repo.add(topic)
        await db_session.commit()

        await repo.remove(topic.id)
        await db_session.commit()

        model = await db_session.get(MedicalTopicModel, topic.id)
        assert model is not None
        assert model.deleted_at is not None

    async def test_is_a_no_op_for_an_unknown_id(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        await repo.remove(uuid4())  # must not raise
        await db_session.commit()

    async def test_frees_the_slug_for_reuse(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        slug = _unique_slug()
        first = _make_topic(slug=TopicSlug(slug))
        await repo.add(first)
        await db_session.commit()
        await repo.remove(first.id)
        await db_session.commit()

        second = _make_topic(slug=TopicSlug(slug))
        await repo.add(second)
        await db_session.commit()  # must not raise

        reloaded = await repo.get_by_slug(slug)
        assert reloaded is not None and reloaded.id == second.id


class TestUniqueSlugConstraint:
    async def test_duplicate_slug_violates_the_index(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        slug = _unique_slug()

        first = _make_topic(slug=TopicSlug(slug))
        await repo.add(first)
        await db_session.commit()

        second = _make_topic(slug=TopicSlug(slug))
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestMedicalTopicRequiresValidReferences:
    async def test_nonexistent_parent_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        topic = _make_topic(parent_id=uuid4())
        await repo.add(topic)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_specialty_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyMedicalTopicRepository(db_session)
        topic = _make_topic(specialty_id=uuid4())
        await repo.add(topic)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestMedicalTopicModelDirectInsert:
    """Confirms the ORM model itself (not just the domain-entity-driven
    repository path) round-trips every column correctly — the same
    "insert the model directly" smoke check
    `tests.integration.modules.community.test_community_repository
    .TestCommunityModelDirectInsert` uses for its own module."""

    async def test_model_insert_and_query(self, db_session: AsyncSession) -> None:
        model = MedicalTopicModel(
            slug=_unique_slug(),
            name="Direct Insert Topic",
            status=TopicStatus.DRAFT,
            visibility=TopicVisibility.PUBLIC,
        )
        db_session.add(model)
        await db_session.commit()

        reloaded = await db_session.get(MedicalTopicModel, model.id)
        assert reloaded is not None
        assert reloaded.name == "Direct Insert Topic"
        assert reloaded.trending_score == 0.0
        assert reloaded.popularity_score == 0.0
