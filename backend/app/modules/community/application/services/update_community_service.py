"""`UpdateCommunityService` — updates a community's own profile fields.

Requires the acting user to hold at least `ADMIN` role in the community
being updated — community-level settings (name/description/visibility)
are gated above plain `MEMBER`/`MODERATOR`, the same "settings changes
need elevated standing" precedent `app.modules.organization.application
.use_cases.update_organization_settings` establishes for organization-
wide settings (there, gated by tenant membership itself, since that
module has no finer-grained role concept; here, by `CommunityRole`).
"""

from app.modules.community.application.dto import UpdateCommunityInput, UpdateCommunityOutput
from app.modules.community.application.services._authorization import ensure_role_at_least
from app.modules.community.domain.enums import CommunityRole
from app.modules.community.domain.exceptions import CommunityNotFoundError
from app.modules.community.domain.repositories import CommunityMemberRepository, CommunityRepository
from app.modules.community.domain.value_objects import CommunityDescription, CommunityName
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class UpdateCommunityService(UseCase[UpdateCommunityInput, UpdateCommunityOutput]):
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

    async def execute(self, input_dto: UpdateCommunityInput) -> UpdateCommunityOutput:
        community = await self._communities.get_by_id(input_dto.community_id)
        if community is None:
            raise CommunityNotFoundError(input_dto.community_id)

        member = await self._members.get_by_community_and_user(
            input_dto.community_id, input_dto.acting_user_id
        )
        ensure_role_at_least(
            member,
            CommunityRole.ADMIN,
            community_id=input_dto.community_id,
            user_id=input_dto.acting_user_id,
        )

        name = CommunityName(input_dto.name) if input_dto.name is not None else None
        description = CommunityDescription(input_dto.description) if input_dto.description else None
        community.update_profile(
            name=name,
            description=description,
            clear_description=input_dto.clear_description,
            visibility=input_dto.visibility,
            updated_by=input_dto.acting_user_id,
        )

        await self._communities.add(community)
        self._uow.collect_events(community.pull_events())
        await self._uow.commit()

        return UpdateCommunityOutput(
            community_id=community.id,
            name=str(community.name),
            visibility=community.visibility,
        )
