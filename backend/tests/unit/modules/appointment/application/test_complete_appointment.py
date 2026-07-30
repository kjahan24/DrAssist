"""Unit tests for the `CompleteAppointment` use case
((CheckedIn|InProgress) -> Completed), including "one completed
appointment may optionally create one Visit"."""

from datetime import date, time
from uuid import uuid4

import pytest

from app.modules.appointment.application.dto import CompleteAppointmentInput
from app.modules.appointment.application.services.appointment_consistency_service import (
    AppointmentConsistencyService,
)
from app.modules.appointment.application.use_cases.complete_appointment import (
    CompleteAppointment,
)
from app.modules.appointment.domain.entities import Appointment
from app.modules.appointment.domain.enums import AppointmentStatus, AppointmentType
from app.modules.appointment.domain.exceptions import (
    AppointmentNotFoundError,
    AppointmentVisitMismatchError,
    AppointmentVisitNotFoundError,
    InvalidAppointmentStatusTransitionError,
)
from tests.unit.modules.appointment.application.fakes import (
    FakeAppointmentRepository,
    FakeDoctorQueryPort,
    FakePatientQueryPort,
    FakeUnitOfWork,
    FakeUserQueryPort,
    FakeVisitQueryPort,
    make_visit_summary,
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
    appointment_repository: FakeAppointmentRepository,
    unit_of_work: FakeUnitOfWork,
    visit_query_port: FakeVisitQueryPort | None = None,
) -> CompleteAppointment:
    consistency_service = AppointmentConsistencyService(
        patient_query_port=FakePatientQueryPort(),
        doctor_query_port=FakeDoctorQueryPort(),
        user_query_port=FakeUserQueryPort(),
        visit_query_port=visit_query_port or FakeVisitQueryPort(),
    )
    return CompleteAppointment(
        appointment_repository=appointment_repository,
        consistency_service=consistency_service,
        unit_of_work=unit_of_work,
    )


class TestCompleteAppointment:
    async def test_completes_a_checked_in_appointment_without_a_visit(
        self, appointment_repository: FakeAppointmentRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        appointment = _make_appointment()
        appointment.check_in()
        await appointment_repository.add(appointment)
        use_case = _use_case(appointment_repository, unit_of_work)

        output = await use_case.execute(CompleteAppointmentInput(appointment_id=appointment.id))

        assert output.status is AppointmentStatus.COMPLETED
        stored = await appointment_repository.get_by_id(appointment.id)
        assert stored is not None
        assert stored.visit_id is None

    async def test_unknown_appointment_raises(
        self, appointment_repository: FakeAppointmentRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(appointment_repository, unit_of_work)
        with pytest.raises(AppointmentNotFoundError):
            await use_case.execute(CompleteAppointmentInput(appointment_id=uuid4()))

    async def test_completing_a_scheduled_appointment_raises(
        self, appointment_repository: FakeAppointmentRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        appointment = _make_appointment()
        await appointment_repository.add(appointment)
        use_case = _use_case(appointment_repository, unit_of_work)

        with pytest.raises(InvalidAppointmentStatusTransitionError):
            await use_case.execute(CompleteAppointmentInput(appointment_id=appointment.id))

    async def test_completing_with_a_matching_visit_links_it(
        self, appointment_repository: FakeAppointmentRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        organization_id = uuid4()
        patient_id = uuid4()
        doctor_id = uuid4()
        visit_id = uuid4()
        appointment = _make_appointment(
            organization_id=organization_id, patient_id=patient_id, doctor_id=doctor_id
        )
        appointment.check_in()
        await appointment_repository.add(appointment)
        visit_port = FakeVisitQueryPort(
            existing_visits={
                visit_id: make_visit_summary(
                    visit_id=visit_id,
                    organization_id=organization_id,
                    patient_id=patient_id,
                    doctor_id=doctor_id,
                )
            }
        )
        use_case = _use_case(appointment_repository, unit_of_work, visit_port)

        output = await use_case.execute(
            CompleteAppointmentInput(appointment_id=appointment.id, visit_id=visit_id)
        )

        assert output.status is AppointmentStatus.COMPLETED
        stored = await appointment_repository.get_by_id(appointment.id)
        assert stored is not None
        assert stored.visit_id == visit_id

    async def test_completing_with_an_unknown_visit_raises(
        self, appointment_repository: FakeAppointmentRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        appointment = _make_appointment()
        appointment.check_in()
        await appointment_repository.add(appointment)
        use_case = _use_case(appointment_repository, unit_of_work)

        with pytest.raises(AppointmentVisitNotFoundError):
            await use_case.execute(
                CompleteAppointmentInput(appointment_id=appointment.id, visit_id=uuid4())
            )

    async def test_completing_with_a_mismatched_visit_raises(
        self, appointment_repository: FakeAppointmentRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        appointment = _make_appointment()
        appointment.check_in()
        await appointment_repository.add(appointment)
        visit_id = uuid4()
        visit_port = FakeVisitQueryPort(
            existing_visits={visit_id: make_visit_summary(visit_id=visit_id)}
        )
        use_case = _use_case(appointment_repository, unit_of_work, visit_port)

        with pytest.raises(AppointmentVisitMismatchError):
            await use_case.execute(
                CompleteAppointmentInput(appointment_id=appointment.id, visit_id=visit_id)
            )
