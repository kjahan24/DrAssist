"""Read-only queries against `Doctor`.

Backs the module's public `DoctorQueryPort` — the one implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.doctor.application.dto import DoctorSummaryDTO
from app.modules.doctor.domain.entities import Doctor
from app.modules.doctor.domain.enums import DoctorStatus
from app.modules.doctor.domain.repositories import DoctorRepository


def _to_summary(doctor: Doctor) -> DoctorSummaryDTO:
    return DoctorSummaryDTO(
        doctor_id=doctor.id,
        organization_id=doctor.organization_id,
        user_id=doctor.user_id,
        employee_id=doctor.employee_id,
        joining_date=doctor.joining_date,
        status=doctor.status,
    )


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
        return _to_summary(doctor)

    async def search_doctors(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[DoctorStatus] | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[DoctorSummaryDTO], int]:
        """Search & Filtering module — see `DoctorRepository.search`'s
        docstring for filter/sort/pagination semantics."""
        doctors, total = await self._doctors.search(
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
        return [_to_summary(doctor) for doctor in doctors], total
