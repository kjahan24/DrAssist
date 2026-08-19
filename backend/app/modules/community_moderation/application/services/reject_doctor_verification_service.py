"""`RejectDoctorVerificationService` — denies a pending verification
request. Gated the same way as `ApproveDoctorVerificationService` — see
that file's own docstring."""

from app.modules.community_moderation.application.dto import (
    RejectDoctorVerificationInput,
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


class RejectDoctorVerificationService:
    def __init__(
        self,
        *,
        verification_repository: DoctorVerificationRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._verifications = verification_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: RejectDoctorVerificationInput) -> VerificationSummaryDTO:
        verification = await self._verifications.get_by_id(input_dto.verification_id)
        if verification is None:
            raise DoctorVerificationNotFoundError(input_dto.verification_id)
        if verification.user_id == input_dto.verifier_id:
            raise CannotVerifySelfError(input_dto.verifier_id)

        verification.reject(verifier_id=input_dto.verifier_id, reason=input_dto.reason)
        await self._verifications.add(verification)
        self._uow.collect_events(verification.pull_events())
        await self._uow.commit()
        return verification_to_summary(verification)
