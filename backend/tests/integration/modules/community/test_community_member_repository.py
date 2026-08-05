"""Integration tests for `SqlAlchemyCommunityMemberRepository`,
including the FKs to `communities`/`users` and the
`(community_id, user_id)` uniqueness constraint, against a real
PostgreSQL instance."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community._helpers import persist_organization, persist_user

from app.modules.community.domain.entities import Community, CommunityMember
from app.modules.community.domain.enums import CommunityMemberStatus, CommunityRole
from app.modules.community.domain.value_objects import CommunityId, CommunityName, CommunitySlug
from app.modules.community.infrastructure.models import CommunityMemberModel
from app.modules.community.infrastructure.repositories import (
    SqlAlchemyCommunityMemberRepository,
    SqlAlchemyCommunityRepository,
)


def _unique_slug() -> str:
    return f"group-{uuid4().hex[:12]}"


async def _persist_community(db_session: AsyncSession, *, organization_id: object) -> Community:
    repo = SqlAlchemyCommunityRepository(db_session)
    community = Community.create(
        organization_id=organization_id,  # type: ignore[arg-type]
        slug=CommunitySlug(_unique_slug()),
        name=CommunityName("Test Community"),
    )
    await repo.add(community)
    await db_session.commit()
    return community


async def _seed(db_session: AsyncSession) -> tuple[Community, UUID]:
    organization = await persist_organization(db_session)
    community = await _persist_community(db_session, organization_id=organization.id)
    user = await persist_user(db_session, organization_id=organization.id)
    return community, user.id


class TestCommunityMemberRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        community, user_id = await _seed(db_session)
        repo = SqlAlchemyCommunityMemberRepository(db_session)

        member = CommunityMember.create(
            community_id=CommunityId(community.id), user_id=user_id, role=CommunityRole.MODERATOR
        )
        await repo.add(member)
        await db_session.commit()

        reloaded = await repo.get_by_id(member.id)
        assert reloaded is not None
        assert reloaded.community_id.value == community.id
        assert reloaded.user_id == user_id
        assert reloaded.role is CommunityRole.MODERATOR
        assert reloaded.status is CommunityMemberStatus.ACTIVE

    async def test_status_transition_round_trips(self, db_session: AsyncSession) -> None:
        community, user_id = await _seed(db_session)
        repo = SqlAlchemyCommunityMemberRepository(db_session)

        member = CommunityMember.create(community_id=CommunityId(community.id), user_id=user_id)
        await repo.add(member)
        await db_session.commit()

        member.leave()
        await repo.add(member)
        await db_session.commit()

        reloaded = await repo.get_by_id(member.id)
        assert reloaded is not None
        assert reloaded.status is CommunityMemberStatus.LEFT

    async def test_rejoin_reuses_the_same_row(self, db_session: AsyncSession) -> None:
        community, user_id = await _seed(db_session)
        repo = SqlAlchemyCommunityMemberRepository(db_session)

        member = CommunityMember.create(community_id=CommunityId(community.id), user_id=user_id)
        await repo.add(member)
        await db_session.commit()
        member.leave()
        await repo.add(member)
        await db_session.commit()

        member.rejoin()
        await repo.add(member)
        await db_session.commit()  # must not raise a duplicate-row error

        reloaded = await repo.get_by_id(member.id)
        assert reloaded is not None
        assert reloaded.status is CommunityMemberStatus.ACTIVE


class TestGetById:
    async def test_returns_none_for_an_unknown_id(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityMemberRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None


class TestGetByCommunityAndUser:
    async def test_returns_the_matching_member(self, db_session: AsyncSession) -> None:
        community, user_id = await _seed(db_session)
        repo = SqlAlchemyCommunityMemberRepository(db_session)
        member = CommunityMember.create(community_id=CommunityId(community.id), user_id=user_id)
        await repo.add(member)
        await db_session.commit()

        found = await repo.get_by_community_and_user(community.id, user_id)
        assert found is not None and found.id == member.id

    async def test_returns_none_when_absent(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityMemberRepository(db_session)
        assert await repo.get_by_community_and_user(uuid4(), uuid4()) is None


class TestListByCommunity:
    async def test_scopes_to_the_community(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community_a = await _persist_community(db_session, organization_id=organization.id)
        community_b = await _persist_community(db_session, organization_id=organization.id)
        user_a = await persist_user(db_session, organization_id=organization.id)
        user_b = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityMemberRepository(db_session)

        member_a = CommunityMember.create(
            community_id=CommunityId(community_a.id), user_id=user_a.id
        )
        member_b = CommunityMember.create(
            community_id=CommunityId(community_b.id), user_id=user_b.id
        )
        await repo.add(member_a)
        await repo.add(member_b)
        await db_session.commit()

        results = await repo.list_by_community(community_a.id)
        assert [m.id for m in results] == [member_a.id]

    async def test_respects_pagination(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityMemberRepository(db_session)
        for _ in range(3):
            user = await persist_user(db_session, organization_id=organization.id)
            await repo.add(
                CommunityMember.create(community_id=CommunityId(community.id), user_id=user.id)
            )
            await db_session.commit()

        page = await repo.list_by_community(community.id, offset=1, limit=1)
        assert len(page) == 1


class TestListByUser:
    async def test_scopes_to_the_user(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community_a = await _persist_community(db_session, organization_id=organization.id)
        community_b = await _persist_community(db_session, organization_id=organization.id)
        user = await persist_user(db_session, organization_id=organization.id)
        other_user = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityMemberRepository(db_session)

        membership_a = CommunityMember.create(
            community_id=CommunityId(community_a.id), user_id=user.id
        )
        membership_b = CommunityMember.create(
            community_id=CommunityId(community_b.id), user_id=other_user.id
        )
        await repo.add(membership_a)
        await repo.add(membership_b)
        await db_session.commit()

        results = await repo.list_by_user(user.id)
        assert [m.id for m in results] == [membership_a.id]


class TestCountActiveByRole:
    async def test_counts_only_active_members_with_the_given_role(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityMemberRepository(db_session)

        active_owner = await persist_user(db_session, organization_id=organization.id)
        left_owner = await persist_user(db_session, organization_id=organization.id)
        active_member = await persist_user(db_session, organization_id=organization.id)

        owner_member = CommunityMember.create(
            community_id=CommunityId(community.id),
            user_id=active_owner.id,
            role=CommunityRole.OWNER,
        )
        left_owner_member = CommunityMember.create(
            community_id=CommunityId(community.id), user_id=left_owner.id, role=CommunityRole.OWNER
        )
        left_owner_member.leave()
        plain_member = CommunityMember.create(
            community_id=CommunityId(community.id),
            user_id=active_member.id,
            role=CommunityRole.MEMBER,
        )
        await repo.add(owner_member)
        await repo.add(left_owner_member)
        await repo.add(plain_member)
        await db_session.commit()

        count = await repo.count_active_by_role(community.id, CommunityRole.OWNER)
        assert count == 1

    async def test_returns_zero_when_no_members_have_the_role(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityMemberRepository(db_session)

        assert await repo.count_active_by_role(community.id, CommunityRole.OWNER) == 0


class TestCountActive:
    async def test_counts_only_active_members(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityMemberRepository(db_session)

        active_user = await persist_user(db_session, organization_id=organization.id)
        left_user = await persist_user(db_session, organization_id=organization.id)
        await repo.add(
            CommunityMember.create(community_id=CommunityId(community.id), user_id=active_user.id)
        )
        left_member = CommunityMember.create(
            community_id=CommunityId(community.id), user_id=left_user.id
        )
        left_member.leave()
        await repo.add(left_member)
        await db_session.commit()

        assert await repo.count_active(community.id) == 1

    async def test_returns_zero_for_a_community_with_no_members(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityMemberRepository(db_session)

        assert await repo.count_active(community.id) == 0


class TestListByRoles:
    async def test_returns_only_members_with_the_given_roles(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityMemberRepository(db_session)

        moderator_user = await persist_user(db_session, organization_id=organization.id)
        plain_user = await persist_user(db_session, organization_id=organization.id)
        moderator = CommunityMember.create(
            community_id=CommunityId(community.id),
            user_id=moderator_user.id,
            role=CommunityRole.MODERATOR,
        )
        plain_member = CommunityMember.create(
            community_id=CommunityId(community.id), user_id=plain_user.id, role=CommunityRole.MEMBER
        )
        await repo.add(moderator)
        await repo.add(plain_member)
        await db_session.commit()

        results = await repo.list_by_roles(community.id, (CommunityRole.MODERATOR,))

        assert [m.id for m in results] == [moderator.id]

    async def test_excludes_non_active_members(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityMemberRepository(db_session)

        user = await persist_user(db_session, organization_id=organization.id)
        member = CommunityMember.create(
            community_id=CommunityId(community.id), user_id=user.id, role=CommunityRole.MODERATOR
        )
        member.leave()
        await repo.add(member)
        await db_session.commit()

        results = await repo.list_by_roles(community.id, (CommunityRole.MODERATOR,))

        assert results == []

    async def test_respects_pagination(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityMemberRepository(db_session)

        for _ in range(3):
            user = await persist_user(db_session, organization_id=organization.id)
            await repo.add(
                CommunityMember.create(
                    community_id=CommunityId(community.id),
                    user_id=user.id,
                    role=CommunityRole.MODERATOR,
                )
            )
        await db_session.commit()

        page = await repo.list_by_roles(community.id, (CommunityRole.MODERATOR,), offset=1, limit=1)
        assert len(page) == 1


class TestUniqueCommunityUserConstraint:
    async def test_duplicate_membership_row_violates_the_constraint(
        self, db_session: AsyncSession
    ) -> None:
        community, user_id = await _seed(db_session)
        repo = SqlAlchemyCommunityMemberRepository(db_session)

        first = CommunityMember.create(community_id=CommunityId(community.id), user_id=user_id)
        await repo.add(first)
        await db_session.commit()

        second = CommunityMember.create(community_id=CommunityId(community.id), user_id=user_id)
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestCommunityMemberRequiresValidReferences:
    async def test_nonexistent_community_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        user = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityMemberRepository(db_session)

        member = CommunityMember.create(community_id=CommunityId(uuid4()), user_id=user.id)
        await repo.add(member)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_user_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityMemberRepository(db_session)

        member = CommunityMember.create(community_id=CommunityId(community.id), user_id=uuid4())
        await repo.add(member)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestCommunityMemberModelDirectInsert:
    async def test_model_insert_and_query(self, db_session: AsyncSession) -> None:
        community, user_id = await _seed(db_session)
        model = CommunityMemberModel(
            community_id=community.id,
            user_id=user_id,
            role=CommunityRole.ADMIN,
            status=CommunityMemberStatus.ACTIVE,
        )
        db_session.add(model)
        await db_session.commit()

        reloaded = await db_session.get(CommunityMemberModel, model.id)
        assert reloaded is not None
        assert reloaded.role is CommunityRole.ADMIN
        assert reloaded.status is CommunityMemberStatus.ACTIVE
