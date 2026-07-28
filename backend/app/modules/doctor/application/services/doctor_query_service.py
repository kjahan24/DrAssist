"""Read-only queries against `Doctor`.

Backs the module's public `DoctorQueryPort` — the one implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).
"""

from uuid import UUID

from app.modules.doctor.application.dto import DoctorSummaryDTO
from app.modules.doctor.domain.enums import DoctorStatus
from app.modules.doctor.domain.repositories import DoctorRepository


class DoctorQueryService:
    def __init__(self, *, doctor_repository: DoctorRepository) -> None:
        self._doctors = doctor_repository

    async def doctor_exists(self, doctor_id: UUID) -> bool:
        return await self._doctors.get_by_id(doctor_id) is not None

    async def is_active(self, doctor_id: UUID) -> bool:
        doctor = await self._doctors.get_by_id(doctor_id)
        return doctor is not None and doctor.status is DoctorStatus.ACTIVE

    async def get_doctor_summary(self, doctor_id: UUID) -> DoctorSummaryDTO | None:
        doctor = await self._doctors.get_by_id(doctor_id)
        if doctor is None:
            return None
        return DoctorSummaryDTO(
            doctor_id=doctor.id,
            organization_id=doctor.organization_id,
            user_id=doctor.user_id,
            employee_id=doctor.employee_id,
            status=doctor.status,
        )
