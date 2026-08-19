"""`ApproveDoctorVerificationService` — grants the "Verified Doctor
Badge". Reachable only by a caller holding the `moderation.verify_doctor`
organization-level permission — enforced at the router via
`Depends(require_permission("moderation.verify_doctor"))`, the same
org-admin-permission-code gate `app.modules.community.presentation.router`
already uses for `communities.verify`/`communities.feature`, since
verifying medical credentials is a platform-level trust decision with no
natural single-community scope (unlike `ensure_is_moderator`'s
per-community rank check used everywhere else in this module). The
`CannotVerifySelfError` check here is defense in depth, independent of
that router-level gate."""

from app.modules.community_moderation.application.dto import (
    ApproveDoctorVerificationInput,
    VerificationSummaryDTO,
)
from app.modules.community_moderation.application.services._summary_mappers import (
    verification_to_summary,
)
from app.modules.community_moderation.domain.exceptions import (
    CannotVerifySelfError,
    DoctorVerificationNotFoundError,
)
from app.modules.community_moderation.domain.repositories import DoctorVerificationRepository
from app.shared.application.unit_of_work import UnitOfWork


class ApproveDoctorVerificationService:
    def __init__(
        self,
        *,
        verification_repository: DoctorVerificationRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._verifications = verification_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: ApproveDoctorVerificationInput) -> VerificationSummaryDTO:
        verification = await self._verifications.get_by_id(input_dto.verification_id)
        if verification is None:
            raise DoctorVerificationNotFoundError(input_dto.verification_id)
        if verification.user_id == input_dto.verifier_id:
            raise CannotVerifySelfError(input_dto.verifier_id)

        verification.approve(verifier_id=input_dto.verifier_id, specialty=input_dto.specialty)
        await self._verifications.add(verification)
        self._uow.collect_events(verification.pull_events())
        await self._uow.commit()
        return verification_to_summary(verification)
