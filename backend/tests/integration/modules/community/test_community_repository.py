"""Integration tests for `SqlAlchemyCommunityRepository`, including the
FK to `organizations`, the tenant-scoped partial-unique slug constraint,
and search/filter/sort/pagination behavior, against a real PostgreSQL
instance."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community._helpers import (
    persist_organization,
    persist_organization_and_user,
    persist_user,
)

from app.modules.community.domain.entities import (
    Community,
    CommunityCategory,
    CommunityMember,
    CommunityTag,
)
from app.modules.community.domain.enums import CommunityVisibility
from app.modules.community.domain.value_objects import (
    CommunityCategoryName,
    CommunityDescription,
    CommunityId,
    CommunityName,
    CommunitySlug,
    CommunityTagName,
)
from app.modules.community.infrastructure.models import CommunityModel
from app.modules.community.infrastructure.repositories import (
    SqlAlchemyCommunityCategoryRepository,
    SqlAlchemyCommunityMemberRepository,
    SqlAlchemyCommunityRepository,
    SqlAlchemyCommunityTagRepository,
)


def _unique_slug() -> str:
    return f"group-{uuid4().hex[:12]}"


def _make_community(*, organization_id: object, **overrides: object) -> Community:
    defaults: dict[str, object] = {
        "organization_id": organization_id,
        "slug": CommunitySlug(_unique_slug()),
        "name": CommunityName("Test Community"),
    }
    defaults.update(overrides)
    return Community.create(**defaults)  # type: ignore[arg-type]


class TestCommunityRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, user = await persist_organization_and_user(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)

        community = _make_community(
            organization_id=organization.id,
            name=CommunityName("Diabetes Support"),
            description=CommunityDescription("A support group."),
            visibility=CommunityVisibility.PRIVATE,
            created_by=user.id,
        )
        await repo.add(community)
        await db_session.commit()

        reloaded = await repo.get_by_id(community.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert str(reloaded.name) == "Diabetes Support"
        assert str(reloaded.description) == "A support group."
        assert reloaded.visibility is CommunityVisibility.PRIVATE
        assert reloaded.created_by == user.id

    async def test_update_round_trips(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)

        community = _make_community(organization_id=organization.id)
        await repo.add(community)
        await db_session.commit()

        community.update_profile(name=CommunityName("Renamed"))
        await repo.add(community)
        await db_session.commit()

        reloaded = await repo.get_by_id(community.id)
        assert reloaded is not None
        assert str(reloaded.name) == "Renamed"


class TestGetById:
    async def test_returns_none_for_an_unknown_id(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None

    async def test_returns_none_for_a_soft_deleted_community(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)
        community = _make_community(organization_id=organization.id)
        await repo.add(community)
        await db_session.commit()

        await repo.remove(community.id)
        await db_session.commit()

        assert await repo.get_by_id(community.id) is None


class TestGetBySlug:
    async def test_returns_the_matching_community(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)
        slug = _unique_slug()
        community = _make_community(organization_id=organization.id, slug=CommunitySlug(slug))
        await repo.add(community)
        await db_session.commit()

        found = await repo.get_by_slug(organization.id, slug)
        assert found is not None and found.id == community.id

    async def test_is_case_insensitive(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)
        slug = _unique_slug()
        community = _make_community(organization_id=organization.id, slug=CommunitySlug(slug))
        await repo.add(community)
        await db_session.commit()

        found = await repo.get_by_slug(organization.id, slug.upper())
        assert found is not None and found.id == community.id

    async def test_returns_none_for_a_different_organization(
        self, db_session: AsyncSession
    ) -> None:
        organization_a = await persist_organization(db_session)
        organization_b = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)
        slug = _unique_slug()
        community = _make_community(organization_id=organization_a.id, slug=CommunitySlug(slug))
        await repo.add(community)
        await db_session.commit()

        assert await repo.get_by_slug(organization_b.id, slug) is None

    async def test_returns_none_for_an_unknown_slug(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)
        assert await repo.get_by_slug(organization.id, "no-such-slug") is None


class TestListByOrganization:
    async def test_scopes_to_the_organization(self, db_session: AsyncSession) -> None:
        organization_a = await persist_organization(db_session)
        organization_b = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)

        community_a = _make_community(organization_id=organization_a.id)
        community_b = _make_community(organization_id=organization_b.id)
        await repo.add(community_a)
        await repo.add(community_b)
        await db_session.commit()

        results = await repo.list_by_organization(organization_a.id)
        assert [c.id for c in results] == [community_a.id]

    async def test_respects_pagination(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)
        for _ in range(3):
            await repo.add(_make_community(organization_id=organization.id))
        await db_session.commit()

        page = await repo.list_by_organization(organization.id, offset=1, limit=1)
        assert len(page) == 1


class TestSearch:
    async def test_query_filters_by_name(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)
        target = _make_community(
            organization_id=organization.id, name=CommunityName("Oncology Care")
        )
        other = _make_community(
            organization_id=organization.id, name=CommunityName("Cardiology Care")
        )
        await repo.add(target)
        await repo.add(other)
        await db_session.commit()

        results, total = await repo.search(organization_id=organization.id, query="Oncology")

        assert total == 1
        assert [c.id for c in results] == [target.id]

    async def test_visibility_filter(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)
        private = _make_community(
            organization_id=organization.id, visibility=CommunityVisibility.PRIVATE
        )
        public = _make_community(
            organization_id=organization.id, visibility=CommunityVisibility.PUBLIC
        )
        await repo.add(private)
        await repo.add(public)
        await db_session.commit()

        results, total = await repo.search(
            organization_id=organization.id, visibilities=[CommunityVisibility.PRIVATE]
        )

        assert total == 1
        assert [c.id for c in results] == [private.id]

    async def test_excludes_soft_deleted_by_default(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)
        community = _make_community(organization_id=organization.id)
        await repo.add(community)
        await db_session.commit()
        await repo.remove(community.id)
        await db_session.commit()

        results, total = await repo.search(organization_id=organization.id)

        assert total == 0
        assert results == []

    async def test_include_deleted_returns_soft_deleted_rows(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)
        community = _make_community(organization_id=organization.id)
        await repo.add(community)
        await db_session.commit()
        await repo.remove(community.id)
        await db_session.commit()

        results, total = await repo.search(organization_id=organization.id, include_deleted=True)

        assert total == 1
        assert [c.id for c in results] == [community.id]

    async def test_date_range_filter(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)
        community = _make_community(organization_id=organization.id)
        await repo.add(community)
        await db_session.commit()

        far_future = datetime.now(UTC) + timedelta(days=365)
        results, total = await repo.search(organization_id=organization.id, created_from=far_future)

        assert total == 0
        assert results == []

    async def test_sort_order_descending(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)
        first = _make_community(organization_id=organization.id, name=CommunityName("Alpha"))
        await repo.add(first)
        await db_session.commit()
        second = _make_community(organization_id=organization.id, name=CommunityName("Beta"))
        await repo.add(second)
        await db_session.commit()

        results, _ = await repo.search(
            organization_id=organization.id, sort_by="name", sort_order="desc"
        )

        assert [str(c.name) for c in results] == ["Beta", "Alpha"]

    async def test_pagination_within_search(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)
        for _ in range(3):
            await repo.add(_make_community(organization_id=organization.id))
            await db_session.commit()

        results, total = await repo.search(organization_id=organization.id, offset=1, limit=1)

        assert total == 3
        assert len(results) == 1


class TestSearchDiscoveryFilters:
    async def test_category_id_filter(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)
        category_repo = SqlAlchemyCommunityCategoryRepository(db_session)
        suffix = uuid4().hex[:12]
        category = CommunityCategory.create(
            name=CommunityCategoryName(f"Category {suffix}"),
            slug=CommunitySlug(f"category-{suffix}"),
        )
        await category_repo.add(category)
        await db_session.commit()

        matching = _make_community(organization_id=organization.id)
        matching.update_profile(category_id=category.id)
        other = _make_community(organization_id=organization.id)
        await repo.add(matching)
        await repo.add(other)
        await db_session.commit()

        results, total = await repo.search(organization_id=organization.id, category_id=category.id)

        assert total == 1
        assert [c.id for c in results] == [matching.id]

    async def test_tag_ids_filter(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community_repo = SqlAlchemyCommunityRepository(db_session)
        tag_repo = SqlAlchemyCommunityTagRepository(db_session)
        matching = _make_community(organization_id=organization.id)
        other = _make_community(organization_id=organization.id)
        await community_repo.add(matching)
        await community_repo.add(other)
        await db_session.commit()

        tag = CommunityTag.create(name=CommunityTagName(f"tag-{uuid4().hex[:8]}"))
        await tag_repo.add(tag)
        await db_session.commit()
        await tag_repo.assign(matching.id, tag.id)
        await db_session.commit()

        results, total = await community_repo.search(
            organization_id=organization.id, tag_ids=[tag.id]
        )

        assert total == 1
        assert [c.id for c in results] == [matching.id]

    async def test_featured_only_filter(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)
        featured = _make_community(organization_id=organization.id)
        featured.set_featured(True)
        unfeatured = _make_community(organization_id=organization.id)
        await repo.add(featured)
        await repo.add(unfeatured)
        await db_session.commit()

        results, total = await repo.search(organization_id=organization.id, featured_only=True)

        assert total == 1
        assert [c.id for c in results] == [featured.id]

    async def test_verified_only_filter(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)
        verified = _make_community(organization_id=organization.id)
        verified.set_verified(True)
        unverified = _make_community(organization_id=organization.id)
        await repo.add(verified)
        await repo.add(unverified)
        await db_session.commit()

        results, total = await repo.search(organization_id=organization.id, verified_only=True)

        assert total == 1
        assert [c.id for c in results] == [verified.id]

    async def test_sort_by_member_count(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community_repo = SqlAlchemyCommunityRepository(db_session)
        member_repo = SqlAlchemyCommunityMemberRepository(db_session)
        low = _make_community(organization_id=organization.id)
        high = _make_community(organization_id=organization.id)
        await community_repo.add(low)
        await community_repo.add(high)
        await db_session.commit()

        low_user = await persist_user(db_session, organization_id=organization.id)
        await member_repo.add(
            CommunityMember.create(community_id=CommunityId(low.id), user_id=low_user.id)
        )
        for _ in range(3):
            user = await persist_user(db_session, organization_id=organization.id)
            await member_repo.add(
                CommunityMember.create(community_id=CommunityId(high.id), user_id=user.id)
            )
        await db_session.commit()

        results, _ = await community_repo.search(
            organization_id=organization.id, sort_by="member_count", sort_order="desc"
        )

        assert [c.id for c in results[:2]] == [high.id, low.id]


class TestRemove:
    async def test_sets_deleted_at(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)
        community = _make_community(organization_id=organization.id)
        await repo.add(community)
        await db_session.commit()

        await repo.remove(community.id)
        await db_session.commit()

        model = await db_session.get(CommunityModel, community.id)
        assert model is not None
        assert model.deleted_at is not None

    async def test_is_a_no_op_for_an_unknown_id(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityRepository(db_session)
        await repo.remove(uuid4())  # must not raise
        await db_session.commit()

    async def test_frees_the_slug_for_reuse_within_the_same_organization(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)
        slug = _unique_slug()
        first = _make_community(organization_id=organization.id, slug=CommunitySlug(slug))
        await repo.add(first)
        await db_session.commit()
        await repo.remove(first.id)
        await db_session.commit()

        second = _make_community(organization_id=organization.id, slug=CommunitySlug(slug))
        await repo.add(second)
        await db_session.commit()  # must not raise

        reloaded = await repo.get_by_slug(organization.id, slug)
        assert reloaded is not None and reloaded.id == second.id


class TestUniqueSlugConstraint:
    async def test_duplicate_slug_within_the_same_organization_violates_the_index(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyCommunityRepository(db_session)
        slug = _unique_slug()

        first = _make_community(organization_id=organization.id, slug=CommunitySlug(slug))
        await repo.add(first)
        await db_session.commit()

        second = _make_community(organization_id=organization.id, slug=CommunitySlug(slug))
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestCommunityRequiresValidReferences:
    async def test_nonexistent_organization_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCommunityRepository(db_session)
        community = _make_community(organization_id=uuid4())
        await repo.add(community)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestCommunityModelDirectInsert:
    """Confirms the ORM model itself (not just the domain-entity-driven
    repository path) round-trips every column correctly — the same
    "insert the model directly" smoke check
    `tests.integration.modules.family_access.test_family_access_repository
    .TestFamilyAccessModelDirectInsert` uses for its own module."""

    async def test_model_insert_and_query(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        model = CommunityModel(
            organization_id=organization.id,
            slug=_unique_slug(),
            name="Direct Insert Community",
            visibility=CommunityVisibility.PUBLIC,
        )
        db_session.add(model)
        await db_session.commit()

        reloaded = await db_session.get(CommunityModel, model.id)
        assert reloaded is not None
        assert reloaded.name == "Direct Insert Community"
        assert reloaded.visibility is CommunityVisibility.PUBLIC
