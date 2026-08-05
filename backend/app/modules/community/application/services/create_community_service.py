"""`CreateCommunityService` — creates a new community *and* its creator's
`OWNER` membership in one transaction.

Creating both together, with no standalone "add owner" step, is what
makes the "every community has exactly one creator-assigned `OWNER`"
invariant impossible to violate rather than something that has to be
checked for — the same shape `app.modules.organization.application
.use_cases.create_organization.CreateOrganization` establishes for its
own `Organization`/`OrganizationSettings` pair.

Named `...Service` (not `...UseCase`) per this task's own literal
CREATE/APPLICATION wording ("Create services: CreateCommunityService,
..."), but implements the exact same `UseCase[InputDTO, OutputDTO]`
contract every mutating command in this codebase already uses — a pure
naming choice, not a different shape. See `container.py`'s own module
docstring for the same reasoning applied to every mutating service in
this module.
"""

from app.modules.community.application.dto import CreateCommunityInput, CreateCommunityOutput
from app.modules.community.domain.entities import Community, CommunityMember
from app.modules.community.domain.enums import CommunityRole
from app.modules.community.domain.exceptions import DuplicateCommunitySlugError
from app.modules.community.domain.repositories import CommunityMemberRepository, CommunityRepository
from app.modules.community.domain.value_objects import (
    CommunityDescription,
    CommunityId,
    CommunityName,
    CommunitySlug,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CreateCommunityService(UseCase[CreateCommunityInput, CreateCommunityOutput]):
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

    async def execute(self, input_dto: CreateCommunityInput) -> CreateCommunityOutput:
        slug = CommunitySlug(input_dto.slug)
        name = CommunityName(input_dto.name)
        description = CommunityDescription(input_dto.description) if input_dto.description else None

        existing = await self._communities.get_by_slug(input_dto.organization_id, str(slug))
        if existing is not None:
            raise DuplicateCommunitySlugError(str(slug))

        community = Community.create(
            organization_id=input_dto.organization_id,
            slug=slug,
            name=name,
            description=description,
            visibility=input_dto.visibility,
            created_by=input_dto.created_by,
        )
        owner_member = CommunityMember.create(
            community_id=CommunityId(community.id),
            user_id=input_dto.created_by,
            role=CommunityRole.OWNER,
        )

        await self._communities.add(community)
        await self._members.add(owner_member)

        self._uow.collect_events(community.pull_events())
        self._uow.collect_events(owner_member.pull_events())
        await self._uow.commit()

        return CreateCommunityOutput(
            community_id=community.id,
            organization_id=community.organization_id,
            slug=str(community.slug),
            name=str(community.name),
            visibility=community.visibility,
        )
