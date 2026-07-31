"""Concrete SQLAlchemy repository implementations.

Every `add()` below is "upsert": look up the row by id, create it if
missing, then overwrite its mapped columns from the domain entity's
current in-memory state — see the identical pattern (and rationale) in
`app.modules.organization.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.infrastructure.database.query_utils import (
    apply_combined_text_search,
    apply_date_range,
    apply_in_filter,
    apply_pagination,
    apply_sort,
    count_total,
    exclude_soft_deleted,
    scope_to_organization,
)
from app.modules.doctor.domain.entities import (
    Doctor,
    DoctorLicense,
    DoctorProfile,
    DoctorSchedule,
    DoctorSpecialization,
)
from app.modules.doctor.domain.enums import DayOfWeek, DoctorStatus
from app.modules.doctor.domain.repositories import (
    DoctorLicenseRepository,
    DoctorProfileRepository,
    DoctorRepository,
    DoctorScheduleRepository,
    DoctorSpecializationRepository,
)
from app.modules.doctor.infrastructure.mappers import (
    apply_doctor_license_to_model,
    apply_doctor_profile_to_model,
    apply_doctor_schedule_to_model,
    apply_doctor_specialization_to_model,
    apply_doctor_to_model,
    doctor_license_to_domain,
    doctor_profile_to_domain,
    doctor_schedule_to_domain,
    doctor_specialization_to_domain,
    doctor_to_domain,
)
from app.modules.doctor.infrastructure.models import (
    DoctorLicenseModel,
    DoctorModel,
    DoctorProfileModel,
    DoctorScheduleModel,
    DoctorSpecializationModel,
)


class SqlAlchemyDoctorRepository(DoctorRepository):
    _SORT_COLUMNS: dict[str, InstrumentedAttribute[Any]] = {
        "created_at": DoctorModel.created_at,
        "updated_at": DoctorModel.updated_at,
        "employee_id": DoctorModel.employee_id,
        "status": DoctorModel.status,
        "joining_date": DoctorModel.joining_date,
    }

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, doctor_id: UUID) -> Doctor | None:
        model = await self._session.get(DoctorModel, doctor_id)
        if model is None or model.deleted_at is not None:
            return None
        return doctor_to_domain(model)

    async def get_by_user_id(self, user_id: UUID) -> Doctor | None:
        stmt = select(DoctorModel).where(
            DoctorModel.user_id == user_id, DoctorModel.deleted_at.is_(None)
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return doctor_to_domain(model) if model is not None else None

    async def get_by_employee_id(self, *, organization_id: UUID, employee_id: str) -> Doctor | None:
        stmt = select(DoctorModel).where(
            DoctorModel.organization_id == organization_id,
            DoctorModel.employee_id == employee_id.strip(),
            DoctorModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return doctor_to_domain(model) if model is not None else None

    async def list_by_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[Doctor]:
        stmt = (
            select(DoctorModel)
            .where(
                DoctorModel.organization_id == organization_id,
                DoctorModel.deleted_at.is_(None),
            )
            .order_by(DoctorModel.created_at)
            .offset(offset)
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [doctor_to_domain(model) for model in models]

    async def search(
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
    ) -> tuple[Sequence[Doctor], int]:
        stmt = select(DoctorModel).outerjoin(
            DoctorProfileModel, DoctorProfileModel.doctor_id == DoctorModel.id
        )
        stmt = scope_to_organization(stmt, DoctorModel.organization_id, organization_id)
        stmt = exclude_soft_deleted(stmt, DoctorModel.deleted_at, include_deleted=include_deleted)
        stmt = apply_in_filter(stmt, DoctorModel.status, statuses)
        stmt = apply_date_range(stmt, DoctorModel.created_at, start=created_from, end=created_to)
        stmt = apply_date_range(stmt, DoctorModel.updated_at, start=updated_from, end=updated_to)
        stmt = apply_combined_text_search(
            stmt,
            full_text_columns=[DoctorProfileModel.full_name],
            partial_columns=[DoctorModel.employee_id],
            term=query,
        )

        total = await count_total(self._session, stmt)
        column = self._SORT_COLUMNS.get(sort_by, DoctorModel.created_at)
        stmt = apply_sort(stmt, column, sort_order)
        stmt = apply_pagination(stmt, offset=offset, limit=limit)
        models = (await self._session.execute(stmt)).scalars().all()
        return [doctor_to_domain(model) for model in models], total

    async def add(self, doctor: Doctor) -> None:
        model = await self._session.get(DoctorModel, doctor.id)
        if model is None:
            model = DoctorModel()
            self._session.add(model)
        apply_doctor_to_model(doctor, model)


class SqlAlchemyDoctorProfileRepository(DoctorProfileRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_doctor_id(self, doctor_id: UUID) -> DoctorProfile | None:
        stmt = select(DoctorProfileModel).where(
            DoctorProfileModel.doctor_id == doctor_id, DoctorProfileModel.deleted_at.is_(None)
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return doctor_profile_to_domain(model) if model is not None else None

    async def add(self, profile: DoctorProfile) -> None:
        model = await self._session.get(DoctorProfileModel, profile.id)
        if model is None:
            model = DoctorProfileModel()
            self._session.add(model)
        apply_doctor_profile_to_model(profile, model)


class SqlAlchemyDoctorLicenseRepository(DoctorLicenseRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, license_id: UUID) -> DoctorLicense | None:
        model = await self._session.get(DoctorLicenseModel, license_id)
        if model is None or model.deleted_at is not None:
            return None
        return doctor_license_to_domain(model)

    async def get_by_license_number(self, license_number: str) -> DoctorLicense | None:
        stmt = select(DoctorLicenseModel).where(
            DoctorLicenseModel.license_number == license_number.strip(),
            DoctorLicenseModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return doctor_license_to_domain(model) if model is not None else None

    async def list_by_doctor(self, doctor_id: UUID) -> list[DoctorLicense]:
        stmt = (
            select(DoctorLicenseModel)
            .where(
                DoctorLicenseModel.doctor_id == doctor_id,
                DoctorLicenseModel.deleted_at.is_(None),
            )
            .order_by(DoctorLicenseModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [doctor_license_to_domain(model) for model in models]

    async def add(self, license: DoctorLicense) -> None:
        model = await self._session.get(DoctorLicenseModel, license.id)
        if model is None:
            model = DoctorLicenseModel()
            self._session.add(model)
        apply_doctor_license_to_model(license, model)


class SqlAlchemyDoctorSpecializationRepository(DoctorSpecializationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, specialization_id: UUID) -> DoctorSpecialization | None:
        model = await self._session.get(DoctorSpecializationModel, specialization_id)
        if model is None or model.deleted_at is not None:
            return None
        return doctor_specialization_to_domain(model)

    async def list_by_doctor(self, doctor_id: UUID) -> list[DoctorSpecialization]:
        stmt = (
            select(DoctorSpecializationModel)
            .where(
                DoctorSpecializationModel.doctor_id == doctor_id,
                DoctorSpecializationModel.deleted_at.is_(None),
            )
            .order_by(DoctorSpecializationModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [doctor_specialization_to_domain(model) for model in models]

    async def unset_primary_for_doctor(self, doctor_id: UUID) -> None:
        stmt = (
            update(DoctorSpecializationModel)
            .where(
                DoctorSpecializationModel.doctor_id == doctor_id,
                DoctorSpecializationModel.is_primary.is_(True),
                DoctorSpecializationModel.deleted_at.is_(None),
            )
            .values(is_primary=False)
        )
        await self._session.execute(stmt)

    async def add(self, specialization: DoctorSpecialization) -> None:
        model = await self._session.get(DoctorSpecializationModel, specialization.id)
        if model is None:
            model = DoctorSpecializationModel()
            self._session.add(model)
        apply_doctor_specialization_to_model(specialization, model)


class SqlAlchemyDoctorScheduleRepository(DoctorScheduleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, schedule_id: UUID) -> DoctorSchedule | None:
        model = await self._session.get(DoctorScheduleModel, schedule_id)
        if model is None or model.deleted_at is not None:
            return None
        return doctor_schedule_to_domain(model)

    async def list_by_doctor(self, doctor_id: UUID) -> list[DoctorSchedule]:
        stmt = (
            select(DoctorScheduleModel)
            .where(
                DoctorScheduleModel.doctor_id == doctor_id,
                DoctorScheduleModel.deleted_at.is_(None),
            )
            .order_by(DoctorScheduleModel.day_of_week, DoctorScheduleModel.start_time)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [doctor_schedule_to_domain(model) for model in models]

    async def list_by_doctor_and_day(
        self, doctor_id: UUID, day_of_week: DayOfWeek
    ) -> list[DoctorSchedule]:
        stmt = (
            select(DoctorScheduleModel)
            .where(
                DoctorScheduleModel.doctor_id == doctor_id,
                DoctorScheduleModel.day_of_week == day_of_week,
                DoctorScheduleModel.deleted_at.is_(None),
            )
            .order_by(DoctorScheduleModel.start_time)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [doctor_schedule_to_domain(model) for model in models]

    async def add(self, schedule: DoctorSchedule) -> None:
        model = await self._session.get(DoctorScheduleModel, schedule.id)
        if model is None:
            model = DoctorScheduleModel()
            self._session.add(model)
        apply_doctor_schedule_to_model(schedule, model)
