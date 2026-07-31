"""Read-only queries against `Patient`.

Backs the module's public `PatientQueryPort` — the one implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.patient.application.dto import PatientSummaryDTO
from app.modules.patient.domain.entities import Patient
from app.modules.patient.domain.enums import PatientStatus
from app.modules.patient.domain.repositories import PatientRepository


def _to_summary(patient: Patient) -> PatientSummaryDTO:
    return PatientSummaryDTO(
        patient_id=patient.id,
        organization_id=patient.organization_id,
        patient_number=patient.patient_number,
        first_name=patient.first_name,
        last_name=patient.last_name,
        gender=patient.gender,
        date_of_birth=patient.date_of_birth,
        status=patient.status,
        middle_name=patient.middle_name,
        preferred_name=patient.preferred_name,
        blood_group=patient.blood_group,
        marital_status=patient.marital_status,
        national_id=patient.national_id,
        passport_number=patient.passport_number,
        phone=str(patient.phone) if patient.phone is not None else None,
        email=str(patient.email) if patient.email is not None else None,
        occupation=patient.occupation,
        nationality=patient.nationality,
        language=patient.language,
        religion=patient.religion,
        address_line_1=patient.address_line_1,
        address_line_2=patient.address_line_2,
        city=patient.city,
        state=patient.state,
        postal_code=patient.postal_code,
        country=patient.country,
        photo_url=patient.photo_url,
        remarks=patient.remarks,
    )


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
        return _to_summary(patient)

    async def search_patients(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[PatientStatus] | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[PatientSummaryDTO], int]:
        """Search & Filtering module — see
        `PatientRepository.search`'s own docstring for the exact filter/
        sort/pagination semantics; this just maps the resulting entities
        to `PatientSummaryDTO` the same way every other read path here
        does, via `_to_summary`."""
        patients, total = await self._patients.search(
            organization_id=organization_id,
            query=query,
            statuses=statuses,
            created_from=created_from,
            created_to=created_to,
            updated_from=updated_from,
            updated_to=updated_to,
            include_deleted=include_deleted,
            sort_by=sort_by,
            sort_order=sort_order,
            offset=offset,
            limit=limit,
        )
        return [_to_summary(patient) for patient in patients], total
