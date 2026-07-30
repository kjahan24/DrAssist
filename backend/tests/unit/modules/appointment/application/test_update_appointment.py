"""Unit tests for the `UpdateAppointment` use case."""

from datetime import date, time
from uuid import uuid4

import pytest

from app.modules.appointment.application.dto import UpdateAppointmentInput
from app.modules.appointment.application.use_cases.update_appointment import UpdateAppointment
from app.modules.appointment.domain.entities import Appointment
from app.modules.appointment.domain.enums import AppointmentType
from app.modules.appointment.domain.events import AppointmentUpdated
from app.modules.appointment.domain.exceptions import (
    AppointmentNotEditableError,
    AppointmentNotFoundError,
    InvalidAppointmentTimeRangeError,
)
from tests.unit.modules.appointment.application.fakes import (
    FakeAppointmentRepository,
    FakeUnitOfWork,
)


def _make_input(**overrides: object) -> UpdateAppointmentInput:
    defaults: dict[str, object] = {"appointment_id": uuid4()}
    defaults.update(overrides)
    return UpdateAppointmentInput(**defaults)  # type: ignore[arg-type]


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
) -> UpdateAppointment:
    return UpdateAppointment(
        appointment_repository=appointment_repository, unit_of_work=unit_of_work
    )


class TestUpdateAppointment:
    async def test_updates_fields_while_editable(
        self, appointment_repository: FakeAppointmentRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        appointment = _make_appointment()
        await appointment_repository.add(appointment)
        use_case = _use_case(appointment_repository, unit_of_work)

        await use_case.execute(
            _make_input(appointment_id=appointment.id, notes="Bring lab results")
        )

        stored = await appointment_repository.get_by_id(appointment.id)
        assert stored is not None
        assert stored.notes == "Bring lab results"
        assert unit_of_work.committed is True
        assert any(isinstance(e, AppointmentUpdated) for e in unit_of_work.published_events)

    async def test_unknown_appointment_raises(
        self, appointment_repository: FakeAppointmentRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(appointment_repository, unit_of_work)

        with pytest.raises(AppointmentNotFoundError):
            await use_case.execute(_make_input(appointment_id=uuid4()))

    async def test_updating_a_completed_appointment_raises(
        self, appointment_repository: FakeAppointmentRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        appointment = _make_appointment()
        appointment.check_in()
        appointment.complete()
        await appointment_repository.add(appointment)
        use_case = _use_case(appointment_repository, unit_of_work)

        with pytest.raises(AppointmentNotEditableError):
            await use_case.execute(_make_input(appointment_id=appointment.id, notes="Too late"))

    async def test_rescheduling_to_an_invalid_time_range_raises(
        self, appointment_repository: FakeAppointmentRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        appointment = _make_appointment(start_time=time(9, 0), end_time=time(9, 30))
        await appointment_repository.add(appointment)
        use_case = _use_case(appointment_repository, unit_of_work)

        with pytest.raises(InvalidAppointmentTimeRangeError):
            await use_case.execute(
                _make_input(appointment_id=appointment.id, start_time=time(10, 0))
            )
