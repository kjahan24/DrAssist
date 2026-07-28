"""Concrete SQLAlchemy repository implementations.

Every `add()` below is "upsert": look up the row by id, create it if
missing, then overwrite its mapped columns from the domain entity's
current in-memory state — see the identical pattern (and rationale) in
`app.modules.organization.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.doctor.domain.entities import (
    Doctor,
    DoctorLicense,
    DoctorProfile,
    DoctorSchedule,
    DoctorSpecialization,
)
from app.modules.doctor.domain.enums import DayOfWeek
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
