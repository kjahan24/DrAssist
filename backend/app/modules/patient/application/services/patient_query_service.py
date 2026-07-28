"""Read-only queries against `Patient`.

Backs the module's public `PatientQueryPort` — the one implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).
"""

from uuid import UUID

from app.modules.patient.application.dto import PatientSummaryDTO
from app.modules.patient.domain.enums import PatientStatus
from app.modules.patient.domain.repositories import PatientRepository


class PatientQueryService:
    def __init__(self, *, patient_repository: PatientRepository) -> None:
        self._patients = patient_repository

    async def patient_exists(self, patient_id: UUID) -> bool:
        return await self._patients.get_by_id(patient_id) is not None

    async def is_active(self, patient_id: UUID) -> bool:
        patient = await self._patients.get_by_id(patient_id)
        return patient is not None and patient.status is PatientStatus.ACTIVE

    async def get_patient_summary(self, patient_id: UUID) -> PatientSummaryDTO | None:
        patient = await self._patients.get_by_id(patient_id)
        if patient is None:
            return None
        return PatientSummaryDTO(
            patient_id=patient.id,
            organization_id=patient.organization_id,
            patient_number=patient.patient_number,
            first_name=patient.first_name,
            last_name=patient.last_name,
            status=patient.status,
        )
