"""`RequestDoctorVerificationService` — files (or resubmits) a "Verified
Doctor Badge" request. Self-request only — `input_dto.requesting_user_id`
must be the doctor's own `user_id` (read via the already-public
`DoctorQueryPort`); a mismatch collapses into
`DoctorNotFoundForVerificationError`, the same anti-enumeration posture
`_target_resolution.py`'s own docstring establishes elsewhere in this
module, so a caller can never probe whether a given `doctor_id` belongs to
someone else."""

from app.modules.community_moderation.application.dto import (
    RequestDoctorVerificationInput,
    VerificationSummaryDTO,
)
from app.modules.community_moderation.application.services._summary_mappers import (
    verification_to_summary,
)
from app.modules.community_moderation.domain.entities import DoctorVerification
from app.modules.community_moderation.domain.enums import VerificationStatus
from app.modules.community_moderation.domain.exceptions import (
    DoctorNotFoundForVerificationError,
    DoctorVerificationAlreadyPendingError,
    DoctorVerificationAlreadyVerifiedError,
)
from app.modules.community_moderation.domain.repositories import DoctorVerificationRepository
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.shared.application.unit_of_work import UnitOfWork


class RequestDoctorVerificationService:
    def __init__(
        self,
        *,
        verification_repository: DoctorVerificationRepository,
        doctor_query_port: DoctorQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._verifications = verification_repository
        self._doctors = doctor_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: RequestDoctorVerificationInput) -> VerificationSummaryDTO:
        doctor = await self._doctors.get_doctor_summary(input_dto.doctor_id)
        if doctor is None or doctor.user_id != input_dto.requesting_user_id:
            raise DoctorNotFoundForVerificationError(input_dto.doctor_id)

        existing = await self._verifications.get_by_doctor_id(input_dto.doctor_id)
        if existing is None:
            verification = DoctorVerification.request(
                doctor_id=doctor.doctor_id,
                user_id=doctor.user_id,
                organization_id=doctor.organization_id,
                specialty=input_dto.specialty,
                metadata=input_dto.metadata,
            )
        else:
            if existing.status is VerificationStatus.PENDING:
                raise DoctorVerificationAlreadyPendingError(input_dto.doctor_id)
            if existing.status is VerificationStatus.VERIFIED:
                raise DoctorVerificationAlreadyVerifiedError(input_dto.doctor_id)
            existing.resubmit(specialty=input_dto.specialty, metadata=input_dto.metadata)
            verification = existing

        await self._verifications.add(verification)
        self._uow.collect_events(verification.pull_events())
        await self._uow.commit()
        return verification_to_summary(verification)
