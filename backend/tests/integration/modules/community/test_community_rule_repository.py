"""Integration tests for `SqlAlchemyCommunityRuleRepository`, including
its FK to `communities` and the hard-delete behavior of `remove`,
against a real PostgreSQL instance."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community._helpers import persist_organization

from app.modules.community.domain.entities import Community, CommunityRule
from app.modules.community.domain.value_objects import (
    CommunityId,
    CommunityName,
    CommunityRuleTitle,
    CommunitySlug,
)
from app.modules.community.infrastructure.models import CommunityRuleModel
from app.modules.community.infrastructure.repositories import (
    SqlAlchemyCommunityRepository,
    SqlAlchemyCommunityRuleRepository,
)


def _unique_suffix() -> str:
    return uuid4().hex[:12]


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


def _make_rule(*, community_id: CommunityId, **overrides: object) -> CommunityRule:
    defaults: dict[str, object] = {
        "community_id": community_id,
        "title": CommunityRuleTitle("Be respectful"),
    }
    defaults.update(overrides)
    return CommunityRule.create(**defaults)  # type: ignore[arg-type]


class TestCommunityRuleRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityRuleRepository(db_session)

        rule = _make_rule(
            community_id=CommunityId(community.id),
            title=CommunityRuleTitle("No harassment"),
            description="Be kind to others.",
            position=2,
        )
        await repo.add(rule)
        await db_session.commit()

        reloaded = await repo.get_by_id(rule.id)
        assert reloaded is not None
        assert reloaded.community_id.value == community.id
        assert str(reloaded.title) == "No harassment"
        assert reloaded.description == "Be kind to others."
        assert reloaded.position == 2
        assert reloaded.is_enabled is True

    async def test_update_round_trips(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityRuleRepository(db_session)

        rule = _make_rule(community_id=CommunityId(community.id))
        await repo.add(rule)
        await db_session.commit()

        rule.set_enabled(False)
        rule.reposition(5)
        await repo.add(rule)
        await db_session.commit()

        reloaded = await repo.get_by_id(rule.id)
        assert reloaded is not None
        assert reloaded.is_enabled is False
        assert reloaded.position == 5


class TestGetById:
    async def test_returns_none_for_an_unknown_id(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityRuleRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None


class TestListByCommunity:
    async def test_orders_by_position(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityRuleRepository(db_session)

        second = _make_rule(
            community_id=CommunityId(community.id), title=CommunityRuleTitle("Second"), position=1
        )
        first = _make_rule(
            community_id=CommunityId(community.id), title=CommunityRuleTitle("First"), position=0
        )
        await repo.add(second)
        await repo.add(first)
        await db_session.commit()

        results = await repo.list_by_community(community.id)

        assert [r.id for r in results] == [first.id, second.id]

    async def test_excludes_disabled_when_requested(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityRuleRepository(db_session)

        enabled = _make_rule(
            community_id=CommunityId(community.id), title=CommunityRuleTitle("Enabled")
        )
        disabled = _make_rule(
            community_id=CommunityId(community.id), title=CommunityRuleTitle("Disabled")
        )
        disabled.set_enabled(False)
        await repo.add(enabled)
        await repo.add(disabled)
        await db_session.commit()

        results = await repo.list_by_community(community.id, include_disabled=False)

        assert [r.id for r in results] == [enabled.id]

    async def test_scopes_to_the_community(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community_a = await _persist_community(db_session, organization_id=organization.id)
        community_b = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityRuleRepository(db_session)

        rule_a = _make_rule(community_id=CommunityId(community_a.id))
        rule_b = _make_rule(community_id=CommunityId(community_b.id))
        await repo.add(rule_a)
        await repo.add(rule_b)
        await db_session.commit()

        results = await repo.list_by_community(community_a.id)

        assert [r.id for r in results] == [rule_a.id]


class TestCountByCommunity:
    async def test_counts_all_rules_regardless_of_enabled_state(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityRuleRepository(db_session)

        enabled = _make_rule(community_id=CommunityId(community.id))
        disabled = _make_rule(community_id=CommunityId(community.id))
        disabled.set_enabled(False)
        await repo.add(enabled)
        await repo.add(disabled)
        await db_session.commit()

        assert await repo.count_by_community(community.id) == 2

    async def test_returns_zero_for_a_community_with_no_rules(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityRuleRepository(db_session)

        assert await repo.count_by_community(community.id) == 0


class TestRemove:
    async def test_hard_deletes_the_row(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityRuleRepository(db_session)
        rule = _make_rule(community_id=CommunityId(community.id))
        await repo.add(rule)
        await db_session.commit()

        await repo.remove(rule.id)
        await db_session.commit()

        assert await db_session.get(CommunityRuleModel, rule.id) is None

    async def test_is_a_no_op_for_an_unknown_id(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityRuleRepository(db_session)
        await repo.remove(uuid4())  # must not raise
        await db_session.commit()


class TestCommunityRuleRequiresValidReferences:
    async def test_nonexistent_community_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCommunityRuleRepository(db_session)
        rule = _make_rule(community_id=CommunityId(uuid4()))
        await repo.add(rule)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestCommunityRuleModelDirectInsert:
    async def test_model_insert_and_query(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        community = await _persist_community(db_session, organization_id=organization.id)
        model = CommunityRuleModel(
            community_id=community.id, title="Direct Insert Rule", position=0
        )
        db_session.add(model)
        await db_session.commit()

        reloaded = await db_session.get(CommunityRuleModel, model.id)
        assert reloaded is not None
        assert reloaded.title == "Direct Insert Rule"
        assert reloaded.is_enabled is True
