"""`AcceptInvitation` (Pending -> Accepted)."""

from datetime import UTC, datetime

from app.modules.family_access.application.dto import (
    AcceptInvitationInput,
    FamilyAccessStatusOutput,
)
from app.modules.family_access.domain.exceptions import FamilyAccessNotFoundError
from app.modules.family_access.domain.repositories import FamilyAccessRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class AcceptInvitation(UseCase[AcceptInvitationInput, FamilyAccessStatusOutput]):
    def __init__(
        self, *, family_access_repository: FamilyAccessRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._grants = family_access_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: AcceptInvitationInput) -> FamilyAccessStatusOutput:
        grant = await self._grants.get_by_id(input_dto.family_access_id)
        if grant is None:
            raise FamilyAccessNotFoundError(input_dto.family_access_id)

        grant.accept(now=datetime.now(UTC))
        await self._grants.add(grant)
        self._uow.collect_events(grant.pull_events())
        await self._uow.commit()

        return FamilyAccessStatusOutput(family_access_id=grant.id, status=grant.status)
