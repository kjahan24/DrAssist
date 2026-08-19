"""Unit tests for `RestrictUserService`, using in-memory fakes."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_moderation.application.dto import RestrictUserInput
from app.modules.community_moderation.application.services.restrict_user_service import (
    RestrictUserService,
)
from app.modules.community_moderation.domain.enums import ModerationRestrictionType
from app.modules.community_moderation.domain.exceptions import (
    CannotModerateSelfError,
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
        RestrictUserService,
        FakeModerationRestrictionRepository,
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
    service = RestrictUserService(
        restriction_repository=restrictions,
        action_repository=actions,
        community_query_port=communities,
        user_query_port=users,
        unit_of_work=uow,
    )
    return service, restrictions, communities, users, uow


class TestRestrictUser:
    async def test_issues_a_time_bounded_restriction(self) -> None:
        service, restrictions, communities, users, _ = _seeded()
        org_id, community_id, moderator_id, target_id = uuid4(), uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=target_id, organization_id=org_id))
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        output = await service.execute(
            RestrictUserInput(
                organization_id=org_id,
                community_id=community_id,
                moderator_id=moderator_id,
                user_id=target_id,
                reason="Repeated rule violations.",
                duration_days=7,
            )
        )
        assert output.restriction_type is ModerationRestrictionType.TEMPORARY_RESTRICTION
        assert output.ends_at is not None
        assert output.ends_at > datetime.now(UTC)
        stored = await restrictions.get_by_id(output.restriction_id)
        assert stored is not None
        assert stored.is_active() is True

    async def test_cannot_restrict_self(self) -> None:
        service, _, communities, users, _ = _seeded()
        org_id, community_id, user_id = uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=user_id, organization_id=org_id))
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=user_id, role=CommunityRole.MODERATOR
            )
        )
        with pytest.raises(CannotModerateSelfError):
            await service.execute(
                RestrictUserInput(
                    organization_id=org_id,
                    community_id=community_id,
                    moderator_id=user_id,
                    user_id=user_id,
                    reason="Self restrict attempt.",
                    duration_days=3,
                )
            )

    async def test_unknown_target_user_raises(self) -> None:
        service, _, communities, _, _ = _seeded()
        org_id, community_id, moderator_id = uuid4(), uuid4(), uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        with pytest.raises(UserNotFoundForModerationError):
            await service.execute(
                RestrictUserInput(
                    organization_id=org_id,
                    community_id=community_id,
                    moderator_id=moderator_id,
                    user_id=uuid4(),
                    reason="Doesn't exist.",
                    duration_days=3,
                )
            )

    async def test_member_without_moderator_rank_raises(self) -> None:
        service, _, communities, users, _ = _seeded()
        org_id, community_id, member_id, target_id = uuid4(), uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=target_id, organization_id=org_id))
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=member_id, role=CommunityRole.MEMBER
            )
        )
        with pytest.raises(InsufficientModeratorRoleError):
            await service.execute(
                RestrictUserInput(
                    organization_id=org_id,
                    community_id=community_id,
                    moderator_id=member_id,
                    user_id=target_id,
                    reason="Not authorized.",
                    duration_days=3,
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, communities, users, uow = _seeded()
        org_id, community_id, moderator_id, target_id = uuid4(), uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=target_id, organization_id=org_id))
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        await service.execute(
            RestrictUserInput(
                organization_id=org_id,
                community_id=community_id,
                moderator_id=moderator_id,
                user_id=target_id,
                reason="Restricted.",
                duration_days=1,
            )
        )
        assert uow.committed is True
