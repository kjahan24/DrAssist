"""`LeaveCommunityService` — the caller leaves a community as themselves.

Enforces "a community must always retain at least one `OWNER`": if the
leaving member is the community's only active `OWNER`,
`CommunityOwnerRequiredError` is raised instead of leaving them
ownerless — this task's own APPLICATION section doesn't name a
"TransferOwnership"/"RemoveMember" service, so there is deliberately no
escape hatch here yet; a sole owner must hand off ownership through a
future module before they can leave.
"""

from app.modules.community.application.dto import LeaveCommunityInput
from app.modules.community.domain.enums import CommunityMemberStatus, CommunityRole
from app.modules.community.domain.exceptions import (
    CommunityMembershipNotFoundError,
    CommunityOwnerRequiredError,
)
from app.modules.community.domain.repositories import CommunityMemberRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class LeaveCommunityService(UseCase[LeaveCommunityInput, None]):
    def __init__(
        self, *, community_member_repository: CommunityMemberRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._members = community_member_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: LeaveCommunityInput) -> None:
        member = await self._members.get_by_community_and_user(
            input_dto.community_id, input_dto.user_id
        )
        if member is None or member.status is not CommunityMemberStatus.ACTIVE:
            raise CommunityMembershipNotFoundError(input_dto.community_id, input_dto.user_id)

        if member.role is CommunityRole.OWNER:
            owner_count = await self._members.count_active_by_role(
                input_dto.community_id, CommunityRole.OWNER
            )
            if owner_count <= 1:
                raise CommunityOwnerRequiredError(input_dto.community_id)

        member.leave()
        await self._members.add(member)
        self._uow.collect_events(member.pull_events())
        await self._uow.commit()
