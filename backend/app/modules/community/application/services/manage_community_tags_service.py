"""`ManageCommunityTagsService` — assign/unassign reusable medical tags
to a community, plus tag search (autocomplete). Requires the acting user
to hold at least `ADMIN` role to assign/unassign — the same bar
`UpdateCommunityService` sets for other community-level changes; `search`
is a read-only lookup, open to any caller, needed before a community
even has an `ADMIN` context (composing the create/edit form).

`assign_tag` is get-or-create by name: a tag is genuinely reusable
(this task's own TAGS section), so assigning "diabetes" to a second
community must resolve to the *same* `CommunityTag` row, not create a
duplicate.
"""

from uuid import UUID

from app.modules.community.application.dto import (
    AssignCommunityTagInput,
    CommunityTagSummaryDTO,
    SearchCommunityTagsInput,
    SearchCommunityTagsOutput,
    UnassignCommunityTagInput,
)
from app.modules.community.application.services._authorization import ensure_role_at_least
from app.modules.community.application.services._summary_mappers import tag_to_summary
from app.modules.community.domain.entities import CommunityTag
from app.modules.community.domain.enums import CommunityRole
from app.modules.community.domain.exceptions import (
    CommunityTagAlreadyAssignedError,
    CommunityTagNotAssignedError,
    CommunityTagNotFoundError,
)
from app.modules.community.domain.repositories import (
    CommunityMemberRepository,
    CommunityTagRepository,
)
from app.modules.community.domain.value_objects import CommunityTagName
from app.shared.application.unit_of_work import UnitOfWork


class ManageCommunityTagsService:
    def __init__(
        self,
        *,
        community_tag_repository: CommunityTagRepository,
        community_member_repository: CommunityMemberRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._tags = community_tag_repository
        self._members = community_member_repository
        self._uow = unit_of_work

    async def assign_tag(self, input_dto: AssignCommunityTagInput) -> CommunityTagSummaryDTO:
        member = await self._members.get_by_community_and_user(
            input_dto.community_id, input_dto.acting_user_id
        )
        ensure_role_at_least(
            member,
            CommunityRole.ADMIN,
            community_id=input_dto.community_id,
            user_id=input_dto.acting_user_id,
        )

        name = CommunityTagName(input_dto.tag_name)
        tag = await self._tags.get_by_name(str(name))
        if tag is None:
            tag = CommunityTag.create(name=name)
            await self._tags.add(tag)
            self._uow.collect_events(tag.pull_events())

        if await self._tags.is_assigned(input_dto.community_id, tag.id):
            raise CommunityTagAlreadyAssignedError(input_dto.community_id, tag.id)

        await self._tags.assign(input_dto.community_id, tag.id)
        await self._uow.commit()

        return tag_to_summary(tag)

    async def unassign_tag(self, input_dto: UnassignCommunityTagInput) -> None:
        member = await self._members.get_by_community_and_user(
            input_dto.community_id, input_dto.acting_user_id
        )
        ensure_role_at_least(
            member,
            CommunityRole.ADMIN,
            community_id=input_dto.community_id,
            user_id=input_dto.acting_user_id,
        )

        tag = await self._tags.get_by_id(input_dto.tag_id)
        if tag is None:
            raise CommunityTagNotFoundError(input_dto.tag_id)
        if not await self._tags.is_assigned(input_dto.community_id, input_dto.tag_id):
            raise CommunityTagNotAssignedError(input_dto.community_id, input_dto.tag_id)

        await self._tags.unassign(input_dto.community_id, input_dto.tag_id)
        await self._uow.commit()

    async def list_tags_for_community(self, community_id: UUID) -> list[CommunityTagSummaryDTO]:
        tags = await self._tags.list_for_community(community_id)
        return [tag_to_summary(tag) for tag in tags]

    async def search_tags(self, input_dto: SearchCommunityTagsInput) -> SearchCommunityTagsOutput:
        tags, total = await self._tags.search(
            input_dto.query, offset=input_dto.offset, limit=input_dto.limit
        )
        return SearchCommunityTagsOutput(items=tuple(tag_to_summary(t) for t in tags), total=total)
