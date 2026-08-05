"""Unit tests for `LeaveCommunityService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.application.dto import LeaveCommunityInput
from app.modules.community.application.services.leave_community_service import (
    LeaveCommunityService,
)
from app.modules.community.domain.entities import CommunityMember
from app.modules.community.domain.enums import CommunityMemberStatus, CommunityRole
from app.modules.community.domain.events import CommunityMemberLeft
from app.modules.community.domain.exceptions import (
    CommunityMembershipNotFoundError,
    CommunityOwnerRequiredError,
)
from app.modules.community.domain.value_objects import CommunityId
from tests.unit.modules.community.application.fakes import (
    FakeCommunityMemberRepository,
    FakeUnitOfWork,
)


def _service() -> tuple[LeaveCommunityService, FakeCommunityMemberRepository, FakeUnitOfWork]:
    members = FakeCommunityMemberRepository()
    uow = FakeUnitOfWork()
    service = LeaveCommunityService(community_member_repository=members, unit_of_work=uow)
    return service, members, uow


class TestLeaveCommunity:
    async def test_sets_member_status_to_left(self) -> None:
        service, members, _ = _service()
        community_id = uuid4()
        user_id = uuid4()
        member = CommunityMember.create(
            community_id=CommunityId(community_id), user_id=user_id, role=CommunityRole.MEMBER
        )
        await members.add(member)

        await service.execute(LeaveCommunityInput(community_id=community_id, user_id=user_id))

        stored = await members.get_by_community_and_user(community_id, user_id)
        assert stored is not None
        assert stored.status is CommunityMemberStatus.LEFT

    async def test_commits_the_unit_of_work(self) -> None:
        service, members, uow = _service()
        community_id = uuid4()
        user_id = uuid4()
        member = CommunityMember.create(
            community_id=CommunityId(community_id), user_id=user_id, role=CommunityRole.MEMBER
        )
        await members.add(member)

        await service.execute(LeaveCommunityInput(community_id=community_id, user_id=user_id))

        assert uow.committed is True

    async def test_publishes_a_member_left_event(self) -> None:
        service, members, uow = _service()
        community_id = uuid4()
        user_id = uuid4()
        member = CommunityMember.create(
            community_id=CommunityId(community_id), user_id=user_id, role=CommunityRole.MEMBER
        )
        await members.add(member)

        await service.execute(LeaveCommunityInput(community_id=community_id, user_id=user_id))

        assert any(isinstance(e, CommunityMemberLeft) for e in uow.published_events)

    async def test_no_membership_raises(self) -> None:
        service, _, _ = _service()
        with pytest.raises(CommunityMembershipNotFoundError):
            await service.execute(LeaveCommunityInput(community_id=uuid4(), user_id=uuid4()))

    async def test_already_left_membership_raises(self) -> None:
        service, members, _ = _service()
        community_id = uuid4()
        user_id = uuid4()
        member = CommunityMember.create(community_id=CommunityId(community_id), user_id=user_id)
        member.leave()
        await members.add(member)

        with pytest.raises(CommunityMembershipNotFoundError):
            await service.execute(LeaveCommunityInput(community_id=community_id, user_id=user_id))

    async def test_sole_owner_cannot_leave(self) -> None:
        service, members, _ = _service()
        community_id = uuid4()
        owner_id = uuid4()
        owner = CommunityMember.create(
            community_id=CommunityId(community_id), user_id=owner_id, role=CommunityRole.OWNER
        )
        await members.add(owner)

        with pytest.raises(CommunityOwnerRequiredError):
            await service.execute(LeaveCommunityInput(community_id=community_id, user_id=owner_id))

    async def test_owner_may_leave_when_another_active_owner_remains(self) -> None:
        service, members, _ = _service()
        community_id = uuid4()
        owner_a_id = uuid4()
        owner_b_id = uuid4()
        owner_a = CommunityMember.create(
            community_id=CommunityId(community_id), user_id=owner_a_id, role=CommunityRole.OWNER
        )
        owner_b = CommunityMember.create(
            community_id=CommunityId(community_id), user_id=owner_b_id, role=CommunityRole.OWNER
        )
        await members.add(owner_a)
        await members.add(owner_b)

        await service.execute(LeaveCommunityInput(community_id=community_id, user_id=owner_a_id))

        stored = await members.get_by_community_and_user(community_id, owner_a_id)
        assert stored is not None
        assert stored.status is CommunityMemberStatus.LEFT

    async def test_owner_may_leave_when_another_owner_is_only_left_not_active(self) -> None:
        """A `LEFT` owner does not count toward the "at least one active
        owner" invariant — leaving the sole *active* owner is still
        blocked even if a previously-left owner row exists."""
        service, members, _ = _service()
        community_id = uuid4()
        active_owner_id = uuid4()
        former_owner_id = uuid4()
        active_owner = CommunityMember.create(
            community_id=CommunityId(community_id),
            user_id=active_owner_id,
            role=CommunityRole.OWNER,
        )
        former_owner = CommunityMember.create(
            community_id=CommunityId(community_id),
            user_id=former_owner_id,
            role=CommunityRole.OWNER,
        )
        former_owner.leave()
        await members.add(active_owner)
        await members.add(former_owner)

        with pytest.raises(CommunityOwnerRequiredError):
            await service.execute(
                LeaveCommunityInput(community_id=community_id, user_id=active_owner_id)
            )

    async def test_non_owner_may_always_leave(self) -> None:
        service, members, _ = _service()
        community_id = uuid4()
        moderator_id = uuid4()
        moderator = CommunityMember.create(
            community_id=CommunityId(community_id),
            user_id=moderator_id,
            role=CommunityRole.MODERATOR,
        )
        await members.add(moderator)

        await service.execute(LeaveCommunityInput(community_id=community_id, user_id=moderator_id))

        stored = await members.get_by_community_and_user(community_id, moderator_id)
        assert stored is not None
        assert stored.status is CommunityMemberStatus.LEFT
