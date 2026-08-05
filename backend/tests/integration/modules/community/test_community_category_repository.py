"""Integration tests for `SqlAlchemyCommunityCategoryRepository`,
including the unique name/slug constraints, against a real PostgreSQL
instance. `community_categories` is platform-wide (not organization-
scoped) and pre-seeded with 10 example categories by the
`e7a2f9c4d813_create_community_discovery_tables` migration — every test
here uses a uniquely-suffixed name/slug so it doesn't collide with those
seeded rows or with other test runs against the same shared database."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.community.domain.entities import CommunityCategory
from app.modules.community.domain.value_objects import CommunityCategoryName, CommunitySlug
from app.modules.community.infrastructure.models import CommunityCategoryModel
from app.modules.community.infrastructure.repositories import SqlAlchemyCommunityCategoryRepository


def _unique_suffix() -> str:
    return uuid4().hex[:12]


def _make_category(**overrides: object) -> CommunityCategory:
    suffix = _unique_suffix()
    defaults: dict[str, object] = {
        "name": CommunityCategoryName(f"Category {suffix}"),
        "slug": CommunitySlug(f"category-{suffix}"),
    }
    defaults.update(overrides)
    return CommunityCategory.create(**defaults)  # type: ignore[arg-type]


class TestCommunityCategoryRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityCategoryRepository(db_session)
        category = _make_category(description="A test category.")
        await repo.add(category)
        await db_session.commit()

        reloaded = await repo.get_by_id(category.id)
        assert reloaded is not None
        assert str(reloaded.name) == str(category.name)
        assert str(reloaded.slug) == str(category.slug)
        assert reloaded.description == "A test category."
        assert reloaded.is_active is True

    async def test_deactivate_round_trips(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityCategoryRepository(db_session)
        category = _make_category()
        await repo.add(category)
        await db_session.commit()

        category.deactivate()
        await repo.add(category)
        await db_session.commit()

        reloaded = await repo.get_by_id(category.id)
        assert reloaded is not None
        assert reloaded.is_active is False


class TestGetById:
    async def test_returns_none_for_an_unknown_id(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityCategoryRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None


class TestGetBySlug:
    async def test_returns_the_matching_category(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityCategoryRepository(db_session)
        category = _make_category()
        await repo.add(category)
        await db_session.commit()

        found = await repo.get_by_slug(str(category.slug))
        assert found is not None and found.id == category.id

    async def test_returns_none_for_an_unknown_slug(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityCategoryRepository(db_session)
        assert await repo.get_by_slug(f"no-such-slug-{_unique_suffix()}") is None


class TestGetByName:
    async def test_returns_the_matching_category(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityCategoryRepository(db_session)
        category = _make_category()
        await repo.add(category)
        await db_session.commit()

        found = await repo.get_by_name(str(category.name))
        assert found is not None and found.id == category.id

    async def test_returns_none_for_an_unknown_name(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityCategoryRepository(db_session)
        assert await repo.get_by_name(f"No Such Category {_unique_suffix()}") is None


class TestListActive:
    async def test_excludes_inactive_categories(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityCategoryRepository(db_session)
        active = _make_category()
        inactive = _make_category()
        inactive.deactivate()
        await repo.add(active)
        await repo.add(inactive)
        await db_session.commit()

        results = await repo.list_active(limit=1000)

        result_ids = {c.id for c in results}
        assert active.id in result_ids
        assert inactive.id not in result_ids

    async def test_respects_pagination(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityCategoryRepository(db_session)
        for _ in range(3):
            await repo.add(_make_category())
        await db_session.commit()

        page = await repo.list_active(offset=0, limit=1)
        assert len(page) == 1


class TestUniqueNameConstraint:
    async def test_duplicate_name_violates_the_constraint(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityCategoryRepository(db_session)
        name = CommunityCategoryName(f"Category {_unique_suffix()}")

        first = CommunityCategory.create(name=name, slug=CommunitySlug(f"slug-{_unique_suffix()}"))
        await repo.add(first)
        await db_session.commit()

        second = CommunityCategory.create(name=name, slug=CommunitySlug(f"slug-{_unique_suffix()}"))
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestUniqueSlugConstraint:
    async def test_duplicate_slug_violates_the_constraint(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityCategoryRepository(db_session)
        slug = CommunitySlug(f"slug-{_unique_suffix()}")

        first = CommunityCategory.create(
            name=CommunityCategoryName(f"Category {_unique_suffix()}"), slug=slug
        )
        await repo.add(first)
        await db_session.commit()

        second = CommunityCategory.create(
            name=CommunityCategoryName(f"Category {_unique_suffix()}"), slug=slug
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestCommunityCategoryModelDirectInsert:
    async def test_model_insert_and_query(self, db_session: AsyncSession) -> None:
        suffix = _unique_suffix()
        model = CommunityCategoryModel(name=f"Direct Category {suffix}", slug=f"direct-{suffix}")
        db_session.add(model)
        await db_session.commit()

        reloaded = await db_session.get(CommunityCategoryModel, model.id)
        assert reloaded is not None
        assert reloaded.name == f"Direct Category {suffix}"
        assert reloaded.is_active is True
