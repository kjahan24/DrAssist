"""Unit tests for the `CancelAppointment` use case
((Scheduled|Confirmed|CheckedIn|InProgress) -> Cancelled)."""

from datetime import date, time
from uuid import uuid4

import pytest

from app.modules.appointment.application.dto import CancelAppointmentInput
from app.modules.appointment.application.use_cases.cancel_appointment import CancelAppointment
from app.modules.appointment.domain.entities import Appointment
from app.modules.appointment.domain.enums import AppointmentStatus, AppointmentType
from app.modules.appointment.domain.exceptions import (
    AppointmentNotFoundError,
    InvalidAppointmentStatusTransitionError,
)
from tests.unit.modules.appointment.application.fakes import (
    FakeAppointmentRepository,
    FakeUnitOfWork,
)


def _make_appointment(**overrides: object) -> Appointment:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "doctor_id": uuid4(),
        "appointment_number": "APT-0001",
        "appointment_date": date(2026, 2, 1),
        "start_time": time(9, 0),
        "end_time": time(9, 30),
        "appointment_type": AppointmentType.CONSULTATION,
    }
    defaults.update(overrides)
    return Appointment.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def appointment_repository() -> FakeAppointmentRepository:
    return FakeAppointmentRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    appointment_repository: FakeAppointmentRepository, unit_of_work: FakeUnitOfWork
) -> CancelAppointment:
    return CancelAppointment(
        appointment_repository=appointment_repository, unit_of_work=unit_of_work
    )


class TestCancelAppointment:
    async def test_cancels_a_scheduled_appointment(
        self, appointment_repository: FakeAppointmentRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        appointment = _make_appointment()
        await appointment_repository.add(appointment)
        use_case = _use_case(appointment_repository, unit_of_work)

        output = await use_case.execute(CancelAppointmentInput(appointment_id=appointment.id))

        assert output.status is AppointmentStatus.CANCELLED
        stored = await appointment_repository.get_by_id(appointment.id)
        assert stored is not None
        assert stored.cancelled_at is not None

    async def test_unknown_appointment_raises(
        self, appointment_repository: FakeAppointmentRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(appointment_repository, unit_of_work)
        with pytest.raises(AppointmentNotFoundError):
            await use_case.execute(CancelAppointmentInput(appointment_id=uuid4()))

    async def test_cancelling_a_completed_appointment_raises(
        self, appointment_repository: FakeAppointmentRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        appointment = _make_appointment()
        appointment.check_in()
        appointment.complete()
        await appointment_repository.add(appointment)
        use_case = _use_case(appointment_repository, unit_of_work)

        with pytest.raises(InvalidAppointmentStatusTransitionError):
            await use_case.execute(CancelAppointmentInput(appointment_id=appointment.id))
