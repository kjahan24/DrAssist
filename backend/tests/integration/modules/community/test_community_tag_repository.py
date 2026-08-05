"""Integration tests for `SqlAlchemyCommunityTagRepository`, including
the unique tag name constraint, the `community_tag_assignments` join
table (assign/unassign/is_assigned/list_for_community), and its FKs to
`communities`/`community_tags`, against a real PostgreSQL instance."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community._helpers import persist_organization

from app.modules.community.domain.entities import Community, CommunityTag
from app.modules.community.domain.value_objects import (
    CommunityName,
    CommunitySlug,
    CommunityTagName,
)
from app.modules.community.infrastructure.models import (
    CommunityTagAssignmentModel,
    CommunityTagModel,
)
from app.modules.community.infrastructure.repositories import (
    SqlAlchemyCommunityRepository,
    SqlAlchemyCommunityTagRepository,
)


def _unique_suffix() -> str:
    return uuid4().hex[:12]


def _make_tag(**overrides: object) -> CommunityTag:
    defaults: dict[str, object] = {"name": CommunityTagName(f"tag-{_unique_suffix()}")}
    defaults.update(overrides)
    return CommunityTag.create(**defaults)  # type: ignore[arg-type]


async def _persist_community(db_session: AsyncSession, *, organization_id: object) -> Community:
    repo = SqlAlchemyCommunityRepository(db_session)
    community = Community.create(
        organization_id=organization_id,  # type: ignore[arg-type]
        slug=CommunitySlug(f"group-{_unique_suffix()}"),
        name=CommunityName("Test Community"),
    )
    await repo.add(community)
    await db_session.commit()
    return community


class TestCommunityTagRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityTagRepository(db_session)
        tag = _make_tag()
        await repo.add(tag)
        await db_session.commit()

        reloaded = await repo.get_by_id(tag.id)
        assert reloaded is not None
        assert str(reloaded.name) == str(tag.name)


class TestGetById:
    async def test_returns_none_for_an_unknown_id(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityTagRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None


class TestGetByName:
    async def test_returns_the_matching_tag(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityTagRepository(db_session)
        tag = _make_tag()
        await repo.add(tag)
        await db_session.commit()

        found = await repo.get_by_name(str(tag.name))
        assert found is not None and found.id == tag.id

    async def test_returns_none_for_an_unknown_name(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityTagRepository(db_session)
        assert await repo.get_by_name(f"no-such-tag-{_unique_suffix()}") is None


class TestSearch:
    async def test_matches_by_partial_name(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityTagRepository(db_session)
        suffix = _unique_suffix()
        target = _make_tag(name=CommunityTagName(f"diabetes-{suffix}"))
        other = _make_tag(name=CommunityTagName(f"oncology-{suffix}"))
        await repo.add(target)
        await repo.add(other)
        await db_session.commit()

        results, total = await repo.search(f"diabetes-{suffix}")

        assert total == 1
        assert [t.id for t in results] == [target.id]

    async def test_no_matches_returns_empty(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityTagRepository(db_session)
        results, total = await repo.search(f"no-such-tag-{_unique_suffix()}")
        assert total == 0
        assert results == []


class TestUniqueNameConstraint:
    async def test_duplicate_name_violates_the_constraint(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityTagRepository(db_session)
        name = CommunityTagName(f"tag-{_unique_suffix()}")

        first = CommunityTag.create(name=name)
        await repo.add(first)
        await db_session.commit()

        second = CommunityTag.create(name=name)
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestAssignAndUnassign:
    async def test_assign_then_is_assigned_returns_true(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityTagRepository(db_session)
        tag = _make_tag()
        await repo.add(tag)
        await db_session.commit()

        await repo.assign(community.id, tag.id)
        await db_session.commit()

        assert await repo.is_assigned(community.id, tag.id) is True

    async def test_assign_is_idempotent(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityTagRepository(db_session)
        tag = _make_tag()
        await repo.add(tag)
        await db_session.commit()

        await repo.assign(community.id, tag.id)
        await db_session.commit()
        await repo.assign(community.id, tag.id)
        await db_session.commit()  # must not raise a duplicate-row error

        assert await repo.is_assigned(community.id, tag.id) is True

    async def test_unassign_removes_the_assignment(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityTagRepository(db_session)
        tag = _make_tag()
        await repo.add(tag)
        await db_session.commit()
        await repo.assign(community.id, tag.id)
        await db_session.commit()

        await repo.unassign(community.id, tag.id)
        await db_session.commit()

        assert await repo.is_assigned(community.id, tag.id) is False

    async def test_unassign_is_a_no_op_when_not_assigned(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityTagRepository(db_session)
        tag = _make_tag()
        await repo.add(tag)
        await db_session.commit()

        await repo.unassign(community.id, tag.id)  # must not raise
        await db_session.commit()

    async def test_is_assigned_false_when_never_assigned(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityTagRepository(db_session)
        tag = _make_tag()
        await repo.add(tag)
        await db_session.commit()

        assert await repo.is_assigned(community.id, tag.id) is False


class TestListForCommunity:
    async def test_returns_only_tags_assigned_to_the_community(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        community_a = await _persist_community(db_session, organization_id=organization.id)
        community_b = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityTagRepository(db_session)
        tag_a = _make_tag()
        tag_b = _make_tag()
        await repo.add(tag_a)
        await repo.add(tag_b)
        await db_session.commit()
        await repo.assign(community_a.id, tag_a.id)
        await repo.assign(community_b.id, tag_b.id)
        await db_session.commit()

        results = await repo.list_for_community(community_a.id)

        assert [t.id for t in results] == [tag_a.id]

    async def test_no_assignments_returns_empty(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityTagRepository(db_session)

        assert await repo.list_for_community(community.id) == []


class TestTagAssignmentRequiresValidReferences:
    async def test_nonexistent_community_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCommunityTagRepository(db_session)
        tag = _make_tag()
        await repo.add(tag)
        await db_session.commit()

        db_session.add(CommunityTagAssignmentModel(community_id=uuid4(), tag_id=tag.id))
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_tag_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)

        db_session.add(CommunityTagAssignmentModel(community_id=community.id, tag_id=uuid4()))
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestCommunityTagModelDirectInsert:
    async def test_model_insert_and_query(self, db_session: AsyncSession) -> None:
        name = f"direct-tag-{_unique_suffix()}"
        model = CommunityTagModel(name=name)
        db_session.add(model)
        await db_session.commit()

        reloaded = await db_session.get(CommunityTagModel, model.id)
        assert reloaded is not None
        assert reloaded.name == name
