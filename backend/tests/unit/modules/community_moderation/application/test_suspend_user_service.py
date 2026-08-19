"""Unit tests for `SuspendUserService`, using in-memory fakes. Covers the
`duration_days is None` -> `PERMANENT_BAN` branch and its stricter
`ADMIN`-or-above authorization bar — see the service's own docstring."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_moderation.application.dto import SuspendUserInput
from app.modules.community_moderation.application.services.suspend_user_service import (
    SuspendUserService,
)
from app.modules.community_moderation.domain.enums import (
    ModerationActionType,
    ModerationRestrictionType,
)
from app.modules.community_moderation.domain.exceptions import (
    CannotModerateSelfError,
    InsufficientAdminRoleError,
    InsufficientModeratorRoleError,
    UserNotFoundForModerationError,
)
from tests.unit.modules.community_moderation.application.fakes import (
    FakeCommunityQueryPort,
    FakeModerationActionRepository,
    FakeModerationRestrictionRepository,
    FakeUnitOfWork,
    FakeUserQueryPort,
    make_member_summary,
    make_user_summary,
)


def _seeded() -> (
    tuple[
        SuspendUserService,
        FakeModerationRestrictionRepository,
        FakeModerationActionRepository,
        FakeCommunityQueryPort,
        FakeUserQueryPort,
        FakeUnitOfWork,
    ]
):
    restrictions = FakeModerationRestrictionRepository()
    actions = FakeModerationActionRepository()
    communities = FakeCommunityQueryPort()
    users = FakeUserQueryPort()
    uow = FakeUnitOfWork()
    service = SuspendUserService(
        restriction_repository=restrictions,
        action_repository=actions,
        community_query_port=communities,
        user_query_port=users,
        unit_of_work=uow,
    )
    return service, restrictions, actions, communities, users, uow


class TestTemporarySuspension:
    async def test_moderator_rank_can_issue_a_time_bounded_suspension(self) -> None:
        service, restrictions, actions, communities, users, _ = _seeded()
        org_id, community_id, moderator_id, target_id = uuid4(), uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=target_id, organization_id=org_id))
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        output = await service.execute(
            SuspendUserInput(
                organization_id=org_id,
                community_id=community_id,
                moderator_id=moderator_id,
                user_id=target_id,
                reason="Repeated abuse.",
                duration_days=14,
            )
        )
        assert output.restriction_type is ModerationRestrictionType.SUSPENSION
        assert output.ends_at is not None
        latest, _ = await actions.list_for_actor(moderator_id)
        assert latest[0].action_type is ModerationActionType.SUSPEND_USER

    async def test_member_without_moderator_rank_raises(self) -> None:
        service, _, _, communities, users, _ = _seeded()
        org_id, community_id, member_id, target_id = uuid4(), uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=target_id, organization_id=org_id))
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=member_id, role=CommunityRole.MEMBER
            )
        )
        with pytest.raises(InsufficientModeratorRoleError):
            await service.execute(
                SuspendUserInput(
                    organization_id=org_id,
                    community_id=community_id,
                    moderator_id=member_id,
                    user_id=target_id,
                    reason="Not authorized.",
                    duration_days=7,
                )
            )


class TestPermanentBan:
    async def test_admin_rank_can_issue_a_permanent_ban(self) -> None:
        service, restrictions, actions, communities, users, _ = _seeded()
        org_id, community_id, admin_id, target_id = uuid4(), uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=target_id, organization_id=org_id))
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=admin_id, role=CommunityRole.ADMIN
            )
        )
        output = await service.execute(
            SuspendUserInput(
                organization_id=org_id,
                community_id=community_id,
                moderator_id=admin_id,
                user_id=target_id,
                reason="Severe, repeated policy violations.",
                duration_days=None,
            )
        )
        assert output.restriction_type is ModerationRestrictionType.PERMANENT_BAN
        assert output.ends_at is None
        latest, _ = await actions.list_for_actor(admin_id)
        assert latest[0].action_type is ModerationActionType.BAN_USER

    async def test_owner_rank_can_issue_a_permanent_ban(self) -> None:
        service, _, _, communities, users, _ = _seeded()
        org_id, community_id, owner_id, target_id = uuid4(), uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=target_id, organization_id=org_id))
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=owner_id, role=CommunityRole.OWNER
            )
        )
        output = await service.execute(
            SuspendUserInput(
                organization_id=org_id,
                community_id=community_id,
                moderator_id=owner_id,
                user_id=target_id,
                reason="Severe violation.",
                duration_days=None,
            )
        )
        assert output.restriction_type is ModerationRestrictionType.PERMANENT_BAN

    async def test_plain_moderator_rank_cannot_issue_a_permanent_ban(self) -> None:
        """The bar is strictly higher than a time-bounded suspension —
        `MODERATOR` rank is sufficient for `SUSPENSION` but not for
        `PERMANENT_BAN`."""
        service, _, _, communities, users, _ = _seeded()
        org_id, community_id, moderator_id, target_id = uuid4(), uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=target_id, organization_id=org_id))
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        with pytest.raises(InsufficientAdminRoleError):
            await service.execute(
                SuspendUserInput(
                    organization_id=org_id,
                    community_id=community_id,
                    moderator_id=moderator_id,
                    user_id=target_id,
                    reason="Attempting a ban without admin rank.",
                    duration_days=None,
                )
            )

    async def test_cannot_ban_self(self) -> None:
        service, _, _, communities, users, _ = _seeded()
        org_id, community_id, admin_id = uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=admin_id, organization_id=org_id))
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=admin_id, role=CommunityRole.ADMIN
            )
        )
        with pytest.raises(CannotModerateSelfError):
            await service.execute(
                SuspendUserInput(
                    organization_id=org_id,
                    community_id=community_id,
                    moderator_id=admin_id,
                    user_id=admin_id,
                    reason="Self ban attempt.",
                    duration_days=None,
                )
            )

    async def test_unknown_target_user_raises(self) -> None:
        service, _, _, communities, _, _ = _seeded()
        org_id, community_id, admin_id = uuid4(), uuid4(), uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=admin_id, role=CommunityRole.ADMIN
            )
        )
        with pytest.raises(UserNotFoundForModerationError):
            await service.execute(
                SuspendUserInput(
                    organization_id=org_id,
                    community_id=community_id,
                    moderator_id=admin_id,
                    user_id=uuid4(),
                    reason="Doesn't exist.",
                    duration_days=None,
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, _, communities, users, uow = _seeded()
        org_id, community_id, admin_id, target_id = uuid4(), uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=target_id, organization_id=org_id))
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=admin_id, role=CommunityRole.ADMIN
            )
        )
        await service.execute(
            SuspendUserInput(
                organization_id=org_id,
                community_id=community_id,
                moderator_id=admin_id,
                user_id=target_id,
                reason="Banned.",
                duration_days=None,
            )
        )
        assert uow.committed is True
