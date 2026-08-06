"""Integration tests for `SqlAlchemyTopicSpecialtyRepository`, including
the unique name/slug constraints, against a real PostgreSQL instance.
`topic_specialties` is platform-wide and pre-seeded with 10 example
specialties by the `bef8b3fd9a86_create_medical_topics_tables`
migration — every test here uses a uniquely-suffixed name/slug so it
doesn't collide with those seeded rows or with other test runs against
the same shared database."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.medical_topics._helpers import unique_suffix

from app.modules.medical_topics.domain.entities import TopicSpecialty
from app.modules.medical_topics.domain.value_objects import TopicName, TopicSlug
from app.modules.medical_topics.infrastructure.models import TopicSpecialtyModel
from app.modules.medical_topics.infrastructure.repositories import (
    SqlAlchemyTopicSpecialtyRepository,
)


def _make_specialty(**overrides: object) -> TopicSpecialty:
    suffix = unique_suffix()
    defaults: dict[str, object] = {
        "name": TopicName(f"Specialty {suffix}"),
        "slug": TopicSlug(f"specialty-{suffix}"),
    }
    defaults.update(overrides)
    return TopicSpecialty.create(**defaults)  # type: ignore[arg-type]


class TestTopicSpecialtyRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyTopicSpecialtyRepository(db_session)
        specialty = _make_specialty(description="A test specialty.")
        await repo.add(specialty)
        await db_session.commit()

        reloaded = await repo.get_by_id(specialty.id)
        assert reloaded is not None
        assert str(reloaded.name) == str(specialty.name)
        assert str(reloaded.slug) == str(specialty.slug)
        assert str(reloaded.description) == "A test specialty."
        assert reloaded.is_active is True

    async def test_deactivate_round_trips(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyTopicSpecialtyRepository(db_session)
        specialty = _make_specialty()
        await repo.add(specialty)
        await db_session.commit()

        specialty.deactivate()
        await repo.add(specialty)
        await db_session.commit()

        reloaded = await repo.get_by_id(specialty.id)
        assert reloaded is not None
        assert reloaded.is_active is False


class TestGetById:
    async def test_returns_none_for_an_unknown_id(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyTopicSpecialtyRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None


class TestGetBySlug:
    async def test_returns_the_matching_specialty(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyTopicSpecialtyRepository(db_session)
        specialty = _make_specialty()
        await repo.add(specialty)
        await db_session.commit()

        found = await repo.get_by_slug(str(specialty.slug))
        assert found is not None and found.id == specialty.id

    async def test_returns_none_for_an_unknown_slug(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyTopicSpecialtyRepository(db_session)
        assert await repo.get_by_slug(f"no-such-slug-{unique_suffix()}") is None


class TestGetByName:
    async def test_returns_the_matching_specialty(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyTopicSpecialtyRepository(db_session)
        specialty = _make_specialty()
        await repo.add(specialty)
        await db_session.commit()

        found = await repo.get_by_name(str(specialty.name))
        assert found is not None and found.id == specialty.id

    async def test_returns_none_for_an_unknown_name(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyTopicSpecialtyRepository(db_session)
        assert await repo.get_by_name(f"No Such Specialty {unique_suffix()}") is None


class TestListActive:
    async def test_excludes_inactive_specialties(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyTopicSpecialtyRepository(db_session)
        active = _make_specialty()
        inactive = _make_specialty()
        inactive.deactivate()
        await repo.add(active)
        await repo.add(inactive)
        await db_session.commit()

        results = await repo.list_active(limit=1000)

        result_ids = {s.id for s in results}
        assert active.id in result_ids
        assert inactive.id not in result_ids

    async def test_respects_pagination(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyTopicSpecialtyRepository(db_session)
        for _ in range(3):
            await repo.add(_make_specialty())
        await db_session.commit()

        page = await repo.list_active(offset=0, limit=1)
        assert len(page) == 1


class TestUniqueNameConstraint:
    async def test_duplicate_name_violates_the_constraint(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyTopicSpecialtyRepository(db_session)
        name = TopicName(f"Specialty {unique_suffix()}")

        first = TopicSpecialty.create(name=name, slug=TopicSlug(f"slug-{unique_suffix()}"))
        await repo.add(first)
        await db_session.commit()

        second = TopicSpecialty.create(name=name, slug=TopicSlug(f"slug-{unique_suffix()}"))
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestUniqueSlugConstraint:
    async def test_duplicate_slug_violates_the_constraint(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyTopicSpecialtyRepository(db_session)
        slug = TopicSlug(f"slug-{unique_suffix()}")

        first = TopicSpecialty.create(name=TopicName(f"Specialty {unique_suffix()}"), slug=slug)
        await repo.add(first)
        await db_session.commit()

        second = TopicSpecialty.create(name=TopicName(f"Specialty {unique_suffix()}"), slug=slug)
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestTopicSpecialtyModelDirectInsert:
    async def test_model_insert_and_query(self, db_session: AsyncSession) -> None:
        suffix = unique_suffix()
        model = TopicSpecialtyModel(name=f"Direct Specialty {suffix}", slug=f"direct-{suffix}")
        db_session.add(model)
        await db_session.commit()

        reloaded = await db_session.get(TopicSpecialtyModel, model.id)
        assert reloaded is not None
        assert reloaded.name == f"Direct Specialty {suffix}"
        assert reloaded.is_active is True
