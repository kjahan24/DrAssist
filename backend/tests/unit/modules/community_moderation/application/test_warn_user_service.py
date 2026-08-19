"""Unit tests for `WarnUserService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_moderation.application.dto import WarnUserInput
from app.modules.community_moderation.application.services.warn_user_service import (
    WarnUserService,
)
from app.modules.community_moderation.domain.enums import (
    ModerationActionType,
    ModerationRestrictionType,
    ModerationTargetType,
)
from app.modules.community_moderation.domain.events import ModerationRestrictionIssued
from app.modules.community_moderation.domain.exceptions import (
    CannotModerateSelfError,
    InsufficientModeratorRoleError,
    ModerationMembershipRequiredError,
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
        WarnUserService,
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
    service = WarnUserService(
        restriction_repository=restrictions,
        action_repository=actions,
        community_query_port=communities,
        user_query_port=users,
        unit_of_work=uow,
    )
    return service, restrictions, actions, communities, users, uow


class TestWarnUser:
    async def test_issues_a_warning(self) -> None:
        service, restrictions, _, communities, users, _ = _seeded()
        org_id, community_id, moderator_id, target_id = uuid4(), uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=target_id, organization_id=org_id))
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        output = await service.execute(
            WarnUserInput(
                organization_id=org_id,
                community_id=community_id,
                moderator_id=moderator_id,
                user_id=target_id,
                reason="Repeated spam links.",
            )
        )
        assert output.restriction_type is ModerationRestrictionType.WARNING
        assert output.ends_at is None
        stored = await restrictions.get_by_id(output.restriction_id)
        assert stored is not None

    async def test_records_a_moderation_action(self) -> None:
        service, _, actions, communities, users, _ = _seeded()
        org_id, community_id, moderator_id, target_id = uuid4(), uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=target_id, organization_id=org_id))
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        await service.execute(
            WarnUserInput(
                organization_id=org_id,
                community_id=community_id,
                moderator_id=moderator_id,
                user_id=target_id,
                reason="Repeated spam links.",
            )
        )
        latest, _ = await actions.list_for_actor(moderator_id)
        assert len(latest) == 1
        assert latest[0].action_type is ModerationActionType.WARN_USER
        assert latest[0].target_type is ModerationTargetType.USER
        assert latest[0].target_id == target_id

    async def test_cannot_warn_self(self) -> None:
        service, _, _, communities, users, _ = _seeded()
        org_id, community_id, user_id = uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=user_id, organization_id=org_id))
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=user_id, role=CommunityRole.MODERATOR
            )
        )
        with pytest.raises(CannotModerateSelfError):
            await service.execute(
                WarnUserInput(
                    organization_id=org_id,
                    community_id=community_id,
                    moderator_id=user_id,
                    user_id=user_id,
                    reason="Self warn attempt.",
                )
            )

    async def test_unknown_target_user_raises(self) -> None:
        service, _, _, communities, _, _ = _seeded()
        org_id, community_id, moderator_id = uuid4(), uuid4(), uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        with pytest.raises(UserNotFoundForModerationError):
            await service.execute(
                WarnUserInput(
                    organization_id=org_id,
                    community_id=community_id,
                    moderator_id=moderator_id,
                    user_id=uuid4(),
                    reason="Doesn't exist.",
                )
            )

    async def test_cross_tenant_target_user_raises(self) -> None:
        service, _, _, communities, users, _ = _seeded()
        org_id, community_id, moderator_id, target_id = uuid4(), uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=target_id, organization_id=uuid4()))
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        with pytest.raises(UserNotFoundForModerationError):
            await service.execute(
                WarnUserInput(
                    organization_id=org_id,
                    community_id=community_id,
                    moderator_id=moderator_id,
                    user_id=target_id,
                    reason="Cross tenant.",
                )
            )

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
                WarnUserInput(
                    organization_id=org_id,
                    community_id=community_id,
                    moderator_id=member_id,
                    user_id=target_id,
                    reason="Not authorized.",
                )
            )

    async def test_non_member_moderator_raises(self) -> None:
        service, _, _, _, users, _ = _seeded()
        org_id, community_id, moderator_id, target_id = uuid4(), uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=target_id, organization_id=org_id))
        with pytest.raises(ModerationMembershipRequiredError):
            await service.execute(
                WarnUserInput(
                    organization_id=org_id,
                    community_id=community_id,
                    moderator_id=moderator_id,
                    user_id=target_id,
                    reason="Not a member.",
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, _, communities, users, uow = _seeded()
        org_id, community_id, moderator_id, target_id = uuid4(), uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=target_id, organization_id=org_id))
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        await service.execute(
            WarnUserInput(
                organization_id=org_id,
                community_id=community_id,
                moderator_id=moderator_id,
                user_id=target_id,
                reason="Warned.",
            )
        )
        assert uow.committed is True

    async def test_publishes_a_restriction_issued_event(self) -> None:
        service, _, _, communities, users, uow = _seeded()
        org_id, community_id, moderator_id, target_id = uuid4(), uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=target_id, organization_id=org_id))
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        await service.execute(
            WarnUserInput(
                organization_id=org_id,
                community_id=community_id,
                moderator_id=moderator_id,
                user_id=target_id,
                reason="Warned.",
            )
        )
        assert any(isinstance(e, ModerationRestrictionIssued) for e in uow.published_events)
