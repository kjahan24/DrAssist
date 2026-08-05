"""`DeleteCommunityService` — soft-deletes a community.

Not named in this task's own APPLICATION service list, but required by
its own API section's explicit "CRUD endpoints" (Delete being the one
CRUD verb that section's own service list otherwise omits) — added here
rather than left as a gap, per "no half-finished implementations."
Requires the acting user to hold `OWNER` role (the highest bar of any
mutating service in this module — deleting the whole community, unlike
updating its profile, is deliberately not delegated to `ADMIN`).
"""

from app.modules.community.application.dto import DeleteCommunityInput
from app.modules.community.application.services._authorization import ensure_role_at_least
from app.modules.community.domain.enums import CommunityRole
from app.modules.community.domain.exceptions import CommunityNotFoundError
from app.modules.community.domain.repositories import CommunityMemberRepository, CommunityRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class DeleteCommunityService(UseCase[DeleteCommunityInput, None]):
    def __init__(
        self,
        *,
        community_repository: CommunityRepository,
        community_member_repository: CommunityMemberRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._communities = community_repository
        self._members = community_member_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: DeleteCommunityInput) -> None:
        community = await self._communities.get_by_id(input_dto.community_id)
        if community is None:
            raise CommunityNotFoundError(input_dto.community_id)

        member = await self._members.get_by_community_and_user(
            input_dto.community_id, input_dto.acting_user_id
        )
        ensure_role_at_least(
            member,
            CommunityRole.OWNER,
            community_id=input_dto.community_id,
            user_id=input_dto.acting_user_id,
        )

        await self._communities.remove(input_dto.community_id)
        await self._uow.commit()
