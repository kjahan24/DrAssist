"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.icd10_coding.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.infrastructure.database.query_utils import (
    apply_combined_text_search,
    apply_date_range,
    apply_equality,
    apply_in_filter,
    apply_pagination,
    apply_sort,
    count_total,
    exclude_soft_deleted,
    scope_to_organization,
)
from app.modules.appointment.domain.entities import Appointment
from app.modules.appointment.domain.enums import AppointmentStatus
from app.modules.appointment.domain.repositories import AppointmentRepository
from app.modules.appointment.infrastructure.mappers import (
    apply_appointment_to_model,
    appointment_to_domain,
)
from app.modules.appointment.infrastructure.models import AppointmentModel


class SqlAlchemyAppointmentRepository(AppointmentRepository):
    _SORT_COLUMNS: dict[str, InstrumentedAttribute[Any]] = {
        "created_at": AppointmentModel.created_at,
        "updated_at": AppointmentModel.updated_at,
        "appointment_date": AppointmentModel.appointment_date,
        "appointment_number": AppointmentModel.appointment_number,
        "status": AppointmentModel.status,
        "appointment_type": AppointmentModel.appointment_type,
    }

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, appointment_id: UUID) -> Appointment | None:
        model = await self._session.get(AppointmentModel, appointment_id)
        if model is None or model.deleted_at is not None:
            return None
        return appointment_to_domain(model)

    async def get_by_appointment_number(self, appointment_number: str) -> Appointment | None:
        stmt = select(AppointmentModel).where(
            AppointmentModel.appointment_number == appointment_number,
            AppointmentModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return appointment_to_domain(model) if model is not None else None

    async def list_by_patient(self, patient_id: UUID) -> list[Appointment]:
        stmt = (
            select(AppointmentModel)
            .where(
                AppointmentModel.patient_id == patient_id,
                AppointmentModel.deleted_at.is_(None),
            )
            .order_by(AppointmentModel.appointment_date, AppointmentModel.start_time)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [appointment_to_domain(model) for model in models]

    async def list_by_doctor(self, doctor_id: UUID) -> list[Appointment]:
        stmt = (
            select(AppointmentModel)
            .where(
                AppointmentModel.doctor_id == doctor_id,
                AppointmentModel.deleted_at.is_(None),
            )
            .order_by(AppointmentModel.appointment_date, AppointmentModel.start_time)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [appointment_to_domain(model) for model in models]

    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[AppointmentStatus] | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        appointment_date_from: date | None = None,
        appointment_date_to: date | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "appointment_date",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Appointment], int]:
        stmt = select(AppointmentModel)
        stmt = scope_to_organization(stmt, AppointmentModel.organization_id, organization_id)
        stmt = exclude_soft_deleted(
            stmt, AppointmentModel.deleted_at, include_deleted=include_deleted
        )
        stmt = apply_equality(stmt, AppointmentModel.patient_id, patient_id)
        stmt = apply_equality(stmt, AppointmentModel.doctor_id, doctor_id)
        stmt = apply_in_filter(stmt, AppointmentModel.status, statuses)
        stmt = apply_date_range(
            stmt,
            AppointmentModel.appointment_date,
            start=appointment_date_from,
            end=appointment_date_to,
        )
        stmt = apply_date_range(
            stmt, AppointmentModel.created_at, start=created_from, end=created_to
        )
        stmt = apply_date_range(
            stmt, AppointmentModel.updated_at, start=updated_from, end=updated_to
        )
        stmt = apply_combined_text_search(
            stmt,
            full_text_columns=[AppointmentModel.reason_for_visit, AppointmentModel.notes],
            partial_columns=[AppointmentModel.appointment_number],
            term=query,
        )

        total = await count_total(self._session, stmt)
        column = self._SORT_COLUMNS.get(sort_by, AppointmentModel.appointment_date)
        stmt = apply_sort(stmt, column, sort_order)
        stmt = apply_pagination(stmt, offset=offset, limit=limit)
        models = (await self._session.execute(stmt)).scalars().all()
        return [appointment_to_domain(model) for model in models], total

    async def add(self, appointment: Appointment) -> None:
        model = await self._session.get(AppointmentModel, appointment.id)
        if model is None:
            model = AppointmentModel()
            self._session.add(model)
        apply_appointment_to_model(appointment, model)
