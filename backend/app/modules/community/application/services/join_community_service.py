"""`JoinCommunityService` — the caller joins a community as themselves
(there is no "join on behalf of another user"; `user_id` is always the
acting principal, matching every other self-service action in this
codebase).

`CommunityVisibility` enforcement at this foundation stage: `PUBLIC`
communities accept a direct, first-time join unconditionally. `PRIVATE`
and `VERIFIED_ONLY` both require an existing `INVITED` membership row to
accept instead (`PrivateCommunityJoinRequiresInviteError` otherwise) —
this task explicitly excludes any invitation-issuing service from this
foundation, so no endpoint here ever *creates* an `INVITED` row, but the
join path that *accepts* one is real and testable now, ready for a
future invitation module to produce those rows. `VERIFIED_ONLY` is
treated identically to `PRIVATE` (rather than checking some notion of
"verified professional") because verifying a caller's professional
status is not a fact this module owns or can check without depending on
another module's internals — see `container.py`'s own module docstring
for why this module has no such cross-module dependency today.
"""

from app.modules.community.application.dto import JoinCommunityInput, JoinCommunityOutput
from app.modules.community.domain.entities import CommunityMember
from app.modules.community.domain.enums import CommunityMemberStatus, CommunityVisibility
from app.modules.community.domain.exceptions import (
    CommunityMemberBlockedError,
    CommunityMembershipAlreadyExistsError,
    CommunityNotFoundError,
    PrivateCommunityJoinRequiresInviteError,
)
from app.modules.community.domain.repositories import CommunityMemberRepository, CommunityRepository
from app.modules.community.domain.value_objects import CommunityId
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class JoinCommunityService(UseCase[JoinCommunityInput, JoinCommunityOutput]):
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

    async def execute(self, input_dto: JoinCommunityInput) -> JoinCommunityOutput:
        community = await self._communities.get_by_id(input_dto.community_id)
        if community is None:
            raise CommunityNotFoundError(input_dto.community_id)

        existing = await self._members.get_by_community_and_user(
            input_dto.community_id, input_dto.user_id
        )

        if existing is None:
            if community.visibility is not CommunityVisibility.PUBLIC:
                raise PrivateCommunityJoinRequiresInviteError(input_dto.community_id)
            member = CommunityMember.create(
                community_id=CommunityId(community.id), user_id=input_dto.user_id
            )
            await self._members.add(member)
        elif existing.status is CommunityMemberStatus.ACTIVE:
            raise CommunityMembershipAlreadyExistsError(input_dto.community_id, input_dto.user_id)
        elif existing.status is CommunityMemberStatus.BLOCKED:
            raise CommunityMemberBlockedError(input_dto.community_id, input_dto.user_id)
        elif existing.status is CommunityMemberStatus.LEFT:
            if community.visibility is not CommunityVisibility.PUBLIC:
                raise PrivateCommunityJoinRequiresInviteError(input_dto.community_id)
            existing.rejoin()
            await self._members.add(existing)
            member = existing
        else:  # INVITED — accepting an invitation is always allowed, regardless of visibility
            existing.rejoin()
            await self._members.add(existing)
            member = existing

        self._uow.collect_events(member.pull_events())
        await self._uow.commit()

        return JoinCommunityOutput(
            member_id=member.id,
            community_id=member.community_id.value,
            user_id=member.user_id,
            role=member.role,
            status=member.status,
            joined_at=member.joined_at,
        )
